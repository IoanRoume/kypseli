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
    file_list: list[str]
    file_types: dict[str, int] 


class AnalysisResult(BaseModel):
    file_info: FileInfo
    analysis_type: str 
    analyzed_at: datetime
    
    tabular: Optional[TabularAnalysis] = None
    document: Optional[DocumentAnalysis] = None
    code: Optional[CodeAnalysis] = None
    image: Optional[ImageAnalysis] = None
    archive: Optional[ArchiveAnalysis] = None
    
    error: Optional[str] = None
    ai_description: Optional[str] = None 