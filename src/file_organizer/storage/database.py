# Copyright 2026 Ioannis Roumeliotis
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
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