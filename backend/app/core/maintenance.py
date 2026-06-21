from __future__ import annotations

_restore_in_progress = False


def set_restore_in_progress(value: bool) -> None:
    global _restore_in_progress
    _restore_in_progress = value


def restore_in_progress() -> bool:
    return _restore_in_progress
