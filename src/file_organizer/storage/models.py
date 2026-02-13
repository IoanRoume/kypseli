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
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from sqlalchemy.sql import func
from file_organizer.storage.database import Base


class Configuration(Base):
    """Saved folder configurations that users can reuse."""
    __tablename__ = "configurations"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    folders_json = Column(Text, nullable=False)  # JSON string of FoldersToClassify
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Configuration(name='{self.name}')>"


class OperationHistory(Base):
    """Log of all file organization operations."""
    __tablename__ = "operation_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # File information
    file_name = Column(String(255), nullable=False, index=True)
    source_path = Column(Text, nullable=False)
    destination_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=True)
    file_extension = Column(String(50), nullable=True)
    
    # Classification information
    category = Column(String(100), nullable=True)
    confidence = Column(Float, nullable=True)
    reasoning = Column(Text, nullable=True)
    
    # Operation information
    operation_mode = Column(String(20), nullable=False)  # move, copy, dry_run
    status = Column(String(20), nullable=False, index=True)  # success, failed, skipped
    error_message = Column(Text, nullable=True)
    
    # Configuration used
    configuration_name = Column(String(100), nullable=True)
    
    # Timestamps
    executed_at = Column(DateTime, server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<OperationHistory(file='{self.file_name}', status='{self.status}')>"
    

class FileAnalysis(Base):
    """Stored analysis results."""
    __tablename__ = "file_analysis"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # File information
    file_name = Column(String(255), nullable=False, index=True)
    file_path = Column(Text, nullable=False)
    file_size = Column(Integer, nullable=True)
    file_extension = Column(String(50), nullable=True)
    
    # Analysis information
    analysis_type = Column(String(50), nullable=False)  # tabular, document, code, etc.
    analysis_json = Column(Text, nullable=False)  # Full analysis as JSON
    ai_description = Column(Text, nullable=True)
    
    # Timestamps
    analyzed_at = Column(DateTime, server_default=func.now(), index=True)
    
    def __repr__(self):
        return f"<FileAnalysis(file='{self.file_name}', type='{self.analysis_type}')>"