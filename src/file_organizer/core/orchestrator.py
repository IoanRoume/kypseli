from file_organizer.core.scanner import DirectoryScanner
from file_organizer.extractors.registry import ExtractorRegistry
from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import FoldersToClassify, OperationMode, FileInfo, PendingOperation
import uuid
import datetime
from pathlib import Path


class FileOrganizer:

    def __init__(
        self,
        scanner: DirectoryScanner,
        extractor_registry: ExtractorRegistry,
        ai_provider: BaseAIProvider,
        folders_config: FoldersToClassify,
        operation_mode: OperationMode = OperationMode.DRY_RUN
    ):
        self.scanner = scanner
        self.extractor_registry = extractor_registry
        self.ai_provider = ai_provider
        self.folders_config = folders_config
        self.operation_mode = operation_mode


    def process_file(self, file_info: FileInfo) -> PendingOperation | None:
        
        extrator = self.extractor_registry.get_extractor(file_info = file_info)

        if not extrator:
            return None
        
        extracted_content = extrator.extract(file_info=file_info)

        classification_result = self.ai_provider.classify(extracted_content=extracted_content, categories = self.folders_config)

        return PendingOperation(
            id=str(uuid.uuid4()),
            file_info=file_info,
            classification = classification_result,
            operation_mode = self.operation_mode,
            created_at = datetime.datetime.now()
        )
    
    def process_directory(self, directory: Path) -> list[PendingOperation]:
        file_infos = self.scanner.scan(directory)
        if not file_infos:
            return []
        if file_infos:
            pending_operations = []
            for file_info in file_infos:
                pending_operation = self.process_file(file_info=file_info)

                if pending_operation:
                    pending_operations.append(pending_operation)
            
            return pending_operations



