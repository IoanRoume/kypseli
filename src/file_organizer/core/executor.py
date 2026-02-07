from file_organizer.core.models import PendingOperation, OperationMode
from file_organizer.storage.database import get_session
from file_organizer.storage.repository import HistoryRepository
import shutil
from typing import Optional


class OperationExecutor:
    
    def __init__(self, configuration_name: Optional[str] = None):
        self.configuration_name = configuration_name

    def execute(self, operation: PendingOperation) -> tuple[bool, str, Optional[str]]:
        """
        Execute a single pending operation.
        Returns (success, status, error_message).
        """
        operation_mode = operation.operation_mode
        file_info = operation.file_info
        classification_result = operation.classification

        if operation_mode == OperationMode.DRY_RUN:
            print(f"[DRY RUN] Would move {file_info.name} to {classification_result.classified_path}")
            return (True, "skipped", None)
        
        elif operation_mode == OperationMode.MOVE:
            source_path = file_info.path
            source_name = file_info.name

            classification_result.classified_path.mkdir(parents=True, exist_ok=True)
            destination_path = classification_result.classified_path / source_name

            if destination_path.exists():
                print(f"{destination_path} already exists, skipping move.")
                return (False, "skipped", "Destination file already exists")
            
            try:
                shutil.move(source_path, destination_path)
                print(f"Moved {source_name} to {destination_path}")
                return (True, "success", None)
            except Exception as e:
                return (False, "failed", str(e))
        
        elif operation_mode == OperationMode.COPY:
            source_path = file_info.path
            source_name = file_info.name

            classification_result.classified_path.mkdir(parents=True, exist_ok=True)
            destination_path = classification_result.classified_path / source_name

            if destination_path.exists():
                print(f"{destination_path} already exists, skipping copy.")
                return (False, "skipped", "Destination file already exists")
            
            try:
                shutil.copy2(source_path, destination_path)
                print(f"Copied {source_name} to {destination_path}")
                return (True, "success", None)
            except Exception as e:
                return (False, "failed", str(e))
        
        return (False, "failed", "Unknown operation mode")

    def execute_batch(
        self,
        operations: list[PendingOperation],
        log_to_database: bool = True
    ) -> dict:
        """
        Execute multiple operations.
        Returns a summary dict with counts of success/failed/skipped.
        """
        total = len(operations)
        successful = 0
        failed = 0
        skipped = 0
        
        results = []
        
        for operation in operations:
            success, status, error_message = self.execute(operation=operation)
            results.append((operation, status, error_message))
            
            if status == "success":
                successful += 1
            elif status == "failed":
                failed += 1
            else:
                skipped += 1
        
        # Log to database
        if log_to_database:
            try:
                session = get_session()
                history_repo = HistoryRepository(session)
                history_repo.log_batch(
                    operations=operations,
                    results=results,
                    configuration_name=self.configuration_name
                )
                session.close()
            except Exception as e:
                print(f"Warning: Failed to log operations to database: {e}")
        
        return {
            "total": total,
            "successful": successful,
            "skipped": skipped,
            "failed": failed
        }