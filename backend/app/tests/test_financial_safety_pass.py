from __future__ import annotations

import asyncio
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import select

from app.models.domain import (
    BudgetPeriod,
    DataQualityIssue,
    ImportBatch,
    StagedImportRow,
    Transaction,
    TransactionSplit,
    TransferLink,
    TransferLinkMember,
)
from app.schemas.common import StagedRowUpdate
from app.services.budget_service import category_actual_cents
from app.services.data_quality_service import ignore_issue, recompute_data_quality
from app.services.import_service import _staged_hash, commit_batch, detect_transfers, remap_batch, update_staged_row, upload_csv
from app.tests.factories import account, category, transaction


def _patch_backup_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services import backup_service

    for key in list(backup_service.BACKUP_DIRS):
        monkeypatch.setitem(backup_service.BACKUP_DIRS, key, tmp_path / "backups" / key)


def _upload(db, account_id: str, csv_text: str) -> ImportBatch:
    file = UploadFile(filename="test.csv", file=BytesIO(csv_text.encode("utf-8")))
    return asyncio.run(upload_csv(db, file=file, account_id=account_id, institution="Test Bank"))


def _manual_two_sided_batch(db, left_account_id: str, right_account_id: str) -> ImportBatch:
    batch = ImportBatch(
        import_type="transactions",
        account_id=left_account_id,
        original_filename="manual.csv",
        original_file_path="manual.csv",
        original_file_sha256="b" * 64,
        parser_version="test",
        status="staged",
    )
    db.add(batch)
    db.flush()
    rows = [
        {
            "account_id": left_account_id,
            "transaction_date": "2026-06-01",
            "original_description": "ACH transfer to savings",
            "merchant_name": "ACH transfer to savings",
            "amount_cents": -10000,
            "transaction_type": "expense",
            "row_number": 2,
        },
        {
            "account_id": right_account_id,
            "transaction_date": "2026-06-01",
            "original_description": "ACH transfer from checking",
            "merchant_name": "ACH transfer from checking",
            "amount_cents": 10000,
            "transaction_type": "income",
            "row_number": 3,
        },
    ]
    for item in rows:
        db.add(
            StagedImportRow(
                import_batch_id=batch.id,
                row_number=item["row_number"],
                raw_json=item,
                normalized_json=item,
                normalized_hash=_staged_hash(item),
                validation_status="valid",
            )
        )
    db.flush()
    detect_transfers(db, batch)
    return batch


