from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

def get_database_path() -> Path:
    """Get the path to the SQLite database file."""
    config_dir = Path.home() / ".file_organizer"
    config_dir.mkdir(exist_ok=True)
    return config_dir / "file_organizer.db"


def get_engine():
    """Create and return the database engine."""
    db_path = get_database_path()
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_database():
    """Initialize the database and create all tables."""
    from file_organizer.storage.models import Configuration, OperationHistory
    
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get a new database session."""
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()