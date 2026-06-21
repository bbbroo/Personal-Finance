from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = ROOT_DIR / "backend"
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "finance.sqlite3"

IMPORTS_DIR = DATA_DIR / "imports"
ORIGINAL_IMPORTS_DIR = IMPORTS_DIR / "originals"
NORMALIZED_IMPORTS_DIR = IMPORTS_DIR / "normalized"
IMPORT_LOGS_DIR = IMPORTS_DIR / "logs"
BACKUPS_DIR = DATA_DIR / "backups"
PRE_IMPORT_BACKUPS_DIR = BACKUPS_DIR / "pre_import"
DAILY_BACKUPS_DIR = BACKUPS_DIR / "daily"
PRE_RESTORE_BACKUPS_DIR = BACKUPS_DIR / "pre_restore"
EXPORTS_DIR = DATA_DIR / "exports"
SECRETS_DIR = DATA_DIR / "secrets"
LOGS_DIR = DATA_DIR / "logs"


def ensure_data_dirs() -> None:
    for path in [
        DATA_DIR,
        ORIGINAL_IMPORTS_DIR,
        NORMALIZED_IMPORTS_DIR,
        IMPORT_LOGS_DIR,
        PRE_IMPORT_BACKUPS_DIR,
        DAILY_BACKUPS_DIR,
        PRE_RESTORE_BACKUPS_DIR,
        EXPORTS_DIR,
        SECRETS_DIR,
        LOGS_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
