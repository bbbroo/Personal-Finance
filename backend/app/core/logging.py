from __future__ import annotations

import logging

from app.core.paths import LOGS_DIR, ensure_data_dirs


def configure_logging() -> None:
    ensure_data_dirs()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOGS_DIR / "backend.log", encoding="utf-8"),
        ],
    )
