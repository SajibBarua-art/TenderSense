"""Database engine and session management for PostgreSQL persistence."""
import logging
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config.settings import settings

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy ORM models
Base = declarative_base()

# Normalize database connection URL (cloud providers like Render/Supabase often provide 'postgres://' which SQLAlchemy 2.0 requires as 'postgresql://')
raw_url = settings.database_url
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

# Pure PostgreSQL engine with connection pooling and vitality check
engine = create_engine(
    raw_url,
    pool_pre_ping=True,  # Automatically tests connection vitality before execution (essential for cloud PostgreSQL)
    pool_size=10,
    max_overflow=20,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Creates database tables if they do not already exist."""
    # Import models so they are registered on Base.metadata
    import src.db.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("Initialized TenderSense database schema at %s.", settings.database_url)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
