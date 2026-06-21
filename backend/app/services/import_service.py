from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from decimal import Decimal
from io import StringIO
from pathlib import Path
from typing import Any

from dateutil import parser as date_parser
from fastapi import HTTPException, UploadFile
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.enums import DuplicateStatus, ImportStatus, StagedRowStatus, TransferStatus, UserAction
from app.core.money import MoneyError, dollars_to_cents
from app.core.paths import NORMALIZED_IMPORTS_DIR, ORIGINAL_IMPORTS_DIR
from app.core.security import normalized_hash, sha256_bytes
from app.models.domain import Account, ImportBatch, ImportMappingPreset, StagedImportRow, Transaction, TransferLink, TransferLinkMember, utc_now
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


def _row_counts(rows: list[StagedImportRow]) -> dict[str, int]:
    return {
        "valid": sum(1 for row in rows if row.validation_status != StagedRowStatus.ERROR),
        "warnings": sum(1 for row in rows if row.warnings_json),
        "errors": sum(1 for row in rows if row.validation_status == StagedRowStatus.ERROR),
        "duplicates": sum(1 for row in rows if row.duplicate_status != DuplicateStatus.UNIQUE),
        "skipped": sum(1 for row in rows if row.user_action == UserAction.SKIP),
    }


def _set_batch_counts(batch: ImportBatch, rows: list[StagedImportRow]) -> None:
    counts = _row_counts(rows)
    batch.row_count = len(rows)
    batch.valid_row_count = counts["valid"]
    batch.warning_count = counts["warnings"]
    batch.error_count = counts["errors"]
    batch.duplicate_row_count = counts["duplicates"]
    batch.skipped_row_count = counts["skipped"]


def _stage_rows(
    db: Session,
    *,
    batch: ImportBatch,
    reader: csv.DictReader,
    mapping: dict[str, str | None],
    account_id: str | None,
) -> list[StagedImportRow]:
    staged_rows: list[StagedImportRow] = []
    normalized_records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
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
        staged_rows.append(staged)
        normalized_records.append(normalized)
    db.flush()
    _set_batch_counts(batch, staged_rows)
    batch.normalized_file_path = str(_write_normalized(batch.id, normalized_records))
    return staged_rows


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

    _stage_rows(db, batch=batch, reader=reader, mapping=mapping, account_id=account_id)
    detect_transfers(db, batch)
    record_audit(db, entity_type="import", entity_id=batch.id, action="stage", after=batch, source="import")
    return batch


def remap_batch(db: Session, batch: ImportBatch, mapping: dict[str, str | None]) -> ImportBatch:
    if batch.status in {ImportStatus.COMMITTED, ImportStatus.ROLLED_BACK}:
        raise HTTPException(status_code=409, detail="Committed or rolled back imports cannot be remapped.")
    original = Path(batch.original_file_path)
    if not original.exists():
        raise HTTPException(status_code=404, detail="Original CSV file is missing; remap cannot safely reparse rows.")
    before = as_dict(batch)
    preset = db.get(ImportMappingPreset, batch.mapping_preset_id) if batch.mapping_preset_id else None
    if preset:
        preset.version += 1
        preset.mapping_json = mapping
        batch.mapping_preset_version = preset.version
    db.execute(delete(StagedImportRow).where(StagedImportRow.import_batch_id == batch.id))
    text = original.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(StringIO(text))
    _stage_rows(db, batch=batch, reader=reader, mapping=mapping, account_id=batch.account_id)
    batch.status = ImportStatus.STAGED
    db.expire(batch, ["staged_rows"])
    detect_transfers(db, batch)
    record_audit(db, entity_type="import", entity_id=batch.id, action="remap", before=before, after=batch, source="import")
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
        if row.user_action == UserAction.SKIP:
            row.validation_status = StagedRowStatus.SKIPPED
            skipped_count += 1
            warning_count += 1 if warnings else 0
            continue
        row.validation_status = StagedRowStatus.ERROR if errors else (StagedRowStatus.WARNING if warnings else StagedRowStatus.VALID)
        error_count += 1 if errors else 0
        warning_count += 1 if warnings else 0
        valid_count += 1 if not errors else 0
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


TRANSFER_KEYWORDS = {
    "transfer",
    "payment",
    "pay",
    "ach",
    "autopay",
    "card",
    "credit card",
    "brokerage",
    "schwab",
    "vanguard",
    "fidelity",
    "hsa",
    "contribution",
}


