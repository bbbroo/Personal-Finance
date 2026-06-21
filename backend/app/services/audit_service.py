from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.domain import AuditLog
from app.services.serialization import as_dict


def record_audit(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    before=None,
    after=None,
    source: str = "manual",
    source_id: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        before_json=as_dict(before) if before is not None and not isinstance(before, dict) else before,
        after_json=as_dict(after) if after is not None and not isinstance(after, dict) else after,
        source=source,
        source_id=source_id,
    )
    db.add(entry)
    return entry
