from abc import ABC, abstractmethod
from typing import Optional
from file_organizer.core.models import FileInfo, AnalysisResult, ContentType


class BaseAnalyzer(ABC):
    """Base class for file analyzers."""
    
    supported_content_types: list[ContentType] = []
    name: str = "base"
    
    def can_analyze(self, file_info: FileInfo) -> bool:
        """Check if this analyzer can handle the file."""
        return file_info.content_type in self.supported_content_types
    
    @abstractmethod
    def analyze(
        self,
        file_info: FileInfo,
        ai_provider=None 
    ) -> AnalysisResult:
        """Analyze the file and return results."""
        pass