def _description_has_transfer_context(*descriptions: str | None) -> bool:
    text = " ".join(description or "" for description in descriptions).lower()
    return any(keyword in text for keyword in TRANSFER_KEYWORDS)


def _account_transfer_bonus(db: Session, account_id: str | None, other_account_id: str | None) -> int:
    if not account_id or not other_account_id or account_id == other_account_id:
        return 0
    account = db.get(Account, account_id)
    other = db.get(Account, other_account_id)
    if not account or not other:
        return 0
    account_types = {account.account_type, other.account_type}
    if account_types & {"credit_card", "brokerage", "retirement", "hsa", "crypto_exchange", "crypto_wallet", "liability"}:
        return 8
    return 2


def _transfer_score(
    db: Session,
    *,
    normalized: dict[str, Any],
    other_account_id: str | None,
    other_description: str | None,
    other_date: date,
    other_transaction_type: str | None = None,
) -> tuple[int, str]:
    txn_date = date.fromisoformat(normalized["transaction_date"])
    day_delta = abs((txn_date - other_date).days)
    score = 70
    bases = ["equal_opposite_amount"]
    if day_delta <= 1:
        score += 15
        bases.append("one_day_window")
    else:
        score += 5
        bases.append("three_day_window")
    if _description_has_transfer_context(normalized.get("original_description"), other_description):
        score += 12
        bases.append("transfer_context")
    score += _account_transfer_bonus(db, normalized.get("account_id"), other_account_id)
    if other_transaction_type == "transfer" or normalized.get("transaction_type") == "transfer":
        score += 8
        bases.append("transfer_type")
    return min(score, 99), "_".join(bases)


def _side(amount_cents: int) -> str:
    return "outflow" if amount_cents < 0 else "inflow"


def _add_transfer_member(
    db: Session,
    *,
    link: TransferLink,
    account_id: str,
    amount_cents: int,
    staged_row_id: str | None = None,
    transaction_id: str | None = None,
) -> None:
    db.add(
        TransferLinkMember(
            transfer_link_id=link.id,
            transaction_id=transaction_id,
            staged_row_id=staged_row_id,
            account_id=account_id,
            amount_cents=amount_cents,
            side=_side(amount_cents),
        )
    )


def _transfer_member_exists(db: Session, link_id: str, *, transaction_id: str | None = None, staged_row_id: str | None = None) -> bool:
    query = select(TransferLinkMember.id).where(TransferLinkMember.transfer_link_id == link_id)
    if transaction_id:
        query = query.where(TransferLinkMember.transaction_id == transaction_id)
    if staged_row_id:
        query = query.where(TransferLinkMember.staged_row_id == staged_row_id)
    return bool(db.scalar(query.limit(1)))


def _set_transfer_candidate(
    row: StagedImportRow,
    *,
    link: TransferLink,
    candidate_type: str,
    candidate_id: str,
    score: int,
    basis: str,
) -> None:
    status = TransferStatus.CONFIRMED_TRANSFER if score >= 95 else TransferStatus.SUGGESTED_TRANSFER
    row.transfer_status = status
    normalized = dict(row.normalized_json)
    normalized["transfer_candidate"] = {
        "transfer_link_id": link.id,
        "candidate_type": candidate_type,
        "candidate_id": candidate_id,
        "confidence_score": score,
        "match_basis": basis,
        "status": "confirmed" if score >= 95 else "suggested",
    }
    row.normalized_json = normalized
    warnings = list(row.warnings_json or [])
    label = "Confirmed high-confidence transfer pair." if score >= 95 else "Suggested transfer pair needs review."
    if label not in warnings:
        warnings.append(label)
    row.warnings_json = warnings


