"""
SQLAlchemy database engine and session configuration.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Use .env or export DATABASE_URL before running."
    )

# Create engine with Supabase SSL configuration
use_ssl = "supabase.co" in DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args=(
        {"sslmode": "require"} if use_ssl else {}
    ),
    pool_pre_ping=True,  # Verify connections before using
    echo=False,  # Set to True for SQL logging during development
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for models
Base = declarative_base()


def get_db():
    """
    Database session dependency for FastAPI.
    Usage:
        @app.get("/endpoint")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
