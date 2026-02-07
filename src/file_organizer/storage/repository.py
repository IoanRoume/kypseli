import json
from datetime import datetime
from typing import Optional
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy import desc

from file_organizer.storage.models import Configuration, OperationHistory
from file_organizer.core.models import (
    FoldersToClassify,
    FolderObject,
    PendingOperation,
    OperationMode
)


class ConfigurationRepository:
    """Repository for managing saved configurations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def _folders_to_json(self, folders_config: FoldersToClassify) -> str:
        """Convert FoldersToClassify to JSON string."""
        data = {
            "folders": [
                {
                    "folder_path": str(folder.folder_path),
                    "description": folder.description
                }
                for folder in folders_config.folders
            ],
            "default_folder": str(folders_config.default_folder)
        }
        return json.dumps(data)
    
    def _json_to_folders(self, json_str: str) -> FoldersToClassify:
        """Convert JSON string back to FoldersToClassify."""
        data = json.loads(json_str)
        return FoldersToClassify(
            folders=[
                FolderObject(
                    folder_path=Path(f["folder_path"]),
                    description=f["description"]
                )
                for f in data["folders"]
            ],
            default_folder=Path(data["default_folder"])
        )
    
    def save(
        self,
        name: str,
        folders_config: FoldersToClassify,
        description: Optional[str] = None
    ) -> Configuration:
        """Save a new configuration or update existing one."""
        
        existing = self.get_by_name(name)
        
        if existing:
            # Update existing
            existing.folders_json = self._folders_to_json(folders_config)
            existing.description = description
            existing.updated_at = datetime.now()
            config = existing
        else:
            # Create new
            config = Configuration(
                name=name,
                description=description,
                folders_json=self._folders_to_json(folders_config)
            )
            self.session.add(config)
        
        self.session.commit()
        return config
    
    def get_by_name(self, name: str) -> Optional[Configuration]:
        """Get a configuration by name."""
        return self.session.query(Configuration).filter(
            Configuration.name == name
        ).first()
    
    def get_folders_config(self, name: str) -> Optional[FoldersToClassify]:
        """Get the FoldersToClassify object for a configuration."""
        config = self.get_by_name(name)
        if config:
            return self._json_to_folders(config.folders_json)
        return None
    
    def list_all(self) -> list[Configuration]:
        """List all saved configurations."""
        return self.session.query(Configuration).order_by(
            desc(Configuration.updated_at)
        ).all()
    
    def delete(self, name: str) -> bool:
        """Delete a configuration by name."""
        config = self.get_by_name(name)
        if config:
            self.session.delete(config)
            self.session.commit()
            return True
        return False


class HistoryRepository:
    """Repository for managing operation history."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def log_operation(
        self,
        operation: PendingOperation,
        status: str,
        error_message: Optional[str] = None,
        configuration_name: Optional[str] = None
    ) -> OperationHistory:
        """Log an executed operation."""
        
        history = OperationHistory(
            file_name=operation.file_info.name,
            source_path=str(operation.file_info.path),
            destination_path=str(operation.classification.classified_path),
            file_size=operation.file_info.size,
            file_extension=operation.file_info.extension,
            category=operation.classification.category,
            confidence=operation.classification.confidence,
            reasoning=operation.classification.reasoning,
            operation_mode=operation.operation_mode.value,
            status=status,
            error_message=error_message,
            configuration_name=configuration_name
        )
        
        self.session.add(history)
        self.session.commit()
        return history
    
    def log_batch(
        self,
        operations: list[PendingOperation],
        results: list[tuple[PendingOperation, str, Optional[str]]],
        configuration_name: Optional[str] = None
    ) -> list[OperationHistory]:
        """Log multiple operations at once."""
        
        histories = []
        for operation, status, error_message in results:
            history = OperationHistory(
                file_name=operation.file_info.name,
                source_path=str(operation.file_info.path),
                destination_path=str(operation.classification.classified_path),
                file_size=operation.file_info.size,
                file_extension=operation.file_info.extension,
                category=operation.classification.category,
                confidence=operation.classification.confidence,
                reasoning=operation.classification.reasoning,
                operation_mode=operation.operation_mode.value,
                status=status,
                error_message=error_message,
                configuration_name=configuration_name
            )
            self.session.add(history)
            histories.append(history)
        
        self.session.commit()
        return histories
    
    def get_recent(self, limit: int = 50) -> list[OperationHistory]:
        """Get recent operations."""
        return self.session.query(OperationHistory).order_by(
            desc(OperationHistory.executed_at)
        ).limit(limit).all()
    
    def search_by_filename(self, filename: str) -> list[OperationHistory]:
        """Search for operations by filename (partial match)."""
        return self.session.query(OperationHistory).filter(
            OperationHistory.file_name.ilike(f"%{filename}%")
        ).order_by(desc(OperationHistory.executed_at)).all()
    
    def search_by_source_path(self, path: str) -> list[OperationHistory]:
        """Search for operations by source path (partial match)."""
        return self.session.query(OperationHistory).filter(
            OperationHistory.source_path.ilike(f"%{path}%")
        ).order_by(desc(OperationHistory.executed_at)).all()
    
    def get_by_status(self, status: str, limit: int = 50) -> list[OperationHistory]:
        """Get operations by status."""
        return self.session.query(OperationHistory).filter(
            OperationHistory.status == status
        ).order_by(desc(OperationHistory.executed_at)).limit(limit).all()
    
    def get_stats(self) -> dict:
        """Get summary statistics."""
        total = self.session.query(OperationHistory).count()
        successful = self.session.query(OperationHistory).filter(
            OperationHistory.status == "success"
        ).count()
        failed = self.session.query(OperationHistory).filter(
            OperationHistory.status == "failed"
        ).count()
        skipped = self.session.query(OperationHistory).filter(
            OperationHistory.status == "skipped"
        ).count()
        
        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "skipped": skipped
        }