def test_confirmed_staged_transfer_commits_only_when_both_sides_commit(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    checking = account(db, "Checking")
    savings = account(db, "Savings")
    batch = _manual_two_sided_batch(db, checking.id, savings.id)
    assert {row.transfer_status for row in batch.staged_rows} == {"confirmed_transfer"}

    commit_batch(db, batch)
    db.commit()

    txns = list(db.scalars(select(Transaction).where(Transaction.source_id == batch.id)))
    assert len(txns) == 2
    assert {txn.transfer_status for txn in txns} == {"confirmed_transfer"}
    assert len({txn.transfer_link_id for txn in txns}) == 1


@pytest.mark.parametrize(
    "mutation",
    [
        "skip",
        "reject",
        "error",
    ],
)
def test_incomplete_confirmed_staged_transfer_pair_blocks_commit(db, monkeypatch, tmp_path, mutation):
    _patch_backup_dirs(monkeypatch, tmp_path)
    checking = account(db, "Checking")
    savings = account(db, "Savings")
    batch = _manual_two_sided_batch(db, checking.id, savings.id)
    row = batch.staged_rows[1]
    if mutation == "skip":
        update_staged_row(db, row, StagedRowUpdate(user_action="skip"))
    elif mutation == "reject":
        update_staged_row(db, row, StagedRowUpdate(transfer_status="rejected_transfer"))
    else:
        edited = dict(row.normalized_json)
        edited["amount_cents"] = None
        update_staged_row(db, row, StagedRowUpdate(normalized_json=edited))

    with pytest.raises(HTTPException) as exc:
        commit_batch(db, batch)

    assert exc.value.status_code == 422
    assert exc.value.detail["error_code"] == "INCOMPLETE_CONFIRMED_TRANSFER_PAIR"
    assert db.scalar(select(Transaction).where(Transaction.source_id == batch.id)) is None


def test_confirmed_existing_side_match_remains_valid(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    checking = account(db, "Checking")
    card = account(db, "Card", account_type="credit_card", valuation_method="liability_balance", balance_sign_policy="liability_positive")
    existing = transaction(db, checking.id, -10000, date(2026, 6, 10), "Credit Card Payment", transaction_type="transfer")
    batch = _upload(db, card.id, "Date,Description,Amount\n2026-06-11,Payment Thank You,100.00\n")

    commit_batch(db, batch)
    db.commit()

    created = db.scalar(select(Transaction).where(Transaction.source_id == batch.id))
    assert created.transfer_status == "confirmed_transfer"
    assert existing.transfer_status == "confirmed_transfer"
    assert created.transfer_link_id == existing.transfer_link_id


def test_same_amount_unrelated_transactions_are_not_confirmed(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    checking = account(db, "Checking")
    savings = account(db, "Savings")
    transaction(db, checking.id, -10000, date(2026, 6, 10), "Dinner")
    batch = _upload(db, savings.id, "Date,Description,Amount\n2026-06-10,Random Deposit,100.00\n")
    row = batch.staged_rows[0]

    assert row.transfer_status == "suggested_transfer"
    commit_batch(db, batch)
    db.commit()
    created = db.scalar(select(Transaction).where(Transaction.source_id == batch.id))
    assert created.transfer_status == "suggested_transfer"


def test_remap_deletes_system_transfer_links_without_orphans(db):
    checking = account(db, "Checking")
    batch = _upload(
        db,
        checking.id,
        "Date,Description,Amount\n2026-06-01,ACH transfer to savings,-100.00\n",
    )
    row = batch.staged_rows[0]
    stale_link = TransferLink(confidence_score="0.99", match_basis="test", status="confirmed", created_by="system")
    db.add(stale_link)
    db.flush()
    db.add(
        TransferLinkMember(
            transfer_link_id=stale_link.id,
            staged_row_id=row.id,
            account_id=checking.id,
            amount_cents=-10000,
            side="outflow",
        )
    )
    db.flush()

    remap_batch(db, batch, {"date": "Date", "posted_date": None, "description": "Description", "amount": "Amount", "debit": None, "credit": None})
    orphaned_system_links = list(
        db.scalars(
            select(TransferLink).where(
                TransferLink.created_by == "system",
                ~TransferLink.id.in_(select(TransferLinkMember.transfer_link_id)),
            )
        )
    )
    null_members = list(
        db.scalars(
            select(TransferLinkMember).where(
                TransferLinkMember.transaction_id.is_(None),
                TransferLinkMember.staged_row_id.is_(None),
            )
        )
    )
    assert orphaned_system_links == []
    assert null_members == []


def test_ignored_data_quality_issue_stays_ignored_until_fingerprint_changes(db):
    acct = account(db, "No Balance")
    issues = recompute_data_quality(db)
    issue = next(issue for issue in issues if issue.entity_id == acct.id and issue.issue_type == "missing_data")
    ignored_id = issue.id
    ignored_fingerprint = issue.fingerprint
    ignore_issue(db, issue)
    db.flush()

    recompute_data_quality(db)
    assert db.get(DataQualityIssue, ignored_id).status == "ignored"
    assert db.scalar(select(DataQualityIssue).where(DataQualityIssue.fingerprint == ignored_fingerprint, DataQualityIssue.status == "open")) is None

    acct.name = "Renamed No Balance"
    reopened = recompute_data_quality(db)
    assert any(open_issue.status == "open" and open_issue.entity_id == acct.id for open_issue in reopened)


def test_budget_actuals_use_signed_refunds_reversals_splits_and_transfer_status(db):
    acct = account(db, "Checking")
    groceries = category(db, "Groceries", "expense")
    paycheck = category(db, "Paycheck", "income")
    period = BudgetPeriod(period_type="monthly", start_date=date(2026, 6, 1), end_date=date(2026, 6, 30), status="active")
    db.add(period)
    db.flush()

    transaction(db, acct.id, -10000, date(2026, 6, 1), "Groceries", category_id=groceries.id)
    transaction(db, acct.id, 2500, date(2026, 6, 2), "Grocery Refund", category_id=groceries.id)
    transaction(db, acct.id, 300000, date(2026, 6, 3), "Paycheck", category_id=paycheck.id)
    transaction(db, acct.id, -5000, date(2026, 6, 4), "Payroll reversal", category_id=paycheck.id)
    transaction(db, acct.id, -7777, date(2026, 6, 5), "Confirmed transfer", category_id=groceries.id, transfer_status="confirmed_transfer")
    transaction(db, acct.id, -3333, date(2026, 6, 6), "Suggested transfer", category_id=groceries.id, transfer_status="suggested_transfer")
    split_parent = transaction(db, acct.id, -4000, date(2026, 6, 7), "Split", is_split=True)
    db.add(TransactionSplit(transaction_id=split_parent.id, category_id=groceries.id, amount_cents=-1500))
    db.flush()

    assert category_actual_cents(db, groceries.id, period) == 12333
    assert category_actual_cents(db, paycheck.id, period) == 295000
