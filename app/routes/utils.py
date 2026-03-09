from __future__ import annotations

from typing import Any, Dict, Generator

from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.models.base import Base


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def to_dict(obj: Base) -> Dict[str, Any]:
    return {col.name: getattr(obj, col.name) for col in obj.__table__.columns}  # type: ignore[attr-defined]


# Fields that must never be written via apply_updates (set only through explicit
# business logic, e.g. the dedicated archive/restore endpoints).
_READONLY_FIELDS = frozenset({
    'id',
    'deleted_at',
    'created_at',
    'updated_at',
})


def apply_updates(obj: Base, payload: Dict[str, Any]) -> None:
    cols = {c.name for c in obj.__table__.columns}  # type: ignore[attr-defined]
    for k, v in payload.items():
        if k in _READONLY_FIELDS:
            continue  # silently ignore read-only fields
        if k in cols:
            # Convert status, payment_status, and vehicle_class to uppercase for enum compatibility
            if k in ('status', 'payment_status', 'vehicle_class') and isinstance(v, str):
                v = v.upper()
            setattr(obj, k, v)
