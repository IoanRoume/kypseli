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
