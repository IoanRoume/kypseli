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
from abc import ABC, abstractmethod
from typing import Optional
from file_organizer.core.models import FileInfo, AnalysisResult, ContentType


class BaseAnalyzer(ABC):
    """Base class for file analyzers."""
    
    supported_content_types: list[ContentType] = []
    name: str = "base"
    
    def can_analyze(self, file_info: FileInfo) -> bool:
        """Check if this analyzer can handle the file."""
        return file_info.content_type in self.supported_content_types
    
    @abstractmethod
    def analyze(
        self,
        file_info: FileInfo,
        ai_provider=None 
    ) -> AnalysisResult:
        """Analyze the file and return results."""
        pass