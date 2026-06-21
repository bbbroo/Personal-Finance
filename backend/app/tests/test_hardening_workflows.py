from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import select

from app.models.domain import (
    AccountStatement,
    AuditLog,
    DailyAppSnapshot,
    ImportBatch,
    Liability,
    Price,
    StagedImportRow,
    Transaction,
    TransferLink,
)
from app.schemas.common import HoldingCreate, StagedRowUpdate
from app.services.backup_service import create_backup, restore_backup
from app.services.daily_refresh_service import run_daily_refresh
from app.services.holding_service import create_holding_snapshot, latest_holdings_as_of
from app.services.import_service import _staged_hash, commit_batch, detect_transfers, remap_batch, rollback_batch, update_staged_row, upload_csv
from app.services.reconciliation_service import run_reconciliation
from app.services.report_service import asset_allocation, calculate_net_worth, cash_flow
from app.tests.factories import account, instrument, transaction


def _patch_backup_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.services import backup_service

    for key in list(backup_service.BACKUP_DIRS):
        monkeypatch.setitem(backup_service.BACKUP_DIRS, key, tmp_path / "backups" / key)


def _upload(db, account_id: str, csv_text: str) -> ImportBatch:
    file = UploadFile(filename="test.csv", file=BytesIO(csv_text.encode("utf-8")))
    return asyncio.run(upload_csv(db, file=file, account_id=account_id, institution="Test Bank"))


def test_holding_snapshot_replacement_prevents_double_count(db):
    brokerage = account(db, "Brokerage", account_type="brokerage", valuation_method="holdings_sum")
    vti = instrument(db, "VTI")
    old = create_holding_snapshot(
        db,
        HoldingCreate(
            account_id=brokerage.id,
            instrument_id=vti.id,
            snapshot_date=date(2026, 6, 1),
            quantity_decimal="10",
            price_decimal="50",
            cost_basis_cents=40000,
            cost_basis_quality="verified",
        ),
    )
    new = create_holding_snapshot(
        db,
        HoldingCreate(
            account_id=brokerage.id,
            instrument_id=vti.id,
            snapshot_date=date(2026, 6, 15),
            quantity_decimal="12",
            price_decimal="55",
            cost_basis_cents=50000,
            cost_basis_quality="verified",
        ),
    )
    assert old.is_current is False
    assert new.is_current is True
    assert [row.id for row in latest_holdings_as_of(db, as_of=date(2026, 6, 30))] == [new.id]
    assert calculate_net_worth(db, date(2026, 6, 30))["net_worth_cents"] == 66000


def test_same_date_holding_replacement_requires_explicit_flag(db):
    brokerage = account(db, "Brokerage", account_type="brokerage", valuation_method="holdings_sum")
    vti = instrument(db, "VXUS")
    first = create_holding_snapshot(
        db,
        HoldingCreate(
            account_id=brokerage.id,
            instrument_id=vti.id,
            snapshot_date=date(2026, 6, 1),
            quantity_decimal="10",
            price_decimal="20",
            cost_basis_cents=15000,
        ),
    )
    with pytest.raises(HTTPException) as exc:
        create_holding_snapshot(
            db,
            HoldingCreate(
                account_id=brokerage.id,
                instrument_id=vti.id,
                snapshot_date=date(2026, 6, 1),
                quantity_decimal="11",
                price_decimal="20",
                cost_basis_cents=16000,
            ),
        )
    assert exc.value.status_code == 409
    replacement = create_holding_snapshot(
        db,
        HoldingCreate(
            account_id=brokerage.id,
            instrument_id=vti.id,
            snapshot_date=date(2026, 6, 1),
            quantity_decimal="11",
            price_decimal="20",
            cost_basis_cents=16000,
            replace_existing=True,
        ),
    )
    assert first.is_current is False
    assert replacement.is_current is True
    assert replacement.replaces_snapshot_id == first.id


