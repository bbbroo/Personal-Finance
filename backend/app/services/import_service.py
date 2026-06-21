from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

from dateutil import parser as date_parser
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import DuplicateStatus, ImportStatus, StagedRowStatus, TransferStatus, UserAction
from app.core.money import MoneyError, dollars_to_cents
from app.core.paths import NORMALIZED_IMPORTS_DIR, ORIGINAL_IMPORTS_DIR
from app.core.security import normalized_hash, sha256_bytes
from app.models.domain import ImportBatch, ImportMappingPreset, StagedImportRow, Transaction, TransferLink, utc_now
from app.schemas.common import StagedRowUpdate, TransactionCreate
from app.services.audit_service import record_audit
from app.services.backup_service import create_backup
from app.services.data_quality_service import recompute_data_quality
from app.services.serialization import as_dict
from app.services.transaction_service import clean_merchant, transaction_fingerprint


HEADER_ALIASES = {
    "date": ["date", "transaction date", "posted date", "posting date", "trans date"],
    "posted_date": ["posted date", "posting date"],
    "description": ["description", "details", "memo", "name", "merchant", "payee"],
    "amount": ["amount", "transaction amount"],
    "debit": ["debit", "withdrawal", "withdrawals", "charge"],
    "credit": ["credit", "deposit", "deposits"],
}


def _match_header(headers: list[str], aliases: list[str]) -> str | None:
    normalized = {header.lower().strip(): header for header in headers}
    for alias in aliases:
        if alias in normalized:
            return normalized[alias]
    for lower, header in normalized.items():
        if any(alias in lower for alias in aliases):
            return header
    return None


def auto_detect_mapping(headers: list[str]) -> dict[str, str | None]:
    return {canonical: _match_header(headers, aliases) for canonical, aliases in HEADER_ALIASES.items()}


def _parse_date(value: Any) -> date | None:
    if value in (None, ""):
        return None
    return date_parser.parse(str(value), fuzzy=False).date()


def _parse_amount(row: dict[str, Any], mapping: dict[str, str | None]) -> int | None:
    amount_col = mapping.get("amount")
    if amount_col and row.get(amount_col) not in (None, ""):
        return dollars_to_cents(row.get(amount_col))
    debit_col = mapping.get("debit")
    credit_col = mapping.get("credit")
    debit = dollars_to_cents(row.get(debit_col), allow_none=True) if debit_col else None
    credit = dollars_to_cents(row.get(credit_col), allow_none=True) if credit_col else None
    if debit is not None and credit is not None and debit != 0 and credit != 0:
        raise MoneyError("Row has both debit and credit values.")
    if credit is not None:
        return abs(credit)
    if debit is not None:
        return -abs(debit)
    return None


