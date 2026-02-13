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
from PIL import Image, ExifTags
from pillow_heif import register_heif_opener


class ImageExtractor(BaseExtractor):
    supported_extensions = [
        '.png', '.jpg', '.jpeg', '.webp', '.gif',
        '.tiff', '.tif', '.bmp',
        '.svg', '.ico',
        '.heic' 
    ]

    register_heif_opener()


    def extract(self, file_info: FileInfo, max_chars: int = 7000) -> ExtractedContent:
        file_path = file_info.path
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            details = []
            
            # Open the image
            with Image.open(file_path) as img:
                details.append(f"Format: {img.format}")
                details.append(f"Mode: {img.mode}")
                details.append(f"Size: {img.width}x{img.height}")
                details.append(f"Megapixels: {(img.width * img.height) / 1_000_000:.2f} MP")

                exif_data = img._getexif()
                if exif_data:
                    details.append("\n--- EXIF Metadata ---")
                    for tag, value in exif_data.items():
                        tag_name = ExifTags.TAGS.get(tag, tag)
                        
                        # Filter out binary data or very long strings
                        if isinstance(value, bytes) or len(str(value)) > 100:
                            continue
                            
                        # specific formatting for interesting tags
                        if tag_name == "DateTimeOriginal":
                            details.append(f"Date Taken: {value}")
                        elif tag_name == "Make":
                            details.append(f"Camera Make: {value}")
                        elif tag_name == "Model":
                            details.append(f"Camera Model: {value}")

            if file_path.suffix.lower() == ".svg":
                with open(file_path, 'r', encoding='utf-8') as f:
                    # Read first 500 chars of SVG XML to identify it
                    details.append("\n--- SVG XML Preview ---")
                    details.append(f.read(500))

            content = "\n".join(details)

        except Exception as e:
            return ExtractedContent(
                file_info=file_info,
                content=f"Error processing image: {str(e)}",
                extraction_method="failed"
            )

        return ExtractedContent(
            file_info=file_info,
            content=content[:max_chars],
            extraction_method="image_metadata"
        )
