from __future__ import annotations

import asyncio
from datetime import date
from io import BytesIO

from fastapi import UploadFile
from sqlalchemy import select

from app.models.domain import AuditLog, ImportBatch, Transaction
from app.services.import_service import commit_batch, rollback_batch, upload_csv
from app.tests.factories import account, transaction


def _upload(db, account_id: str, csv_text: str) -> ImportBatch:
    file = UploadFile(filename="test.csv", file=BytesIO(csv_text.encode("utf-8")))
    return asyncio.run(upload_csv(db, file=file, account_id=account_id, institution="Test Bank"))


def test_import_stage_commit_and_rollback(db):
    acct = account(db)
    batch = _upload(db, acct.id, "Date,Description,Amount\n2026-06-01,Coffee,-4.25\n")
    assert batch.status == "staged"
    assert batch.valid_row_count == 1
    commit_batch(db, batch)
    db.commit()
    assert db.scalar(select(Transaction).where(Transaction.source_id == batch.id).limit(1)) is not None
    assert db.scalar(select(AuditLog).where(AuditLog.action == "import_commit").limit(1)) is not None
    rollback_batch(db, batch)
    db.commit()
    assert db.scalar(select(Transaction).where(Transaction.source_id == batch.id).limit(1)) is None
    assert batch.status == "rolled_back"


def test_duplicate_detection_marks_exact_duplicate(db):
    acct = account(db)
    transaction(db, acct.id, -425, date(2026, 6, 1), "Coffee")
    batch = _upload(db, acct.id, "Date,Description,Amount\n2026-06-01,Coffee,-4.25\n")
    row = batch.staged_rows[0]
    assert row.duplicate_status == "duplicate"
    assert row.user_action == "skip"


def test_transfer_detection_confirms_high_confidence_existing_match(db):
    checking = account(db, "Checking")
    card = account(db, "Card", account_type="credit_card", valuation_method="liability_balance", balance_sign_policy="liability_positive")
    transaction(db, checking.id, -10000, date(2026, 6, 10), "Credit Card Payment", transaction_type="transfer")
    batch = _upload(db, card.id, "Date,Description,Amount\n2026-06-11,Payment Thank You,100.00\n")
    assert batch.staged_rows[0].transfer_status == "confirmed_transfer"
