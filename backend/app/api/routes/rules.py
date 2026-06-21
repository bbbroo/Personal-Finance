from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import Transaction, TransactionRule
from app.repositories.common import get_or_404
from app.schemas.common import RuleCreate
from app.services.audit_service import record_audit
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("")
def list_rules(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(TransactionRule).order_by(TransactionRule.priority)))


@router.post("")
def create_rule(payload: RuleCreate, db: Session = Depends(get_db)):
    rule = TransactionRule(**payload.model_dump())
    db.add(rule)
    db.flush()
    record_audit(db, entity_type="rule", entity_id=rule.id, action="create", after=rule)
    db.commit()
    return as_dict(rule)


@router.patch("/{rule_id}")
def update_rule(rule_id: str, payload: dict, db: Session = Depends(get_db)):
    rule = get_or_404(db, TransactionRule, rule_id)
    before = as_dict(rule)
    for key, value in payload.items():
        if hasattr(rule, key):
            setattr(rule, key, value)
    record_audit(db, entity_type="rule", entity_id=rule.id, action="update", before=before, after=rule)
    db.commit()
    return as_dict(rule)


def _matches(rule: TransactionRule, txn: Transaction) -> bool:
    merchant = (txn.merchant_name or "").lower()
    desc = (txn.original_description or "").lower()
    if rule.match_merchant_contains and rule.match_merchant_contains.lower() not in merchant:
        return False
    if rule.match_description_contains and rule.match_description_contains.lower() not in desc:
        return False
    if rule.match_account_id and rule.match_account_id != txn.account_id:
        return False
    if rule.match_amount_min_cents is not None and txn.amount_cents < rule.match_amount_min_cents:
        return False
    if rule.match_amount_max_cents is not None and txn.amount_cents > rule.match_amount_max_cents:
        return False
    return True


@router.post("/{rule_id}/preview")
def preview_rule(rule_id: str, db: Session = Depends(get_db)):
    rule = get_or_404(db, TransactionRule, rule_id)
    matches = [txn for txn in db.scalars(select(Transaction)) if _matches(rule, txn)]
    return {"match_count": len(matches), "transactions": as_dict_list(matches[:50])}


@router.post("/{rule_id}/apply")
def apply_rule(rule_id: str, db: Session = Depends(get_db)):
    rule = get_or_404(db, TransactionRule, rule_id)
    count = 0
    for txn in db.scalars(select(Transaction)):
        if not _matches(rule, txn):
            continue
        before = as_dict(txn)
        if rule.action_category_id:
            txn.category_id = rule.action_category_id
        if rule.action_merchant_name:
            txn.merchant_name = rule.action_merchant_name
        record_audit(db, entity_type="transaction", entity_id=txn.id, action="rule_apply", before=before, after=txn, source="rule", source_id=rule.id)
        count += 1
    db.commit()
    return {"applied_count": count}