def normalize_row(
    raw: dict[str, Any],
    mapping: dict[str, str | None],
    *,
    account_id: str | None,
    row_number: int,
) -> tuple[dict[str, Any], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        txn_date = _parse_date(raw.get(mapping.get("date") or ""))
    except Exception:
        txn_date = None
        errors.append("Invalid or missing transaction date.")
    try:
        posted_date = _parse_date(raw.get(mapping.get("posted_date") or "")) if mapping.get("posted_date") else None
    except Exception:
        posted_date = None
        warnings.append("Posted date could not be parsed.")
    description_col = mapping.get("description")
    description = str(raw.get(description_col) or "").strip() if description_col else ""
    if not description:
        errors.append("Missing description.")
    try:
        amount_cents = _parse_amount(raw, mapping)
    except MoneyError as exc:
        amount_cents = None
        errors.append(str(exc))
    if amount_cents is None:
        errors.append("Missing amount; missing money cannot be treated as zero.")
    if account_id is None:
        errors.append("Missing target account.")
    merchant = clean_merchant(description)
    normalized = {
        "account_id": account_id,
        "transaction_date": txn_date.isoformat() if txn_date else None,
        "posted_date": posted_date.isoformat() if posted_date else None,
        "original_description": description,
        "merchant_name": merchant,
        "amount_cents": amount_cents,
        "transaction_type": "income" if amount_cents is not None and amount_cents > 0 else "expense",
        "row_number": row_number,
    }
    return normalized, errors, warnings


def _staged_hash(normalized: dict[str, Any]) -> str:
    return normalized_hash(
        [
            normalized.get("account_id"),
            normalized.get("transaction_date"),
            normalized.get("amount_cents"),
            normalized.get("merchant_name") or normalized.get("original_description"),
        ]
    )


def _write_normalized(batch_id: str, rows: list[dict[str, Any]]) -> Path:
    path = NORMALIZED_IMPORTS_DIR / f"{batch_id}.json"
    path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return path


async def upload_csv(
    db: Session,
    *,
    file: UploadFile,
    account_id: str | None,
    import_type: str = "transactions",
    institution: str | None = None,
) -> ImportBatch:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=422, detail="CSV file is empty.")
    file_sha = sha256_bytes(payload)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_name = Path(file.filename or "import.csv").name.replace(" ", "_")
    original_path = ORIGINAL_IMPORTS_DIR / f"{stamp}_{file_sha[:12]}_{safe_name}"
    original_path.write_bytes(payload)

    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="CSV has no header row.")
    mapping = auto_detect_mapping(reader.fieldnames)
    preset = ImportMappingPreset(
        name=f"Auto-detected {institution or 'CSV'} {import_type}",
        institution=institution,
        import_type=import_type,
        mapping_json=mapping,
        sign_policy="credits_positive_debits_negative" if mapping.get("debit") or mapping.get("credit") else "as_is",
    )
    db.add(preset)
    db.flush()

    batch = ImportBatch(
        import_type=import_type,
        institution=institution,
        account_id=account_id,
        original_filename=file.filename or "import.csv",
        original_file_path=str(original_path),
        original_file_sha256=file_sha,
        mapping_preset_id=preset.id,
        mapping_preset_version=preset.version,
        parser_version=get_settings().parser_version,
        status=ImportStatus.STAGED,
    )
    db.add(batch)
    db.flush()

    normalized_records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    counts = {"valid": 0, "warnings": 0, "errors": 0, "duplicates": 0, "skipped": 0}
    for index, raw in enumerate(reader, start=2):
        normalized, errors, warnings = normalize_row(raw, mapping, account_id=account_id, row_number=index)
        row_hash = _staged_hash(normalized)
        fingerprint = (
            transaction_fingerprint(
                normalized["account_id"],
                normalized["transaction_date"],
                normalized["amount_cents"],
                normalized["merchant_name"] or normalized["original_description"],
            )
            if not errors
            else row_hash
        )
        duplicate_status = DuplicateStatus.UNIQUE
        user_action = UserAction.IMPORT
        if row_hash in seen_hashes:
            duplicate_status = DuplicateStatus.DUPLICATE
            user_action = UserAction.SKIP
            warnings.append("Duplicate within this file.")
        elif not errors and db.scalar(select(Transaction.id).where(Transaction.fingerprint == fingerprint).limit(1)):
            duplicate_status = DuplicateStatus.DUPLICATE
            user_action = UserAction.SKIP
            warnings.append("Exact duplicate of an existing transaction.")
        elif not errors and _similar_existing(db, normalized):
            duplicate_status = DuplicateStatus.POSSIBLE_DUPLICATE
            warnings.append("Possible duplicate based on amount/date/merchant.")
        seen_hashes.add(row_hash)
        status = StagedRowStatus.ERROR if errors else (StagedRowStatus.WARNING if warnings else StagedRowStatus.VALID)
        counts["errors"] += 1 if errors else 0
        counts["warnings"] += 1 if warnings else 0
        counts["valid"] += 1 if not errors else 0
        counts["duplicates"] += 1 if duplicate_status != DuplicateStatus.UNIQUE else 0
        counts["skipped"] += 1 if user_action == UserAction.SKIP else 0
        staged = StagedImportRow(
            import_batch_id=batch.id,
            row_number=index,
            raw_json=raw,
            normalized_json=normalized,
            normalized_hash=row_hash,
            validation_status=status,
            duplicate_status=duplicate_status,
            user_action=user_action,
            errors_json=errors or None,
            warnings_json=warnings or None,
        )
        db.add(staged)
        normalized_records.append(normalized)
    batch.row_count = len(normalized_records)
    batch.valid_row_count = counts["valid"]
    batch.warning_count = counts["warnings"]
    batch.error_count = counts["errors"]
    batch.duplicate_row_count = counts["duplicates"]
    batch.skipped_row_count = counts["skipped"]
    batch.normalized_file_path = str(_write_normalized(batch.id, normalized_records))
    db.flush()
    detect_transfers(db, batch)
    record_audit(db, entity_type="import", entity_id=batch.id, action="stage", after=batch, source="import")
    return batch


