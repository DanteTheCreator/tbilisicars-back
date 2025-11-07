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


def apply_updates(obj: Base, payload: Dict[str, Any]) -> None:
    cols = {c.name for c in obj.__table__.columns}  # type: ignore[attr-defined]
    for k, v in payload.items():
        if k in cols:
            # Convert status and payment_status to uppercase for enum compatibility
            if k in ('status', 'payment_status') and isinstance(v, str):
                v = v.upper()
            setattr(obj, k, v)
