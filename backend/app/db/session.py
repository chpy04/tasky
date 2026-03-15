"""SQLAlchemy session and engine setup.

Creates the engine from settings.database_url and provides a
get_db() dependency for FastAPI route injection.

Usage in a route:
    from app.db.session import get_db
    from fastapi import Depends
    from sqlalchemy.orm import Session

    @router.get(...)
    def my_route(db: Session = Depends(get_db)):
        ...
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # required for SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
