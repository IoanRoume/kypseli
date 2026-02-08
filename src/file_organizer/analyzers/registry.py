from typing import Optional
from file_organizer.analyzers.base import BaseAnalyzer
from file_organizer.core.models import FileInfo


class AnalyzerRegistry:
    """Registry that maps file types to analyzers."""
    
    def __init__(self):
        self._analyzers: list[BaseAnalyzer] = []
    
    def register(self, analyzer: BaseAnalyzer):
        """Register an analyzer."""
        if analyzer not in self._analyzers:
            self._analyzers.append(analyzer)
    
    def get_analyzer(self, file_info: FileInfo) -> Optional[BaseAnalyzer]:
        """Find an analyzer that can handle this file."""
        for analyzer in self._analyzers:
            if analyzer.can_analyze(file_info):
                return analyzer
        return None
    
    def list_analyzers(self) -> list[str]:
        """List all registered analyzer names."""
        return [a.name for a in self._analyzers]