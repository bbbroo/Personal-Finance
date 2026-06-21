from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import Goal, GoalAccountLink
from app.repositories.common import get_or_404
from app.schemas.common import GoalCreate
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(prefix="/goals", tags=["goals"])


@router.get("")
def goals(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(Goal).order_by(Goal.name)))


@router.post("")
def create_goal(payload: GoalCreate, db: Session = Depends(get_db)):
    goal = Goal(**payload.model_dump())
    db.add(goal)
    db.commit()
    return as_dict(goal)


@router.patch("/{goal_id}")
def update_goal(goal_id: str, payload: dict, db: Session = Depends(get_db)):
    goal = get_or_404(db, Goal, goal_id)
    for key, value in payload.items():
        if hasattr(goal, key):
            setattr(goal, key, value)
    db.commit()
    return as_dict(goal)


@router.post("/{goal_id}/links")
def add_link(goal_id: str, payload: dict, db: Session = Depends(get_db)):
    get_or_404(db, Goal, goal_id)
    link = GoalAccountLink(goal_id=goal_id, **payload)
    db.add(link)
    db.commit()
    return as_dict(link)


@router.delete("/{goal_id}/links/{link_id}")
def delete_link(goal_id: str, link_id: str, db: Session = Depends(get_db)):
    link = get_or_404(db, GoalAccountLink, link_id)
    db.delete(link)
    db.commit()
    return {"deleted": True}


@router.get("/{goal_id}/progress")
def progress(goal_id: str, db: Session = Depends(get_db)):
    goal = get_or_404(db, Goal, goal_id)
    current = goal.current_manual_cents
    percent = None if current is None or goal.target_cents == 0 else round(current / goal.target_cents, 4)
    return {
        "goal_id": goal.id,
        "current_cents": current,
        "target_cents": goal.target_cents,
        "percent_decimal": percent,
        "source": goal.progress_method,
        "confidence": "unknown" if current is None else "medium",
    }
