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
from file_organizer.extractors.base import BaseExtractor
from file_organizer.core.models import FileInfo, ExtractedContent
import zipfile
import tarfile
import gzip
import datetime
from pathlib import Path

try:
    import py7zr
except ImportError:
    py7zr = None

try:
    import rarfile
except ImportError:
    rarfile = None

class ArchiveExtractor(BaseExtractor):
    supported_extensions = [
        ".zip", 
        ".tar", ".tar.gz", ".tgz", ".tar.bz2",
        ".gz", ".bz2",
        ".7z", ".rar"
    ]


    def extract(self, file_info: FileInfo, max_chars: int = 7000) -> ExtractedContent:
        file_path = file_info.path
        ext = file_path.suffix.lower()
        
        # Check if compound extension (e.g., .tar.gz)
        if file_path.name.endswith(".tar.gz") or file_path.name.endswith(".tgz"):
            ext = ".tar.gz"

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content_list = []
        
        try:
            if ext == '.zip':
                if not zipfile.is_zipfile(file_path):
                    return ExtractedContent(file_info, "Error: Not a valid zip file", "failed")
                
                with zipfile.ZipFile(file_path, 'r') as z:
                    content_list.append(f"Archive Type: ZIP")
                    content_list.append(f"File Count: {len(z.namelist())}")
                    content_list.append("\n--- Contents ---")
                    
                    for info in z.infolist()[:50]: # Limit to first 50 files to avoid spam
                        size_str = f"{info.file_size / 1024:.1f} KB"
                        date_str = datetime.datetime(*info.date_time).strftime('%Y-%m-%d')
                        content_list.append(f"[{date_str}] {info.filename} ({size_str})")

            elif ext in ['.tar', '.tar.gz', '.tgz', '.tar.bz2']:
                mode = "r:gz" if ext in ['.tar.gz', '.tgz'] else "r:bz2" if ext == '.tar.bz2' else "r"
                
                with tarfile.open(file_path, mode) as t:
                    content_list.append(f"Archive Type: TAR ({mode})")
                    content_list.append("\n--- Contents ---")
                    
                    count = 0
                    for member in t:
                        if count > 50: break
                        size_str = f"{member.size / 1024:.1f} KB"
                        content_list.append(f"{member.name} ({size_str})")
                        count += 1

            elif ext == '.7z':
                if py7zr is None:
                    return ExtractedContent(file_info, "Error: py7zr not installed", "failed")
                
                with py7zr.SevenZipFile(file_path, mode='r') as z:
                    content_list.append(f"Archive Type: 7Z")
                    content_list.append("\n--- Contents ---")
                    for fname in z.getnames()[:50]:
                        content_list.append(fname)

            elif ext == '.rar':
                if rarfile is None:
                    return ExtractedContent(file_info, "Error: rarfile lib not installed", "failed")
                
                with rarfile.RarFile(file_path) as rf:
                    content_list.append(f"Archive Type: RAR")
                    content_list.append("\n--- Contents ---")
                    for f in rf.infolist()[:50]:
                        content_list.append(f"{f.filename} ({f.file_size/1024:.1f} KB)")

            elif ext == '.gz':
                with gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                    content_list.append("Archive Type: GZIP (Single File Preview)")
                    content_list.append("\n--- Text Preview ---")
                    content_list.append(f.read(500))

            else:
                return ExtractedContent(file_info, "Unsupported archive format", "failed")

        except Exception as e:
            return ExtractedContent(
                file_info=file_info,
                content=f"Error reading archive: {str(e)}",
                extraction_method="failed"
            )

        # Convert list to string
        final_content = "\n".join(content_list)
        
        return ExtractedContent(
            file_info=file_info,
            content=final_content[:max_chars],
            extraction_method="archive_listing"
        )