def test_allocation_modes_include_correct_balance_sheet_components(db):
    checking = account(db, "Checking")
    brokerage = account(db, "Brokerage", account_type="brokerage", valuation_method="holdings_plus_cash")
    card = account(db, "Card", account_type="credit_card", valuation_method="liability_balance", balance_sign_policy="liability_positive")
    vti = instrument(db, "ITOT", "us_stock")
    db.add_all(
        [
            Price(instrument_id=vti.id, price_date=date.today(), price_decimal="100", provider="manual", status="manual_override"),
            Liability(account_id=card.id, liability_type="credit_card", current_balance_cents=12000, minimum_payment_cents=2500),
        ]
    )
    from app.models.domain import AccountBalanceSnapshot

    db.add_all(
        [
            AccountBalanceSnapshot(account_id=checking.id, snapshot_date=date.today(), balance_cents=10000, balance_kind="current", source_type="manual", confidence="high", is_reconciled=True),
            AccountBalanceSnapshot(account_id=brokerage.id, snapshot_date=date.today(), balance_cents=5000, balance_kind="cash_position", source_type="manual", confidence="high", is_reconciled=True),
        ]
    )
    create_holding_snapshot(
        db,
        HoldingCreate(
            account_id=brokerage.id,
            instrument_id=vti.id,
            snapshot_date=date.today(),
            quantity_decimal="5",
            price_decimal="100",
            cost_basis_cents=40000,
            cost_basis_quality="verified",
        ),
    )
    investment_only = asset_allocation(db, mode="investment_only")
    full = asset_allocation(db, mode="full_net_worth")
    assert investment_only["total_cents"] == 50000
    assert full["total_cents"] == 53000
    slices = {row["asset_class"]: row["value_cents"] for row in full["slices"]}
    assert slices["cash"] == 15000
    assert slices["liability"] == -12000
    assert slices["us_stock"] == 50000


