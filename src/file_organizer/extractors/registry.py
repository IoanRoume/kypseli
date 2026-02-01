from file_organizer.extractors.base import BaseExtractor
from file_organizer.core.models import FileInfo

class ExtractorRegistry:
    def __init__(self):
        self._extractors: list[BaseExtractor] = []

    def register(self, extractor: BaseExtractor):
        if extractor not in self._extractors:
            self._extractors.append(extractor)
            return "Extractor was successfully Added"
        else:
            return "Extractor insertion was not successful"
        
    def get_extractor(self, file_info: FileInfo) -> BaseExtractor | None:
        for extractor in self._extractors:
            if extractor.can_handle(file_info):
                return extractor
        return None
