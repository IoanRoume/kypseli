from abc import ABC, abstractmethod
from file_organizer.core.models import FileInfo, ExtractedContent

class BaseExtractor(ABC):
    supported_extensions: list[str] = []

    def can_handle(self, file_info: FileInfo) -> bool:
        file_extension = file_info.extension
        if file_extension in self.supported_extensions:
            return True
        return False
    
    @abstractmethod
    def extract(self, file_info: FileInfo, max_chars: int = 5000) -> ExtractedContent:
        pass


