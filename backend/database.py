from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import DB_URL

engine = create_engine(DB_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 1. Used by FastAPI endpoints (app/api/routes.py)
def get_db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

# 2. Used by Background Tasks & Scripts (app/scheduler.py)
@contextmanager
def session_scope():
    """Context manager for standalone scripts and background jobs."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()