def _similar_existing(db: Session, normalized: dict[str, Any]) -> bool:
    if not normalized.get("transaction_date") or normalized.get("amount_cents") is None:
        return False
    txn_date = date.fromisoformat(normalized["transaction_date"])
    start = date.fromordinal(txn_date.toordinal() - 2)
    end = date.fromordinal(txn_date.toordinal() + 2)
    merchant = (normalized.get("merchant_name") or "").lower()
    candidates = db.scalars(
        select(Transaction).where(
            Transaction.account_id == normalized["account_id"],
            Transaction.amount_cents == normalized["amount_cents"],
            Transaction.transaction_date >= start,
            Transaction.transaction_date <= end,
        )
    )
    for candidate in candidates:
        candidate_merchant = (candidate.merchant_name or candidate.original_description or "").lower()
        if merchant and (merchant in candidate_merchant or candidate_merchant in merchant):
            return True
    return False


def validate_batch(db: Session, batch: ImportBatch) -> ImportBatch:
    error_count = 0
    warning_count = 0
    valid_count = 0
    skipped_count = 0
    for row in batch.staged_rows:
        errors = list(row.errors_json or [])
        warnings = list(row.warnings_json or [])
        normalized = row.normalized_json
        if normalized.get("amount_cents") is None and "Missing amount; missing money cannot be treated as zero." not in errors:
            errors.append("Missing amount; missing money cannot be treated as zero.")
        if normalized.get("transaction_date") is None and "Invalid or missing transaction date." not in errors:
            errors.append("Invalid or missing transaction date.")
        row.errors_json = errors or None
        row.warnings_json = warnings or None
        row.validation_status = StagedRowStatus.ERROR if errors else (StagedRowStatus.WARNING if warnings else StagedRowStatus.VALID)
        error_count += 1 if errors else 0
        warning_count += 1 if warnings else 0
        valid_count += 1 if not errors else 0
        skipped_count += 1 if row.user_action == UserAction.SKIP else 0
    batch.valid_row_count = valid_count
    batch.warning_count = warning_count
    batch.error_count = error_count
    batch.skipped_row_count = skipped_count
    batch.status = ImportStatus.VALIDATED if error_count == 0 else ImportStatus.STAGED
    record_audit(db, entity_type="import", entity_id=batch.id, action="validate", after=batch, source="system")
    return batch


def detect_duplicates(db: Session, batch: ImportBatch) -> ImportBatch:
    duplicate_count = 0
    for row in batch.staged_rows:
        normalized = row.normalized_json
        if row.validation_status == StagedRowStatus.ERROR:
            continue
        fingerprint = transaction_fingerprint(
            normalized["account_id"],
            normalized["transaction_date"],
            normalized["amount_cents"],
            normalized["merchant_name"] or normalized["original_description"],
        )
        if db.scalar(select(Transaction.id).where(Transaction.fingerprint == fingerprint).limit(1)):
            row.duplicate_status = DuplicateStatus.DUPLICATE
            row.user_action = UserAction.SKIP
            warnings = list(row.warnings_json or [])
            if "Exact duplicate of an existing transaction." not in warnings:
                warnings.append("Exact duplicate of an existing transaction.")
            row.warnings_json = warnings
            duplicate_count += 1
    batch.duplicate_row_count = duplicate_count
    return batch


