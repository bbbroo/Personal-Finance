from __future__ import annotations

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.routes import goals as goal_routes
from app.models.domain import AuditLog, Goal, GoalAccountLink
from app.tests.factories import account


def test_goal_link_create_delete_and_list_are_audited(db):
    acct = account(db, "Checking")
    goal = Goal(name="Emergency Fund", goal_type="savings", target_cents=1000000, current_manual_cents=250000)
    db.add(goal)
    db.flush()

    link = goal_routes.add_link(goal.id, {"account_id": acct.id, "allocation_percent": "100"}, db=db)
    links = goal_routes.goal_links(db=db)
    deleted = goal_routes.delete_link(goal.id, link["id"], db=db)

    assert any(row["id"] == link["id"] for row in links)
    assert deleted == {"deleted": True}
    create_audit = db.scalar(select(AuditLog).where(AuditLog.entity_type == "goal_account_link", AuditLog.action == "create"))
    delete_audit = db.scalar(select(AuditLog).where(AuditLog.entity_type == "goal_account_link", AuditLog.action == "delete"))
    assert create_audit is not None
    assert create_audit.after_json["account_id"] == acct.id
    assert delete_audit is not None
    assert delete_audit.before_json["account_id"] == acct.id


def test_goal_link_delete_rejects_wrong_goal_id(db):
    acct = account(db, "Checking")
    goal = Goal(name="Emergency Fund", goal_type="savings", target_cents=1000000)
    other_goal = Goal(name="Vacation", goal_type="savings", target_cents=500000)
    db.add_all([goal, other_goal])
    db.flush()
    link = GoalAccountLink(goal_id=goal.id, account_id=acct.id, allocation_percent="100")
    db.add(link)
    db.flush()

    with pytest.raises(HTTPException) as exc:
        goal_routes.delete_link(other_goal.id, link.id, db=db)

    assert exc.value.status_code == 404
