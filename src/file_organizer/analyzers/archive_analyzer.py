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
import zipfile
import tarfile
import gzip
import bz2
import lzma
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import Counter

from file_organizer.analyzers.base import BaseAnalyzer
from file_organizer.core.models import (
    FileInfo,
    AnalysisResult,
    ArchiveAnalysis,
    ContentType
)


class ArchiveAnalyzer(BaseAnalyzer):
    """Analyzer for archive and compressed files (.zip, .tar, .gz, .rar, .7z, etc.)"""
    
    supported_content_types = [ContentType.ARCHIVE]
    name = "archive"
    
    ARCHIVE_HANDLERS = {
        '.zip': 'zip',
        '.tar': 'tar',
        '.tar.gz': 'tar_gz',
        '.tgz': 'tar_gz',
        '.tar.bz2': 'tar_bz2',
        '.tbz2': 'tar_bz2',
        '.tar.xz': 'tar_xz',
        '.txz': 'tar_xz',
        '.gz': 'gzip',
        '.bz2': 'bzip2',
        '.xz': 'xz',
        '.rar': 'rar',
        '.7z': '7z',
    }
    
    def analyze(
        self,
        file_info: FileInfo,
        ai_provider=None
    ) -> AnalysisResult:
        """Analyze an archive file."""
        
        try:
            archive_type = self._detect_archive_type(file_info.path)
            
            archive_info = self._analyze_archive(file_info.path, archive_type)
            
            archive_analysis = ArchiveAnalysis(
                file_count=archive_info['file_count'],
                total_uncompressed_size=archive_info['total_uncompressed_size'],
                file_list=archive_info['file_list'],
                file_types=archive_info['file_types'],
                compression_ratio=archive_info.get('compression_ratio'),
                has_password=archive_info.get('has_password', False),
                archive_type=archive_type,
                top_level_items=archive_info.get('top_level_items', []),
                directory_count=archive_info.get('directory_count', 0),
                largest_file=archive_info.get('largest_file'),
                oldest_file=archive_info.get('oldest_file'),
                newest_file=archive_info.get('newest_file'),
            )
            
            ai_description = None
            if ai_provider:
                ai_description = self._generate_ai_description(
                    file_info, archive_analysis, ai_provider
                )
            
            return AnalysisResult(
                file_info=file_info,
                analysis_type="archive",
                analyzed_at=datetime.now(),
                archive=archive_analysis,
                ai_description=ai_description
            )
            
        except Exception as e:
            return AnalysisResult(
                file_info=file_info,
                analysis_type="archive",
                analyzed_at=datetime.now(),
                error=str(e)
            )
    
    def _detect_archive_type(self, path: Path) -> str:
        """Detect archive type from extension and magic bytes."""
        
        name = path.name.lower()
        
        # Check compound extensions first
        if name.endswith('.tar.gz') or name.endswith('.tgz'):
            return 'tar_gz'
        elif name.endswith('.tar.bz2') or name.endswith('.tbz2'):
            return 'tar_bz2'
        elif name.endswith('.tar.xz') or name.endswith('.txz'):
            return 'tar_xz'
        
        # Check single extensions
        ext = path.suffix.lower()
        if ext in self.ARCHIVE_HANDLERS:
            return self.ARCHIVE_HANDLERS[ext]
        
        # Try magic bytes detection
        try:
            with open(path, 'rb') as f:
                header = f.read(8)
                
                if header[:4] == b'PK\x03\x04':
                    return 'zip'
                elif header[:2] == b'\x1f\x8b':
                    return 'gzip'
                elif header[:2] == b'BZ':
                    return 'bzip2'
                elif header[:6] == b'\xfd7zXZ\x00':
                    return 'xz'
                elif header[:6] == b'7z\xbc\xaf\x27\x1c':
                    return '7z'
                elif header[:6] == b'Rar!\x1a\x07':
                    return 'rar'
                else:
                    f.seek(257)
                    if f.read(5) == b'ustar':
                        return 'tar'
        except Exception:
            pass
        
        return 'unknown'
    
    def _analyze_archive(self, path: Path, archive_type: str) -> dict:
        """Analyze archive contents based on type."""
        
        handlers = {
            'zip': self._analyze_zip,
            'tar': self._analyze_tar,
            'tar_gz': self._analyze_tar_gz,
            'tar_bz2': self._analyze_tar_bz2,
            'tar_xz': self._analyze_tar_xz,
            'gzip': self._analyze_gzip,
            'bzip2': self._analyze_bzip2,
            'xz': self._analyze_xz,
            'rar': self._analyze_rar,
            '7z': self._analyze_7z,
        }
        
        handler = handlers.get(archive_type, self._analyze_unknown)
        return handler(path)
    
    def _analyze_zip(self, path: Path) -> dict:
        """Analyze ZIP archive."""
        
        file_list = []
        file_types = Counter()
        total_uncompressed = 0
        total_compressed = 0
        top_level = set()
        directories = set()
        largest_file = None
        largest_size = 0
        oldest_date = None
        newest_date = None
        has_password = False
        
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                for info in zf.infolist():
                    # Check for encryption
                    if info.flag_bits & 0x1:
                        has_password = True
                    
                    if info.is_dir():
                        directories.add(info.filename)
                        continue
                    
                    # File info
                    file_list.append(info.filename)
                    total_uncompressed += info.file_size
                    total_compressed += info.compress_size
                    
                    # Track file types
                    ext = Path(info.filename).suffix.lower() or 'no_extension'
                    file_types[ext] += 1
                    
                    # Track top-level items
                    top_item = info.filename.split('/')[0]
                    top_level.add(top_item)
                    
                    # Track largest file
                    if info.file_size > largest_size:
                        largest_size = info.file_size
                        largest_file = {
                            'name': info.filename,
                            'size': self._format_size(info.file_size)
                        }
                    
                    # Track dates
                    try:
                        file_date = datetime(*info.date_time)
                        if oldest_date is None or file_date < oldest_date:
                            oldest_date = file_date
                        if newest_date is None or file_date > newest_date:
                            newest_date = file_date
                    except Exception:
                        pass
                
        except zipfile.BadZipFile:
            raise ValueError("Invalid or corrupted ZIP file")
        
        # Calculate compression ratio
        compression_ratio = None
        if total_uncompressed > 0:
            compression_ratio = round((1 - total_compressed / total_uncompressed) * 100, 1)
        
        return {
            'file_count': len(file_list),
            'total_uncompressed_size': self._format_size(total_uncompressed),
            'file_list': file_list[:500],  # Limit to 500 files
            'file_types': dict(file_types.most_common(20)),
            'compression_ratio': compression_ratio,
            'has_password': has_password,
            'top_level_items': sorted(list(top_level))[:50],
            'directory_count': len(directories),
            'largest_file': largest_file,
            'oldest_file': oldest_date.isoformat() if oldest_date else None,
            'newest_file': newest_date.isoformat() if newest_date else None,
        }
    
    def _analyze_tar(self, path: Path) -> dict:
        """Analyze TAR archive."""
        return self._analyze_tar_common(path, 'r')
    
    def _analyze_tar_gz(self, path: Path) -> dict:
        """Analyze TAR.GZ archive."""
        return self._analyze_tar_common(path, 'r:gz')
    
    def _analyze_tar_bz2(self, path: Path) -> dict:
        """Analyze TAR.BZ2 archive."""
        return self._analyze_tar_common(path, 'r:bz2')
    
    def _analyze_tar_xz(self, path: Path) -> dict:
        """Analyze TAR.XZ archive."""
        return self._analyze_tar_common(path, 'r:xz')
    
    def _analyze_tar_common(self, path: Path, mode: str) -> dict:
        """Common TAR analysis logic."""
        
        file_list = []
        file_types = Counter()
        total_uncompressed = 0
        top_level = set()
        directories = set()
        largest_file = None
        largest_size = 0
        oldest_date = None
        newest_date = None
        
        try:
            with tarfile.open(path, mode) as tf:
                for member in tf.getmembers():
                    if member.isdir():
                        directories.add(member.name)
                        continue
                    
                    if not member.isfile():
                        continue
                    
                    # File info
                    file_list.append(member.name)
                    total_uncompressed += member.size
                    
                    # Track file types
                    ext = Path(member.name).suffix.lower() or 'no_extension'
                    file_types[ext] += 1
                    
                    # Track top-level items
                    top_item = member.name.split('/')[0]
                    top_level.add(top_item)
                    
                    # Track largest file
                    if member.size > largest_size:
                        largest_size = member.size
                        largest_file = {
                            'name': member.name,
                            'size': self._format_size(member.size)
                        }
                    
                    # Track dates
                    try:
                        file_date = datetime.fromtimestamp(member.mtime)
                        if oldest_date is None or file_date < oldest_date:
                            oldest_date = file_date
                        if newest_date is None or file_date > newest_date:
                            newest_date = file_date
                    except Exception:
                        pass
                        
        except tarfile.TarError as e:
            raise ValueError(f"Invalid or corrupted TAR file: {e}")
        
        # Calculate compression ratio for compressed tars
        compression_ratio = None
        compressed_size = path.stat().st_size
        if total_uncompressed > 0 and mode != 'r':
            compression_ratio = round((1 - compressed_size / total_uncompressed) * 100, 1)
        
        return {
            'file_count': len(file_list),
            'total_uncompressed_size': self._format_size(total_uncompressed),
            'file_list': file_list[:500],
            'file_types': dict(file_types.most_common(20)),
            'compression_ratio': compression_ratio,
            'has_password': False,
            'top_level_items': sorted(list(top_level))[:50],
            'directory_count': len(directories),
            'largest_file': largest_file,
            'oldest_file': oldest_date.isoformat() if oldest_date else None,
            'newest_file': newest_date.isoformat() if newest_date else None,
        }
    
    def _analyze_gzip(self, path: Path) -> dict:
        """Analyze GZIP file (single file compression)."""
        
        original_name = path.stem  
        uncompressed_size = 0
        
        try:
            with open(path, 'rb') as f:
                f.seek(-4, 2)
                uncompressed_size = int.from_bytes(f.read(4), 'little')
            
            with gzip.open(path, 'rb') as gz:
                gz.read(1)
                
        except Exception as e:
            raise ValueError(f"Invalid or corrupted GZIP file: {e}")
        
        compressed_size = path.stat().st_size
        compression_ratio = None
        if uncompressed_size > 0:
            compression_ratio = round((1 - compressed_size / uncompressed_size) * 100, 1)
        
        ext = Path(original_name).suffix.lower() or 'no_extension'
        
        return {
            'file_count': 1,
            'total_uncompressed_size': self._format_size(uncompressed_size),
            'file_list': [original_name],
            'file_types': {ext: 1},
            'compression_ratio': compression_ratio,
            'has_password': False,
            'top_level_items': [original_name],
            'directory_count': 0,
            'largest_file': {'name': original_name, 'size': self._format_size(uncompressed_size)},
            'oldest_file': None,
            'newest_file': None,
        }
    
    def _analyze_bzip2(self, path: Path) -> dict:
        """Analyze BZIP2 file (single file compression)."""
        
        original_name = path.stem 
        uncompressed_size = 0
        
        try:

            with bz2.open(path, 'rb') as bz:
                chunk_size = 1024 * 1024 
                while True:
                    chunk = bz.read(chunk_size)
                    if not chunk:
                        break
                    uncompressed_size += len(chunk)
                    if uncompressed_size > 100 * 1024 * 1024:
                        uncompressed_size = -1  
                        break
                        
        except Exception as e:
            raise ValueError(f"Invalid or corrupted BZIP2 file: {e}")
        
        compressed_size = path.stat().st_size
        compression_ratio = None
        if uncompressed_size > 0:
            compression_ratio = round((1 - compressed_size / uncompressed_size) * 100, 1)
        
        ext = Path(original_name).suffix.lower() or 'no_extension'
        size_str = self._format_size(uncompressed_size) if uncompressed_size > 0 else "Unknown (large file)"
        
        return {
            'file_count': 1,
            'total_uncompressed_size': size_str,
            'file_list': [original_name],
            'file_types': {ext: 1},
            'compression_ratio': compression_ratio,
            'has_password': False,
            'top_level_items': [original_name],
            'directory_count': 0,
            'largest_file': {'name': original_name, 'size': size_str},
            'oldest_file': None,
            'newest_file': None,
        }
    
    def _analyze_xz(self, path: Path) -> dict:
        """Analyze XZ file (single file compression)."""
        
        original_name = path.stem  # Remove .xz
        uncompressed_size = 0
        
        try:
            with lzma.open(path, 'rb') as xz:
                # Read in chunks to estimate size
                chunk_size = 1024 * 1024
                while True:
                    chunk = xz.read(chunk_size)
                    if not chunk:
                        break
                    uncompressed_size += len(chunk)
                    if uncompressed_size > 100 * 1024 * 1024:
                        uncompressed_size = -1
                        break
                        
        except Exception as e:
            raise ValueError(f"Invalid or corrupted XZ file: {e}")
        
        compressed_size = path.stat().st_size
        compression_ratio = None
        if uncompressed_size > 0:
            compression_ratio = round((1 - compressed_size / uncompressed_size) * 100, 1)
        
        ext = Path(original_name).suffix.lower() or 'no_extension'
        size_str = self._format_size(uncompressed_size) if uncompressed_size > 0 else "Unknown (large file)"
        
        return {
            'file_count': 1,
            'total_uncompressed_size': size_str,
            'file_list': [original_name],
            'file_types': {ext: 1},
            'compression_ratio': compression_ratio,
            'has_password': False,
            'top_level_items': [original_name],
            'directory_count': 0,
            'largest_file': {'name': original_name, 'size': size_str},
            'oldest_file': None,
            'newest_file': None,
        }
    
    def _analyze_rar(self, path: Path) -> dict:
        """Analyze RAR archive (requires rarfile package)."""
        
        try:
            import rarfile
        except ImportError:
            return self._analyze_fallback(path, 'rar', 
                "RAR support requires 'rarfile' package: pip install rarfile")
        
        file_list = []
        file_types = Counter()
        total_uncompressed = 0
        top_level = set()
        directories = set()
        largest_file = None
        largest_size = 0
        has_password = False
        
        try:
            with rarfile.RarFile(path, 'r') as rf:
                has_password = rf.needs_password()
                
                for info in rf.infolist():
                    if info.is_dir():
                        directories.add(info.filename)
                        continue
                    
                    file_list.append(info.filename)
                    total_uncompressed += info.file_size
                    
                    ext = Path(info.filename).suffix.lower() or 'no_extension'
                    file_types[ext] += 1
                    
                    top_item = info.filename.split('/')[0].split('\\')[0]
                    top_level.add(top_item)
                    
                    if info.file_size > largest_size:
                        largest_size = info.file_size
                        largest_file = {
                            'name': info.filename,
                            'size': self._format_size(info.file_size)
                        }
                        
        except rarfile.Error as e:
            raise ValueError(f"Invalid or corrupted RAR file: {e}")
        
        compressed_size = path.stat().st_size
        compression_ratio = None
        if total_uncompressed > 0:
            compression_ratio = round((1 - compressed_size / total_uncompressed) * 100, 1)
        
        return {
            'file_count': len(file_list),
            'total_uncompressed_size': self._format_size(total_uncompressed),
            'file_list': file_list[:500],
            'file_types': dict(file_types.most_common(20)),
            'compression_ratio': compression_ratio,
            'has_password': has_password,
            'top_level_items': sorted(list(top_level))[:50],
            'directory_count': len(directories),
            'largest_file': largest_file,
            'oldest_file': None,
            'newest_file': None,
        }
    
    def _analyze_7z(self, path: Path) -> dict:
        """Analyze 7Z archive (requires py7zr package)."""
        
        try:
            import py7zr
        except ImportError:
            return self._analyze_fallback(path, '7z',
                "7Z support requires 'py7zr' package: pip install py7zr")
        
        file_list = []
        file_types = Counter()
        total_uncompressed = 0
        top_level = set()
        directories = set()
        largest_file = None
        largest_size = 0
        has_password = False
        
        try:
            with py7zr.SevenZipFile(path, 'r') as sz:
                has_password = sz.needs_password()
                
                for name, info in sz.archiveinfo().files.items() if hasattr(sz.archiveinfo(), 'files') else []:
                    if info.is_directory:
                        directories.add(name)
                        continue
                    
                    file_list.append(name)
                    total_uncompressed += info.uncompressed if hasattr(info, 'uncompressed') else 0
                
                # Alternative method for py7zr
                if not file_list:
                    for entry in sz.list():
                        if entry.is_directory:
                            directories.add(entry.filename)
                            continue
                        
                        file_list.append(entry.filename)
                        file_size = entry.uncompressed if hasattr(entry, 'uncompressed') else 0
                        total_uncompressed += file_size
                        
                        ext = Path(entry.filename).suffix.lower() or 'no_extension'
                        file_types[ext] += 1
                        
                        top_item = entry.filename.split('/')[0].split('\\')[0]
                        top_level.add(top_item)
                        
                        if file_size > largest_size:
                            largest_size = file_size
                            largest_file = {
                                'name': entry.filename,
                                'size': self._format_size(file_size)
                            }
                            
        except py7zr.Bad7zFile as e:
            raise ValueError(f"Invalid or corrupted 7Z file: {e}")
        except Exception as e:
            raise ValueError(f"Error reading 7Z file: {e}")
        
        compressed_size = path.stat().st_size
        compression_ratio = None
        if total_uncompressed > 0:
            compression_ratio = round((1 - compressed_size / total_uncompressed) * 100, 1)
        
        return {
            'file_count': len(file_list),
            'total_uncompressed_size': self._format_size(total_uncompressed),
            'file_list': file_list[:500],
            'file_types': dict(file_types.most_common(20)),
            'compression_ratio': compression_ratio,
            'has_password': has_password,
            'top_level_items': sorted(list(top_level))[:50],
            'directory_count': len(directories),
            'largest_file': largest_file,
            'oldest_file': None,
            'newest_file': None,
        }
    
    def _analyze_fallback(self, path: Path, archive_type: str, message: str) -> dict:
        """Fallback analysis when specific package is not available."""
        
        return {
            'file_count': 0,
            'total_uncompressed_size': "Unknown",
            'file_list': [],
            'file_types': {},
            'compression_ratio': None,
            'has_password': None,
            'top_level_items': [],
            'directory_count': 0,
            'largest_file': None,
            'oldest_file': None,
            'newest_file': None,
            'note': message,
        }
    
    def _analyze_unknown(self, path: Path) -> dict:
        """Fallback for unknown archive types."""
        
        return {
            'file_count': 0,
            'total_uncompressed_size': "Unknown",
            'file_list': [],
            'file_types': {},
            'compression_ratio': None,
            'has_password': None,
            'top_level_items': [],
            'directory_count': 0,
            'largest_file': None,
            'oldest_file': None,
            'newest_file': None,
            'note': "Unknown archive format. Unable to analyze contents.",
        }
    
    def _format_size(self, size_bytes: int) -> str:
        """Format byte size to human readable string."""
        
        if size_bytes < 0:
            return "Unknown"
        elif size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def _generate_ai_description(
        self,
        file_info: FileInfo,
        analysis: ArchiveAnalysis,
        ai_provider
    ) -> Optional[str]:
        """Generate AI description of the archive."""
        
        from file_organizer.prompts.analysis import build_archive_analysis_prompt, ANALYSIS_SYSTEM_PROMPT
        
        prompt = build_archive_analysis_prompt(
            file_info=file_info,
            file_count=analysis.file_count,
            total_size=analysis.total_uncompressed_size,
            file_types=analysis.file_types,
            top_level_items=analysis.top_level_items,
            compression_ratio=analysis.compression_ratio,
            archive_type=analysis.archive_type,
            largest_file=analysis.largest_file,
        )
        
        try:
            messages = [
                ("system", ANALYSIS_SYSTEM_PROMPT),
                ("user", prompt),
            ]
            response = ai_provider.base_llm.invoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            return f"Could not generate AI description: {str(e)}"