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

    def __init__(self, dir_depth = 2):
        self.dir_depth = dir_depth


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
        '.sqlite3': ContentType.BINARY,
        '.exe': ContentType.BINARY,
        '.dll': ContentType.BINARY,
        '.so': ContentType.BINARY,
        '.class': ContentType.BINARY,
    }
    

    def get_content_type(self, extension: str) -> ContentType:
        return self.EXTENSION_MAP.get(extension.lower(), ContentType.BINARY)

    def scan(self, directory: Path, _depth: int = 0) -> list[FileInfo]:
        
        if not directory.exists():
            return []
        
        all_file_info = []
        
        for item in directory.iterdir():
            if item.name.startswith('.'):
                continue
            
            if item.is_dir():
                if _depth < self.dir_depth:
                    all_file_info.extend(self.scan(item, _depth + 1))
                continue
            
            if item.is_file():
                stat_info = item.stat()
                
                file_info = FileInfo(
                    path=item,
                    name=item.name,
                    size=stat_info.st_size,
                    extension=item.suffix,
                    date_created=datetime.datetime.fromtimestamp(stat_info.st_ctime),
                    date_modified=datetime.datetime.fromtimestamp(stat_info.st_mtime),
                    content_type=self.get_content_type(extension=item.suffix)
                )
                
                all_file_info.append(file_info)
        
        return all_file_info

                
