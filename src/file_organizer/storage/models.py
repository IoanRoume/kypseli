from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from file_organizer.storage.database import Base


class Configuration(Base):
    """Saved folder configurations that users can reuse."""
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    folders_json = Column(Text, nullable=False)  # JSON string of FoldersToClassify
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Configuration(name='{self.name}')>"


class OperationHistory(Base):
    """Log of all file organization operations."""
    __tablename__ = "operation_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # File information
    file_name = Column(String(255), nullable=False, index=True)
    source_path = Column(Text, nullable=False)
    destination_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=True)
    file_extension = Column(String(50), nullable=True)
    
    # Classification information
    category = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    
    # Operation information
    operation_mode = Column(String(20), nullable=False)  # move, copy, dry_run
    status = Column(String(20), nullable=False, index=True)  # success, failed, skipped
    error_message = Column(Text, nullable=True)
    
    # Configuration used
    configuration_name = Column(String(100), nullable=True)
    
    # Timestamps
    executed_at = Column(DateTime, server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<OperationHistory(file='{self.file_name}', status='{self.status}')>"