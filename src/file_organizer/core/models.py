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
from pydantic import BaseModel, BeforeValidator, ValidationError, Field
from datetime import datetime
from pathlib import Path
from typing import Optional, Annotated
from enum import Enum



class ContentType(str, Enum):
    TEXT = "text"
    TABULAR = "tabular"
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    ARCHIVE = "archive"
    BINARY = "binary"

class OperationMode(str, Enum):
    MOVE = "move"
    COPY = "copy"
    DRY_RUN = "dry_run"

class PendingStatus(str, Enum):
    WAIT = "wait"
    ACCEPT = "accept"
    DECLINE = "decline"
    


class FileInfo(BaseModel):
    path: Path
    name: str
    size: int
    extension: str
    date_created: datetime
    date_modified: datetime # Will be the same  when scanned
    content_type: ContentType

class ExtractedContent(BaseModel):
    file_info: FileInfo
    content: str
    extraction_method: str


class ClassificationResult(BaseModel):
    extracted_content: ExtractedContent
    category: Optional[str]
    confidence: Optional[float]
    reasoning: Optional[str]
    generated_summary: Optional[str]
    classified_path: Path



class PendingOperation(BaseModel):
    id: str  
    file_info: FileInfo
    classification: ClassificationResult
    operation_mode: OperationMode  
    created_at: datetime
    

class FolderObject(BaseModel):
    folder_path: Path
    description: Optional[str]

class FoldersToClassify(BaseModel):
    folders: list[FolderObject]
    default_folder: Path



class LLMClassificationResponse(BaseModel):
    folder_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str]



class TabularAnalysis(BaseModel):
    row_count: int
    column_count: int
    columns: list[str]
    dtypes: dict[str, str]  
    missing_values: dict[str, int]  
    missing_percentage: dict[str, float]  
    memory_usage: str
    numeric_summary: Optional[dict]  
    sample_values: Optional[dict[str, list]]


class DocumentAnalysis(BaseModel):
    page_count: Optional[int]
    word_count: Optional[int]
    char_count: Optional[int]
    summary: str  
    key_topics: Optional[list[str]]
    language: Optional[str]


class CodeAnalysis(BaseModel):
    language: str
    line_count: int
    import_statements: list[str]
    functions: list[str]
    classes: list[str]
    complexity_estimate: Optional[str] 
    summary: Optional[str]  


class ImageAnalysis(BaseModel):
    width: int
    height: int
    format: str
    mode: str  
    file_size: str
    has_exif: bool
    exif_data: Optional[dict]
    description: Optional[str]  

class ArchiveAnalysis(BaseModel):    
    file_count: int
    total_uncompressed_size: str
    file_list: list[str] = []
    file_types: dict[str, int] = {}
    compression_ratio: Optional[float] = None 
    has_password: Optional[bool] = False
    archive_type: Optional[str] = None
    top_level_items: list[str] = [] 
    directory_count: int = 0
    largest_file: Optional[dict] = None 
    oldest_file: Optional[str] = None
    newest_file: Optional[str] = None
    note: Optional[str] = None

class BinaryAnalysis(BaseModel):    
    binary_type: str
    format_details: Optional[str] = None  # More specific format info
    architecture: Optional[str] = None  # x86, x64, ARM, ARM64, etc.
    bit_depth: Optional[int] = None  # 32 or 64
    is_executable: bool = False
    is_library: bool = False
    is_database: bool = False
    endianness: Optional[str] = None  # Little Endian, Big Endian
    entry_point: Optional[str] = None  # Hex address
    sections: list[str] = []  # Section names or indexes
    imports: list[str] = []  # Imported functions/libraries
    exports: list[str] = []  # Exported functions
    strings_preview: list[str] = []  
    
    db_tables: list[str] = []
    db_row_counts: dict[str, int] = {}
    db_size_info: Optional[dict] = None
    
    # Metadata
    file_version: Optional[str] = None
    product_name: Optional[str] = None
    company_name: Optional[str] = None
    created_date: Optional[str] = None
    
    # Security/analysis
    entropy: Optional[float] = None  # 0-8 scale
    is_packed: Optional[bool] = None  
    magic_bytes: Optional[str] = None  

class AnalysisResult(BaseModel):
    file_info: FileInfo
    analysis_type: str 
    analyzed_at: datetime
    
    tabular: Optional[TabularAnalysis] = None
    document: Optional[DocumentAnalysis] = None
    code: Optional[CodeAnalysis] = None
    image: Optional[ImageAnalysis] = None
    archive: Optional[ArchiveAnalysis] = None
    binary: Optional[BinaryAnalysis] = None
    
    error: Optional[str] = None
    ai_description: Optional[str] = None 