from file_organizer.extractors.base import BaseExtractor
from file_organizer.core.models import FileInfo, ExtractedContent

import pandas as pd


class CSVExtractor(BaseExtractor):
    supported_extensions = [".csv"]

    def extract(self, file_info: FileInfo, max_chars: int = 7000) -> ExtractedContent:
        file_path = file_info.path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        df = pd.read_csv(file_path, nrows=20)
        content = df.to_string()[:max_chars]
        
        return ExtractedContent(
            file_info=file_info,
            content=content,
            extraction_method="first_20_rows"
        )

