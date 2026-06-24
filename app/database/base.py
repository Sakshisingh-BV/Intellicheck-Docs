"""SQLAlchemy declarative base and table creation utility."""

from sqlalchemy.orm import declarative_base

Base = declarative_base()


def create_tables(engine):
    """Create all registered tables if they don't already exist."""
    Base.metadata.create_all(bind=engine)
