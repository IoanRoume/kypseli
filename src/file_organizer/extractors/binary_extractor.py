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
import sqlite3
import binascii
import re

class BinaryExtractor(BaseExtractor):
    supported_extensions = [
        ".bin", ".dat", 
        ".exe", ".dll", ".so", ".o",
        ".class",
        ".db", ".sqlite", ".sqlite3"
    ]


    def extract(self, file_info: FileInfo, max_chars: int = 7000) -> ExtractedContent:
        file_path = file_info.path
        ext = file_path.suffix.lower()

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content_parts = []

        if ext in ['.db', '.sqlite', '.sqlite3']:
            try:
                # Connect in read-only mode
                conn = sqlite3.connect(f"file:{file_path}?mode=ro", uri=True)
                cursor = conn.cursor()
                
                # List all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                if tables:
                    content_parts.append(f"--- SQLite Database Structure ---")
                    content_parts.append(f"Tables found: {len(tables)}")
                    for table_name in tables:
                        name = table_name[0]
                        # Get row count for each table
                        try:
                            count = cursor.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                            content_parts.append(f"- Table '{name}': {count} rows")
                        except:
                            content_parts.append(f"- Table '{name}': (Access Error)")
                    
                    conn.close()
                    return ExtractedContent(
                        file_info=file_info,
                        content="\n".join(content_parts),
                        extraction_method="sqlite_inspection"
                    )
                conn.close()
            except sqlite3.Error:
                pass

        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(4096) 
            

            header_hex = binascii.hexlify(chunk[:32]).decode('ascii').upper()
            formatted_hex = " ".join(header_hex[i:i+2] for i in range(0, len(header_hex), 2))
            
            content_parts.append("--- Binary File Analysis ---")
            content_parts.append(f"Header (Hex): {formatted_hex}...")
            

            strings_found = re.findall(b"[ -~]{4,}", chunk)
            
            if strings_found:
                content_parts.append("\n--- Extracted Strings (Preview) ---")
                # Decode bytes to string
                decoded_strings = [s.decode('ascii') for s in strings_found]
                
                # Filter out noise (optional: ignore very short strings if list is huge)
                clean_strings = [s for s in decoded_strings if len(s) > 4]
                
                # Join top 50 strings
                content_parts.append("\n".join(clean_strings[:50]))
            else:
                content_parts.append("\n(No printable strings found in header)")

        except Exception as e:
            return ExtractedContent(
                file_info=file_info,
                content=f"Error reading binary file: {str(e)}",
                extraction_method="failed"
            )

        return ExtractedContent(
            file_info=file_info,
            content="\n".join(content_parts)[:max_chars],
            extraction_method="binary_analysis"
        )
