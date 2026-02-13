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


class TextExtractor(BaseExtractor):
    supported_extensions = [
        ".txt", ".md", ".log",
        ".html", ".css", ".json", ".xml", ".yaml", ".yml",
        ".py", ".js", ".sql", ".sh", ".bat",
        ".c", ".cpp", ".java", ".go", ".rs",
        ".ini"
    ]


    def extract(self, file_info: FileInfo, max_chars: int = 7000) -> ExtractedContent:
        file_path = file_info.path

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = ""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(max_chars)
                
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read(max_chars)
            except Exception as e:
                return ExtractedContent(
                    file_info=file_info,
                    content=f"Error reading text file: {str(e)}",
                    extraction_method="failed"
                )

        content = content[:max_chars]

        return ExtractedContent(
            file_info=file_info,
            content=content,
            extraction_method="text_read"
        )
