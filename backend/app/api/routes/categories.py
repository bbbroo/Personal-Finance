from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import Category, CategoryGroup
from app.repositories.common import get_or_404
from app.schemas.common import CategoryCreate, CategoryGroupCreate
from app.services.audit_service import record_audit
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(tags=["categories"])


@router.get("/category-groups")
def groups(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(CategoryGroup).order_by(CategoryGroup.sort_order, CategoryGroup.name)))


@router.post("/category-groups")
def create_group(payload: CategoryGroupCreate, db: Session = Depends(get_db)):
    group = CategoryGroup(**payload.model_dump())
    db.add(group)
    db.flush()
    record_audit(db, entity_type="category_group", entity_id=group.id, action="create", after=group)
    db.commit()
    return as_dict(group)


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(Category).order_by(Category.sort_order, Category.name)))


@router.post("/categories")
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)):
    category = Category(**payload.model_dump())
    db.add(category)
    db.flush()
    record_audit(db, entity_type="category", entity_id=category.id, action="create", after=category)
    db.commit()
    return as_dict(category)


@router.patch("/categories/{category_id}")
def update_category(category_id: str, payload: dict, db: Session = Depends(get_db)):
    category = get_or_404(db, Category, category_id)
    before = as_dict(category)
    for key, value in payload.items():
        if hasattr(category, key):
            setattr(category, key, value)
    record_audit(db, entity_type="category", entity_id=category.id, action="update", before=before, after=category)
    db.commit()
    return as_dict(category)
