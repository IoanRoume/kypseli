from pathlib import Path
import datetime
from file_organizer.core.models import FileInfo, ContentType

class DirectoryScanner:

    EXTENSION_MAP = {
            # Tabular
            '.csv': ContentType.TABULAR,
            '.xlsx': ContentType.TABULAR,
            '.parquet': ContentType.TABULAR,
            '.pkl': ContentType.TABULAR,
            '.xz': ContentType.TABULAR,
            # Text
            '.txt': ContentType.TEXT,
            '.md': ContentType.TEXT,
            '.py': ContentType.TEXT,
            '.js': ContentType.TEXT,
            # Document
            '.pdf': ContentType.DOCUMENT,
            '.docx': ContentType.DOCUMENT,
            # Image
            '.png': ContentType.IMAGE,
            '.jpg': ContentType.IMAGE,
            '.jpeg': ContentType.IMAGE,
            # Video
            '.mp4': ContentType.VIDEO,
            '.mov': ContentType.VIDEO,
        }
    

    def get_content_type(self, extension: str) -> ContentType:
        return self.EXTENSION_MAP.get(extension.lower(), ContentType.BINARY)

    def scan(self, directory: Path) -> list[FileInfo] | None:

        if not directory.exists():
            return None

        all_file_info = []

        for item in directory.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                path = item
                file_name = item.name
                size = item.stat().st_size
                extension = item.suffix

                stat_info = item.stat()

                creation_time = datetime.datetime.fromtimestamp(stat_info.st_ctime)
                modified_time = datetime.datetime.fromtimestamp(stat_info.st_mtime)
                content_type = self.get_content_type(extension=extension)

                file_info = FileInfo(
                    path=path,
                    name=file_name,
                    size=size,
                    extension=extension,
                    date_created=creation_time,
                    date_modified=modified_time,
                    content_type=content_type
                )

                all_file_info.append(file_info)

        return all_file_info

                