def detect_transfers(db: Session, batch: ImportBatch) -> ImportBatch:
    rows = [row for row in batch.staged_rows if row.validation_status != StagedRowStatus.ERROR]
    for row in rows:
        normalized = row.normalized_json
        amount = normalized.get("amount_cents")
        txn_date_raw = normalized.get("transaction_date")
        if amount is None or txn_date_raw is None:
            continue
        txn_date = date.fromisoformat(txn_date_raw)
        candidates: list[tuple[str, int, str]] = []
        for other in rows:
            if other.id == row.id:
                continue
            other_norm = other.normalized_json
            if other_norm.get("amount_cents") == -amount and other_norm.get("account_id") != normalized.get("account_id"):
                other_date = date.fromisoformat(other_norm["transaction_date"])
                day_delta = abs((txn_date - other_date).days)
                if day_delta <= 3:
                    score = 98 if day_delta <= 1 else 88
                    candidates.append((other.id, score, "staged_equal_opposite_amount_date_window"))
        existing = db.scalars(
            select(Transaction).where(
                Transaction.amount_cents == -amount,
                Transaction.transaction_date >= date.fromordinal(txn_date.toordinal() - 3),
                Transaction.transaction_date <= date.fromordinal(txn_date.toordinal() + 3),
                Transaction.account_id != normalized.get("account_id"),
            )
        )
        for txn in existing:
            score = 96 if abs((txn.transaction_date - txn_date).days) <= 1 else 86
            candidates.append((txn.id, score, "existing_equal_opposite_amount_date_window"))
        if candidates:
            best = max(candidates, key=lambda item: item[1])
            row.transfer_status = (
                TransferStatus.CONFIRMED_TRANSFER if best[1] >= 95 else TransferStatus.SUGGESTED_TRANSFER
            )
            warnings = list(row.warnings_json or [])
            label = "Confirmed high-confidence transfer match." if best[1] >= 95 else "Suggested transfer match needs review."
            if label not in warnings:
                warnings.append(label)
            row.warnings_json = warnings
    return batch


def apply_rules_to_batch(db: Session, batch: ImportBatch) -> ImportBatch:
    from app.models.domain import TransactionRule

    rules = list(db.scalars(select(TransactionRule).where(TransactionRule.is_active.is_(True)).order_by(TransactionRule.priority)))
    for row in batch.staged_rows:
        normalized = dict(row.normalized_json)
        for rule in rules:
            merchant = (normalized.get("merchant_name") or "").lower()
            description = (normalized.get("original_description") or "").lower()
            if rule.match_merchant_contains and rule.match_merchant_contains.lower() not in merchant:
                continue
            if rule.match_description_contains and rule.match_description_contains.lower() not in description:
                continue
            if rule.match_account_id and rule.match_account_id != normalized.get("account_id"):
                continue
            amount = normalized.get("amount_cents")
            if rule.match_amount_min_cents is not None and amount < rule.match_amount_min_cents:
                continue
            if rule.match_amount_max_cents is not None and amount > rule.match_amount_max_cents:
                continue
            if rule.action_category_id:
                normalized["category_id"] = rule.action_category_id
            if rule.action_merchant_name:
                normalized["merchant_name"] = rule.action_merchant_name
            warnings = list(row.warnings_json or [])
            warnings.append(f"Rule applied: {rule.name}")
            row.warnings_json = warnings
            row.normalized_json = normalized
            if rule.stop_processing:
                break
    record_audit(db, entity_type="import", entity_id=batch.id, action="rule_apply", after=batch, source="rule")
    return batch


def update_staged_row(db: Session, row: StagedImportRow, payload: StagedRowUpdate) -> StagedImportRow:
    before = as_dict(row)
    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(row, key, value)
    if payload.normalized_json is not None:
        row.normalized_hash = _staged_hash(payload.normalized_json)
        row.user_action = UserAction.EDIT
    db.flush()
    record_audit(db, entity_type="staged_import_row", entity_id=row.id, action="update", before=before, after=row)
    return row


