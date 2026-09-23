"""
SIF Sentinel — Database Session & Engine Configuration (Phase 9)
================================================================

Configures SQLAlchemy 2.0 engine, SessionLocal factory, and Base declarative model.
Supports PostgreSQL connection strings from environment variables, with graceful
SQLite fallback for local unit tests and developer environments.
"""

from __future__ import annotations

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

# Determine connect args (e.g. check_same_thread for SQLite)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# Declarative Base for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields an active database session
    and ensures clean closure after request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize all registered SQLAlchemy tables."""
    # Import models so they register with Base.metadata
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