def detect_transfers(db: Session, batch: ImportBatch) -> ImportBatch:
    if batch.status in {ImportStatus.COMMITTED, ImportStatus.ROLLED_BACK}:
        raise HTTPException(status_code=409, detail="Committed or rolled back imports cannot be re-detected.")
    rows = [row for row in batch.staged_rows if row.validation_status != StagedRowStatus.ERROR]
    staged_ids = [row.id for row in rows if row.id]
    if staged_ids:
        link_ids = list(
            db.scalars(
                select(TransferLinkMember.transfer_link_id).where(TransferLinkMember.staged_row_id.in_(staged_ids))
            )
        )
        for link_id in set(link_ids):
            link = db.get(TransferLink, link_id)
            if link and link.created_by == "system" and link.status in {"suggested", "confirmed"}:
                db.delete(link)
        db.flush()
    for row in rows:
        if row.transfer_status != TransferStatus.REJECTED_TRANSFER:
            row.transfer_status = TransferStatus.NOT_TRANSFER
            normalized = dict(row.normalized_json)
            normalized.pop("transfer_candidate", None)
            row.normalized_json = normalized
    paired_keys: set[tuple[str, str]] = set()
    for row in rows:
        if row.transfer_status == TransferStatus.REJECTED_TRANSFER:
            continue
        normalized = row.normalized_json
        amount = normalized.get("amount_cents")
        txn_date_raw = normalized.get("transaction_date")
        if amount is None or txn_date_raw is None:
            continue
        txn_date = date.fromisoformat(txn_date_raw)
        candidates: list[tuple[str, str, int, str, dict[str, Any] | Transaction]] = []
        for other in rows:
            if other.id == row.id:
                continue
            other_norm = other.normalized_json
            if other_norm.get("amount_cents") == -amount and other_norm.get("account_id") != normalized.get("account_id"):
                other_date = date.fromisoformat(other_norm["transaction_date"])
                day_delta = abs((txn_date - other_date).days)
                if day_delta <= 3:
                    score, basis = _transfer_score(
                        db,
                        normalized=normalized,
                        other_account_id=other_norm.get("account_id"),
                        other_description=other_norm.get("original_description"),
                        other_date=other_date,
                        other_transaction_type=other_norm.get("transaction_type"),
                    )
                    candidates.append(("staged_row", other.id, score, basis, other_norm))
        existing = db.scalars(
            select(Transaction).where(
                Transaction.amount_cents == -amount,
                Transaction.transaction_date >= date.fromordinal(txn_date.toordinal() - 3),
                Transaction.transaction_date <= date.fromordinal(txn_date.toordinal() + 3),
                Transaction.account_id != normalized.get("account_id"),
            )
        )
        for txn in existing:
            score, basis = _transfer_score(
                db,
                normalized=normalized,
                other_account_id=txn.account_id,
                other_description=txn.original_description,
                other_date=txn.transaction_date,
                other_transaction_type=txn.transaction_type,
            )
            candidates.append(("transaction", txn.id, score, basis, txn))
        if candidates:
            candidate_type, candidate_id, score, basis, candidate = max(candidates, key=lambda item: item[2])
            pair_key = tuple(sorted([f"staged:{row.id}", f"{candidate_type}:{candidate_id}"]))
            if pair_key in paired_keys:
                continue
            paired_keys.add(pair_key)
            status = "confirmed" if score >= 95 else "suggested"
            link = TransferLink(
                confidence_score=str(Decimal(score) / Decimal("100")),
                match_basis=basis,
                status=status,
                created_by="system",
                confirmed_at=utc_now() if status == "confirmed" else None,
            )
            db.add(link)
            db.flush()
            _add_transfer_member(
                db,
                link=link,
                account_id=normalized["account_id"],
                amount_cents=amount,
                staged_row_id=row.id,
            )
            _set_transfer_candidate(
                row,
                link=link,
                candidate_type=candidate_type,
                candidate_id=candidate_id,
                score=score,
                basis=basis,
            )
            if candidate_type == "staged_row":
                other = next(candidate_row for candidate_row in rows if candidate_row.id == candidate_id)
                other_norm = other.normalized_json
                _add_transfer_member(
                    db,
                    link=link,
                    account_id=other_norm["account_id"],
                    amount_cents=other_norm["amount_cents"],
                    staged_row_id=other.id,
                )
                _set_transfer_candidate(
                    other,
                    link=link,
                    candidate_type="staged_row",
                    candidate_id=row.id,
                    score=score,
                    basis=basis,
                )
            elif isinstance(candidate, Transaction):
                _add_transfer_member(
                    db,
                    link=link,
                    account_id=candidate.account_id,
                    amount_cents=candidate.amount_cents,
                    transaction_id=candidate.id,
                )
    db.flush()
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
        if payload.user_action is None:
            row.user_action = UserAction.EDIT
        errors: list[str] = []
        warnings = list(row.warnings_json or [])
        normalized = payload.normalized_json
        if normalized.get("amount_cents") is None:
            errors.append("Missing amount; missing money cannot be treated as zero.")
        if normalized.get("transaction_date") is None:
            errors.append("Invalid or missing transaction date.")
        if normalized.get("account_id") is None:
            errors.append("Missing target account.")
        if not normalized.get("original_description"):
            errors.append("Missing description.")
        row.errors_json = errors or None
        row.warnings_json = warnings or None
        row.validation_status = StagedRowStatus.ERROR if errors else (StagedRowStatus.WARNING if warnings else StagedRowStatus.VALID)
    if payload.duplicate_status == DuplicateStatus.CONFIRMED_DUPLICATE:
        row.user_action = UserAction.SKIP
    elif payload.duplicate_status == DuplicateStatus.IGNORED_DUPLICATE and row.user_action == UserAction.SKIP:
        row.user_action = UserAction.IMPORT
    if payload.transfer_status == TransferStatus.REJECTED_TRANSFER:
        normalized = dict(row.normalized_json)
        normalized.pop("transfer_candidate", None)
        row.normalized_json = normalized
    if row.user_action == UserAction.SKIP:
        row.validation_status = StagedRowStatus.SKIPPED
    db.flush()
    record_audit(db, entity_type="staged_import_row", entity_id=row.id, action="update", before=before, after=row)
    db.flush()
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
        for row in batch.staged_rows:
            if row.user_action == UserAction.SKIP or row.validation_status in {StagedRowStatus.ERROR, StagedRowStatus.SKIPPED}:
                continue
            if row.duplicate_status in {DuplicateStatus.DUPLICATE, DuplicateStatus.CONFIRMED_DUPLICATE}:
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
            candidate = normalized.get("transfer_candidate") if row.transfer_status != TransferStatus.REJECTED_TRANSFER else None
            link = db.get(TransferLink, candidate.get("transfer_link_id")) if candidate else None
            if row.transfer_status == TransferStatus.CONFIRMED_TRANSFER and link:
                link.status = "confirmed"
                link.confirmed_at = link.confirmed_at or utc_now()
                txn.transfer_link_id = link.id
            elif row.transfer_status == TransferStatus.SUGGESTED_TRANSFER and link:
                txn.transfer_link_id = link.id
            db.add(txn)
            db.flush()
            if link and not _transfer_member_exists(db, link.id, transaction_id=txn.id):
                _add_transfer_member(
                    db,
                    link=link,
                    transaction_id=txn.id,
                    account_id=txn.account_id,
                    amount_cents=txn.amount_cents,
                )
            if link and row.transfer_status == TransferStatus.CONFIRMED_TRANSFER and candidate.get("candidate_type") == "transaction":
                existing_txn = db.get(Transaction, candidate.get("candidate_id"))
                if existing_txn:
                    before_existing = as_dict(existing_txn)
                    existing_txn.transfer_status = TransferStatus.CONFIRMED_TRANSFER
                    existing_txn.transfer_link_id = link.id
                    if not _transfer_member_exists(db, link.id, transaction_id=existing_txn.id):
                        _add_transfer_member(
                            db,
                            link=link,
                            transaction_id=existing_txn.id,
                            account_id=existing_txn.account_id,
                            amount_cents=existing_txn.amount_cents,
                        )
                    manifest["updated"].append({"entity_type": "transaction", "entity_id": existing_txn.id, "before": before_existing})
                    record_audit(
                        db,
                        entity_type="transaction",
                        entity_id=existing_txn.id,
                        action="update",
                        before=before_existing,
                        after=existing_txn,
                        source="import",
                        source_id=batch.id,
                    )
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
    for item in reversed(manifest.get("updated", [])):
        if item["entity_type"] == "transaction":
            txn = db.get(Transaction, item["entity_id"])
            before_state = item.get("before") or {}
            if txn is None or not before_state:
                continue
            before = as_dict(txn)
            for key in ["transfer_status", "transfer_link_id", "review_status", "duplicate_status", "notes"]:
                if key in before_state:
                    setattr(txn, key, before_state[key])
            record_audit(
                db,
                entity_type="transaction",
                entity_id=txn.id,
                action="rollback_update",
                before=before,
                after=txn,
                source="import",
                source_id=batch.id,
            )
    batch.status = ImportStatus.ROLLED_BACK
    batch.rolled_back_at = utc_now()
    record_audit(db, entity_type="import", entity_id=batch.id, action="rollback", after=batch, source="import", source_id=batch.id)
    recompute_data_quality(db)
    db.flush()
    return batch
