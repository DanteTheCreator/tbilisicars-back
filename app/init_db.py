from __future__ import annotations

from app.core.db import engine
from app.models import Base  # imports all models via package __init__


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
