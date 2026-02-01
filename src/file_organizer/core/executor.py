
from file_organizer.core.models import PendingOperation, OperationMode
import shutil

class OperationExecutor:

    def execute(self, operation: PendingOperation) -> bool:
        """
        Execute a single pending operation.
        Returns True if successful, False otherwise.
        """
        operation_mode = operation.operation_mode
        file_info = operation.file_info
        classification_result = operation.classification


        if operation_mode == OperationMode.DRY_RUN:
            print(f"Operation with id: {operation.id}, Would have moved to {classification_result.classified_path}")
            return True
        
        elif operation_mode == OperationMode.MOVE:
            source_path = file_info.path
            source_name = file_info.name

            classification_result.classified_path.mkdir(parents=True, exist_ok=True)

            destination_path = classification_result.classified_path / source_name

            if destination_path.exists():
                print(f"{destination_path} Already exists, skipping move.")
                return False
            
            shutil.move(source_path, destination_path)
            print(f"File {source_name} has been moved to {destination_path}")
            return True
        
        elif operation_mode == OperationMode.COPY:
            source_path = file_info.path
            source_name = file_info.name

            classification_result.classified_path.mkdir(parents=True, exist_ok=True)

            destination_path = classification_result.classified_path / source_name

            if destination_path.exists():
                print(f"{destination_path} Already exists, skipping copy.")
                return False
            
            shutil.copy2(source_path, destination_path)
            print(f"File {source_name} has been copied to {destination_path}")
            return True


            
    
    def execute_batch(self, operations: list[PendingOperation]) -> dict:
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
                result = self.execute(operation=operation)
                if result:
                    successful += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"Error executing operation {operation.id}: {e}")
                failed += 1

        return {"total": total,
                "successful": successful,
                "skipped": skipped,
                "failed": failed}

