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
import cv2
import datetime



class VideoExtractor(BaseExtractor):
    supported_extensions = [
        ".mp4", ".webm",
        ".mov", ".m4v",
        ".avi", ".wmv",
        ".mkv", ".flv"
    ]

    def extract(self, file_info: FileInfo, max_chars: int = 7000) -> ExtractedContent:
        file_path = str(file_info.path) # OpenCV requires string path, not Path object
        
        if not file_info.path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            video = cv2.VideoCapture(file_path)
            
            if not video.isOpened():
                return ExtractedContent(
                    file_info=file_info,
                    content="Error: Could not open video file (corrupt or unsupported codec).",
                    extraction_method="failed"
                )

            # Extract Raw Properties
            width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = video.get(cv2.CAP_PROP_FPS)
            frame_count = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Calculate Duration
            duration_seconds = frame_count / fps if fps > 0 else 0
            formatted_duration = str(datetime.timedelta(seconds=int(duration_seconds)))

            # Build Summary
            details = [
                f"--- Video Metadata ---",
                f"Resolution: {width}x{height}",
                f"Duration: {formatted_duration}",
                f"FPS: {fps:.2f}",
                f"Total Frames: {frame_count}",
                f"Codec Info: (FourCC): {int(video.get(cv2.CAP_PROP_FOURCC))}"
            ]

            video.release()
            content = "\n".join(details)

        except Exception as e:
            return ExtractedContent(
                file_info=file_info,
                content=f"Error reading video metadata: {str(e)}",
                extraction_method="failed"
            )

        return ExtractedContent(
            file_info=file_info,
            content=content[:max_chars],
            extraction_method="video_metadata"
        )