def test_daily_refresh_creates_snapshot_and_marks_stale_prices(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    acct = account(db, "Brokerage", account_type="brokerage", valuation_method="holdings_sum")
    vti = instrument(db, "STALE")
    db.add(Price(instrument_id=vti.id, price_date=date.today() - timedelta(days=10), price_decimal="10", provider="manual", status="current"))
    create_holding_snapshot(
        db,
        HoldingCreate(account_id=acct.id, instrument_id=vti.id, snapshot_date=date.today(), quantity_decimal="1", price_decimal="10"),
    )
    run = run_daily_refresh(db, force=True)
    db.flush()
    snapshot = db.scalar(select(DailyAppSnapshot).where(DailyAppSnapshot.snapshot_date == date.today()))
    price = db.scalar(select(Price).where(Price.instrument_id == vti.id))
    assert run.created_snapshot is True
    assert run.refreshed_prices is False
    assert snapshot is not None
    assert price.status == "stale"
    assert any("No external price provider" in warning for warning in (run.warnings_json or []))
    assert any("Coinbase sync is not implemented" in warning for warning in (run.warnings_json or []))


def test_import_remap_row_edit_commit_and_rollback(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    acct = account(db)
    batch = _upload(db, acct.id, "When,Text,Outflow\n2026-06-01,Coffee,-4.25\n")
    assert batch.error_count == 1
    remap_batch(db, batch, {"date": "When", "posted_date": None, "description": "Text", "amount": "Outflow", "debit": None, "credit": None})
    row = batch.staged_rows[0]
    assert batch.error_count == 0
    edited = dict(row.normalized_json)
    edited["amount_cents"] = -500
    update_staged_row(db, row, StagedRowUpdate(normalized_json=edited))
    assert db.scalar(select(AuditLog).where(AuditLog.entity_type == "staged_import_row").limit(1)) is not None
    commit_batch(db, batch)
    db.commit()
    txn = db.scalar(select(Transaction).where(Transaction.source_id == batch.id))
    assert txn.amount_cents == -500
    rollback_batch(db, batch)
    db.commit()
    assert db.scalar(select(Transaction).where(Transaction.source_id == batch.id)) is None


def test_duplicate_review_can_confirm_skip_possible_duplicate(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    acct = account(db)
    transaction(db, acct.id, -425, date(2026, 6, 1), "Coffee Shop")
    batch = _upload(db, acct.id, "Date,Description,Amount\n2026-06-01,Coffee,-4.25\n")
    row = batch.staged_rows[0]
    assert row.duplicate_status == "possible_duplicate"
    update_staged_row(db, row, StagedRowUpdate(duplicate_status="confirmed_duplicate"))
    commit_batch(db, batch)
    db.commit()
    assert db.scalar(select(Transaction).where(Transaction.source_id == batch.id)) is None


def test_transfer_pair_confirms_credit_card_payment_and_updates_existing_side(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    checking = account(db, "Checking")
    card = account(db, "Card", account_type="credit_card", valuation_method="liability_balance", balance_sign_policy="liability_positive")
    existing = transaction(db, checking.id, -10000, date(2026, 6, 10), "Credit Card Payment", transaction_type="transfer")
    batch = _upload(db, card.id, "Date,Description,Amount\n2026-06-11,Payment Thank You,100.00\n")
    row = batch.staged_rows[0]
    assert row.transfer_status == "confirmed_transfer"
    assert row.normalized_json["transfer_candidate"]["candidate_type"] == "transaction"
    commit_batch(db, batch)
    db.commit()
    created = db.scalar(select(Transaction).where(Transaction.source_id == batch.id))
    assert created.transfer_link_id == existing.transfer_link_id
    assert existing.transfer_status == "confirmed_transfer"
    assert db.get(TransferLink, created.transfer_link_id).status == "confirmed"
    flow = cash_flow(db, date(2026, 6, 1), date(2026, 6, 30))
    assert flow["income_cents"] == 0
    assert flow["expenses_cents"] == 0


def test_equal_amount_reimbursement_stays_suggested_and_reports_include_it(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    checking = account(db, "Checking")
    savings = account(db, "Savings")
    transaction(db, checking.id, -10000, date(2026, 6, 10), "Lunch with Alex")
    batch = _upload(db, savings.id, "Date,Description,Amount\n2026-06-10,Refund from Alex,100.00\n")
    assert batch.staged_rows[0].transfer_status == "suggested_transfer"
    commit_batch(db, batch)
    db.commit()
    flow = cash_flow(db, date(2026, 6, 1), date(2026, 6, 30))
    assert flow["income_cents"] == 10000
    assert flow["expenses_cents"] == 10000


def test_staged_brokerage_and_hsa_transfers_are_linked_as_pairs(db):
    checking = account(db, "Checking")
    brokerage = account(db, "Brokerage", account_type="brokerage", valuation_method="holdings_plus_cash")
    hsa = account(db, "HSA", account_type="hsa", valuation_method="holdings_plus_cash")
    batch = ImportBatch(
        import_type="transactions",
        account_id=checking.id,
        original_filename="manual.csv",
        original_file_path="manual.csv",
        original_file_sha256="a" * 64,
        parser_version="test",
        status="staged",
    )
    db.add(batch)
    db.flush()
    rows = [
        {"account_id": checking.id, "transaction_date": "2026-06-01", "original_description": "ACH transfer to Schwab Brokerage", "merchant_name": "ACH transfer to Schwab Brokerage", "amount_cents": -50000, "transaction_type": "expense", "row_number": 2},
        {"account_id": brokerage.id, "transaction_date": "2026-06-01", "original_description": "ACH transfer from checking", "merchant_name": "ACH transfer from checking", "amount_cents": 50000, "transaction_type": "income", "row_number": 3},
        {"account_id": checking.id, "transaction_date": "2026-06-02", "original_description": "HSA contribution", "merchant_name": "HSA contribution", "amount_cents": -20000, "transaction_type": "expense", "row_number": 4},
        {"account_id": hsa.id, "transaction_date": "2026-06-02", "original_description": "HSA contribution received", "merchant_name": "HSA contribution received", "amount_cents": 20000, "transaction_type": "income", "row_number": 5},
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
    assert {row.transfer_status for row in batch.staged_rows} == {"confirmed_transfer"}
    link_ids = {row.normalized_json["transfer_candidate"]["transfer_link_id"] for row in batch.staged_rows}
    assert len(link_ids) == 2


def test_reconciliation_respects_liability_positive_sign_policy(db):
    card = account(db, "Card", account_type="credit_card", valuation_method="liability_balance", balance_sign_policy="liability_positive")
    transaction(db, card.id, -2000, date(2026, 6, 5), "Purchase")
    transaction(db, card.id, 5000, date(2026, 6, 10), "Payment")
    statement = AccountStatement(
        account_id=card.id,
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
        opening_balance_cents=10000,
        ending_balance_cents=7000,
    )
    db.add(statement)
    db.flush()
    run = run_reconciliation(db, statement)
    assert run.status == "matched"
    assert run.calculated_ending_balance_cents == 7000


def test_backup_manifest_hash_mismatch_rejects_restore(db, monkeypatch, tmp_path):
    _patch_backup_dirs(monkeypatch, tmp_path)
    account(db)
    manifest = create_backup(db, backup_type="manual", notes="test")
    db.commit()
    backup_path = Path(manifest.backup_path)
    backup_path.write_bytes(backup_path.read_bytes() + b"tamper")
    with pytest.raises(HTTPException) as exc:
        restore_backup(db, str(backup_path))
    assert exc.value.detail["error_code"] == "BACKUP_HASH_MISMATCH"


def test_fresh_database_can_be_created_through_migrations(tmp_path):
    db_path = tmp_path / "fresh.sqlite3"
    env = os.environ.copy()
    env["LOCAL_FINANCE_DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    backend_dir = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
