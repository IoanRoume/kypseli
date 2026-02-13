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
from pathlib import Path
import datetime
from file_organizer.core.models import FileInfo, ContentType

class DirectoryScanner:

    EXTENSION_MAP = {
        # --- Tabular (Data & Spreadsheets) ---
        '.csv': ContentType.TABULAR,
        '.tsv': ContentType.TABULAR,
        '.xlsx': ContentType.TABULAR,
        '.xls': ContentType.TABULAR,
        '.ods': ContentType.TABULAR,
        '.parquet': ContentType.TABULAR,
        '.feather': ContentType.TABULAR,
        '.pkl': ContentType.TABULAR,
        '.orc': ContentType.TABULAR,
        '.dta': ContentType.TABULAR, 
        '.sas7bdat': ContentType.TABULAR, 
        '.h5': ContentType.TABULAR,  
        '.xz': ContentType.TABULAR, 

        # --- Text (Code, Config, Web) ---
        '.txt': ContentType.TEXT,
        '.md': ContentType.TEXT,
        '.py': ContentType.TEXT,
        '.js': ContentType.TEXT,
        '.html': ContentType.TEXT,
        '.css': ContentType.TEXT,
        '.json': ContentType.TEXT,
        '.xml': ContentType.TEXT,
        '.yaml': ContentType.TEXT,
        '.yml': ContentType.TEXT,
        '.ini': ContentType.TEXT,
        '.log': ContentType.TEXT,
        '.sql': ContentType.TEXT,
        '.sh': ContentType.TEXT,
        '.bat': ContentType.TEXT,
        '.c': ContentType.TEXT,
        '.cpp': ContentType.TEXT,
        '.java': ContentType.TEXT,
        '.go': ContentType.TEXT,
        '.rs': ContentType.TEXT,

        # --- Document (Office, E-books) ---
        '.pdf': ContentType.DOCUMENT,
        '.docx': ContentType.DOCUMENT,
        '.doc': ContentType.DOCUMENT,
        '.rtf': ContentType.DOCUMENT,
        '.odt': ContentType.DOCUMENT,
        '.ppt': ContentType.DOCUMENT,
        '.pptx': ContentType.DOCUMENT,
        '.odp': ContentType.DOCUMENT,
        '.epub': ContentType.DOCUMENT,

        # --- Image ---
        '.png': ContentType.IMAGE,
        '.jpg': ContentType.IMAGE,
        '.jpeg': ContentType.IMAGE,
        '.gif': ContentType.IMAGE,
        '.bmp': ContentType.IMAGE,
        '.tiff': ContentType.IMAGE,
        '.tif': ContentType.IMAGE,
        '.webp': ContentType.IMAGE,
        '.svg': ContentType.IMAGE,
        '.ico': ContentType.IMAGE,
        '.heic': ContentType.IMAGE,

        # --- Video ---
        '.mp4': ContentType.VIDEO,
        '.mov': ContentType.VIDEO,
        '.avi': ContentType.VIDEO,
        '.mkv': ContentType.VIDEO,
        '.wmv': ContentType.VIDEO,
        '.flv': ContentType.VIDEO,
        '.webm': ContentType.VIDEO,
        '.m4v': ContentType.VIDEO,
        
        # --- Archive (Compressed files) ---
        '.zip': ContentType.ARCHIVE,
        '.tar': ContentType.ARCHIVE,
        '.gz': ContentType.ARCHIVE,
        '.bz2': ContentType.ARCHIVE,
        '.rar': ContentType.ARCHIVE,
        '.7z': ContentType.ARCHIVE,

        # --- Binary (Executables & Raw Data) ---
        '.bin': ContentType.BINARY,
        '.dat': ContentType.BINARY,
        '.db': ContentType.BINARY,
        '.sqlite': ContentType.BINARY,
        '.exe': ContentType.BINARY,
        '.dll': ContentType.BINARY,
        '.so': ContentType.BINARY,
        '.class': ContentType.BINARY,
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

                
