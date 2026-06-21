from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.domain import ImportBatch, ImportMappingPreset, StagedImportRow
from app.repositories.common import get_or_404
from app.schemas.common import ImportMappingPresetCreate, StagedRowUpdate
from app.services import import_service
from app.services.serialization import as_dict, as_dict_list

router = APIRouter(tags=["imports"])


@router.post("/imports/upload")
async def upload(
    file: UploadFile = File(...),
    account_id: str | None = None,
    import_type: str = "transactions",
    institution: str | None = None,
    db: Session = Depends(get_db),
):
    batch = await import_service.upload_csv(db, file=file, account_id=account_id, import_type=import_type, institution=institution)
    db.commit()
    return as_dict(batch)


@router.get("/imports")
def list_imports(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(ImportBatch).order_by(ImportBatch.created_at.desc())))


@router.get("/imports/{import_batch_id}")
def get_import(import_batch_id: str, db: Session = Depends(get_db)):
    return as_dict(get_or_404(db, ImportBatch, import_batch_id))


@router.post("/imports/{import_batch_id}/map")
def remap_import(import_batch_id: str, mapping: dict, db: Session = Depends(get_db)):
    batch = get_or_404(db, ImportBatch, import_batch_id)
    preset = db.get(ImportMappingPreset, batch.mapping_preset_id) if batch.mapping_preset_id else None
    if preset:
        preset.version += 1
        preset.mapping_json = mapping
        batch.mapping_preset_version = preset.version
    db.commit()
    return as_dict(batch)


@router.post("/imports/{import_batch_id}/validate")
def validate(import_batch_id: str, db: Session = Depends(get_db)):
    batch = import_service.validate_batch(db, get_or_404(db, ImportBatch, import_batch_id))
    db.commit()
    return as_dict(batch)


@router.post("/imports/{import_batch_id}/apply-rules")
def apply_rules(import_batch_id: str, db: Session = Depends(get_db)):
    batch = import_service.apply_rules_to_batch(db, get_or_404(db, ImportBatch, import_batch_id))
    db.commit()
    return as_dict(batch)


@router.post("/imports/{import_batch_id}/detect-duplicates")
def detect_duplicates(import_batch_id: str, db: Session = Depends(get_db)):
    batch = import_service.detect_duplicates(db, get_or_404(db, ImportBatch, import_batch_id))
    db.commit()
    return as_dict(batch)


@router.post("/imports/{import_batch_id}/detect-transfers")
def detect_transfers(import_batch_id: str, db: Session = Depends(get_db)):
    batch = import_service.detect_transfers(db, get_or_404(db, ImportBatch, import_batch_id))
    db.commit()
    return as_dict(batch)


@router.get("/imports/{import_batch_id}/staged-rows")
def staged_rows(import_batch_id: str, db: Session = Depends(get_db)):
    get_or_404(db, ImportBatch, import_batch_id)
    rows = db.scalars(select(StagedImportRow).where(StagedImportRow.import_batch_id == import_batch_id).order_by(StagedImportRow.row_number))
    return as_dict_list(rows)


@router.patch("/imports/{import_batch_id}/staged-rows/{row_id}")
def update_row(import_batch_id: str, row_id: str, payload: StagedRowUpdate, db: Session = Depends(get_db)):
    row = get_or_404(db, StagedImportRow, row_id)
    row = import_service.update_staged_row(db, row, payload)
    db.commit()
    return as_dict(row)


@router.post("/imports/{import_batch_id}/commit")
def commit(import_batch_id: str, db: Session = Depends(get_db)):
    batch = import_service.commit_batch(db, get_or_404(db, ImportBatch, import_batch_id))
    db.commit()
    return as_dict(batch)


@router.post("/imports/{import_batch_id}/rollback")
def rollback(import_batch_id: str, db: Session = Depends(get_db)):
    batch = import_service.rollback_batch(db, get_or_404(db, ImportBatch, import_batch_id))
    db.commit()
    return as_dict(batch)


@router.get("/import-mapping-presets")
def presets(db: Session = Depends(get_db)):
    return as_dict_list(db.scalars(select(ImportMappingPreset).order_by(ImportMappingPreset.updated_at.desc())))


@router.post("/import-mapping-presets")
def create_preset(payload: ImportMappingPresetCreate, db: Session = Depends(get_db)):
    preset = ImportMappingPreset(**payload.model_dump())
    db.add(preset)
    db.commit()
    return as_dict(preset)


@router.patch("/import-mapping-presets/{preset_id}")
def update_preset(preset_id: str, payload: dict, db: Session = Depends(get_db)):
    preset = get_or_404(db, ImportMappingPreset, preset_id)
    for key, value in payload.items():
        if hasattr(preset, key):
            setattr(preset, key, value)
    preset.version += 1
    db.commit()
    return as_dict(preset)