def commit_batch(db: Session, batch: ImportBatch) -> ImportBatch:
    if batch.status in {ImportStatus.COMMITTED, ImportStatus.ROLLED_BACK}:
        raise HTTPException(status_code=409, detail=f"Import batch is already {batch.status}.")
    validate_batch(db, batch)
    if batch.error_count:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "IMPORT_VALIDATION_FAILED",
                "message": f"{batch.error_count} staged rows have fatal errors.",
                "details": {"import_batch_id": batch.id},
                "recommended_action": "Fix or skip invalid rows before committing.",
            },
        )
    backup = create_backup(db, backup_type="pre_import", notes=f"Before import {batch.original_filename}")
    manifest: dict[str, list[dict[str, Any]]] = {"created": [], "updated": [], "deleted": []}
    try:
        transfer_link_cache: dict[str, str] = {}
        for row in batch.staged_rows:
            if row.user_action == UserAction.SKIP or row.validation_status == StagedRowStatus.ERROR:
                continue
            normalized = row.normalized_json
            payload = TransactionCreate(
                account_id=normalized["account_id"],
                transaction_date=date.fromisoformat(normalized["transaction_date"]),
                posted_date=date.fromisoformat(normalized["posted_date"]) if normalized.get("posted_date") else None,
                original_description=normalized["original_description"],
                merchant_name=normalized.get("merchant_name"),
                amount_cents=int(normalized["amount_cents"]),
                category_id=normalized.get("category_id"),
                transaction_type=normalized.get("transaction_type") or "unknown",
                transfer_status=row.transfer_status,
            )
            txn = Transaction(
                account_id=payload.account_id,
                transaction_date=payload.transaction_date,
                posted_date=payload.posted_date,
                original_description=payload.original_description,
                merchant_name=payload.merchant_name,
                amount_cents=payload.amount_cents,
                category_id=payload.category_id,
                transaction_type=payload.transaction_type,
                transfer_status=payload.transfer_status,
                review_status="needs_review",
                duplicate_status=row.duplicate_status,
                fingerprint=transaction_fingerprint(
                    payload.account_id, payload.transaction_date, payload.amount_cents, payload.merchant_name
                ),
                source_type="csv_import",
                source_id=batch.id,
                created_by_import_batch_id=batch.id,
            )
            if row.transfer_status == TransferStatus.CONFIRMED_TRANSFER:
                link_key = f"{abs(payload.amount_cents)}:{payload.transaction_date.isoformat()}"
                if link_key not in transfer_link_cache:
                    link = TransferLink(
                        confidence_score="0.98",
                        match_basis="exact_amount_date_window",
                        status="confirmed",
                        created_by="system",
                        confirmed_at=utc_now(),
                    )
                    db.add(link)
                    db.flush()
                    transfer_link_cache[link_key] = link.id
                txn.transfer_link_id = transfer_link_cache[link_key]
            db.add(txn)
            db.flush()
            row.final_record_type = "transaction"
            row.final_record_id = txn.id
            manifest["created"].append({"entity_type": "transaction", "entity_id": txn.id})
            record_audit(
                db,
                entity_type="transaction",
                entity_id=txn.id,
                action="create",
                after=txn,
                source="import",
                source_id=batch.id,
            )
        batch.status = ImportStatus.COMMITTED
        batch.committed_at = utc_now()
        batch.committed_record_manifest_json = manifest
        record_audit(
            db,
            entity_type="import",
            entity_id=batch.id,
            action="import_commit",
            after={"batch": as_dict(batch), "backup_id": backup.id, "manifest": manifest},
            source="import",
            source_id=batch.id,
        )
        recompute_data_quality(db)
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "IMPORT_COMMIT_DUPLICATE",
                "message": "Import could not commit because it would duplicate an existing transaction.",
                "details": {"error": str(exc)},
                "recommended_action": "Re-run duplicate detection and skip duplicate rows.",
            },
        ) from exc
    return batch


def rollback_batch(db: Session, batch: ImportBatch) -> ImportBatch:
    if batch.status != ImportStatus.COMMITTED:
        raise HTTPException(status_code=409, detail="Only committed imports can be rolled back.")
    create_backup(db, backup_type="pre_rollback", notes=f"Before rollback {batch.original_filename}")
    manifest = batch.committed_record_manifest_json or {"created": [], "updated": [], "deleted": []}
    created = list(reversed(manifest.get("created", [])))
    for item in created:
        if item["entity_type"] == "transaction":
            txn = db.get(Transaction, item["entity_id"])
            if txn is None:
                continue
            committed_at = batch.committed_at.replace(tzinfo=None) if batch.committed_at else None
            txn_updated_at = txn.updated_at.replace(tzinfo=None) if txn.updated_at else None
            if committed_at and txn_updated_at and txn_updated_at > committed_at:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error_code": "ROLLBACK_BLOCKED_BY_MANUAL_EDIT",
                        "message": "An imported transaction was changed after commit.",
                        "details": {"transaction_id": txn.id},
                        "recommended_action": "Review the transaction before forcing rollback.",
                    },
                )
            before = as_dict(txn)
            db.delete(txn)
            record_audit(
                db,
                entity_type="transaction",
                entity_id=item["entity_id"],
                action="delete",
                before=before,
                source="import",
                source_id=batch.id,
            )
    batch.status = ImportStatus.ROLLED_BACK
    batch.rolled_back_at = utc_now()
    record_audit(db, entity_type="import", entity_id=batch.id, action="rollback", after=batch, source="import", source_id=batch.id)
    recompute_data_quality(db)
    db.flush()
    return batch
