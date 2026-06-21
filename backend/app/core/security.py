from __future__ import annotations

import hashlib
from pathlib import Path


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def normalized_hash(parts: list[str | int | None]) -> str:
    payload = "|".join("" if part is None else str(part).strip().lower() for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
