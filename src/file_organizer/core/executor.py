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
from file_organizer.core.models import PendingOperation, OperationMode
from file_organizer.storage.database import get_session
from file_organizer.storage.repository import HistoryRepository
import shutil
from typing import Optional


class OperationExecutor:
    
    def __init__(self, configuration_name: Optional[str] = None):
        self.configuration_name = configuration_name

    def _log_to_database(
        self,
        operation: PendingOperation,
        status: str,
        error_message: Optional[str] = None
    ):
        """Log a single operation to the database."""
        try:
            session = get_session()
            history_repo = HistoryRepository(session)
            history_repo.log_operation(
                operation=operation,
                status=status,
                error_message=error_message,
                configuration_name=self.configuration_name
            )
            session.close()
        except Exception as e:
            print(f"Warning: Failed to log operation to database: {e}")

    def execute(
        self,
        operation: PendingOperation,
        log_to_database: bool = True
    ) -> tuple[bool, str, Optional[str]]:
        """
        Execute a single pending operation.
        Returns (success, status, error_message).
        """
        operation_mode = operation.operation_mode
        file_info = operation.file_info
        classification_result = operation.classification

        success = False
        status = "failed"
        error_message = None

        if operation_mode == OperationMode.DRY_RUN:
            print(f"[DRY RUN] Would move {file_info.name} to {classification_result.classified_path}")
            success = True
            status = "skipped"
        
        elif operation_mode == OperationMode.MOVE:
            source_path = file_info.path
            source_name = file_info.name

            classification_result.classified_path.mkdir(parents=True, exist_ok=True)
            destination_path = classification_result.classified_path / source_name

            if destination_path.exists():
                print(f"{destination_path} already exists, skipping move.")
                success = False
                status = "skipped"
                error_message = "Destination file already exists"
            else:
                try:
                    shutil.move(source_path, destination_path)
                    print(f"Moved {source_name} to {destination_path}")
                    success = True
                    status = "success"
                except Exception as e:
                    success = False
                    status = "failed"
                    error_message = str(e)
        
        elif operation_mode == OperationMode.COPY:
            source_path = file_info.path
            source_name = file_info.name

            classification_result.classified_path.mkdir(parents=True, exist_ok=True)
            destination_path = classification_result.classified_path / source_name

            if destination_path.exists():
                print(f"{destination_path} already exists, skipping copy.")
                success = False
                status = "skipped"
                error_message = "Destination file already exists"
            else:
                try:
                    shutil.copy2(source_path, destination_path)
                    print(f"Copied {source_name} to {destination_path}")
                    success = True
                    status = "success"
                except Exception as e:
                    success = False
                    status = "failed"
                    error_message = str(e)
        
        else:
            status = "failed"
            error_message = "Unknown operation mode"

        # Log to database
        if log_to_database:
            self._log_to_database(operation, status, error_message)

        return (success, status, error_message)

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
        
        for operation in operations:
            try:
                # Pass log_to_database=False here since we log individually
                success, status, error_message = self.execute(
                    operation=operation,
                    log_to_database=log_to_database
                )
                
                if status == "success":
                    successful += 1
                elif status == "failed":
                    failed += 1
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"Error executing operation {operation.id}: {e}")
                failed += 1
                
                # Still log the failure
                if log_to_database:
                    self._log_to_database(operation, "failed", str(e))

        return {
            "total": total,
            "successful": successful,
            "skipped": skipped,
            "failed": failed
        }