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
import struct
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import Counter

from file_organizer.analyzers.base import BaseAnalyzer
from file_organizer.core.models import (
    FileInfo,
    AnalysisResult,
    BinaryAnalysis,
    ContentType
)


class BinaryAnalyzer(BaseAnalyzer):
    """Analyzer for binary files (.exe, .dll, .so, .db, .sqlite, .bin, .dat, etc.)"""
    
    supported_content_types = [ContentType.BINARY]
    name = "binary"
    
    # Magic bytes for file type detection
    MAGIC_SIGNATURES = {
        # Executables
        b'MZ': 'PE Executable (Windows EXE/DLL)',
        b'\x7fELF': 'ELF Executable (Linux/Unix)',
        b'\xfe\xed\xfa\xce': 'Mach-O 32-bit (macOS)',
        b'\xfe\xed\xfa\xcf': 'Mach-O 64-bit (macOS)',
        b'\xce\xfa\xed\xfe': 'Mach-O 32-bit Reversed (macOS)',
        b'\xcf\xfa\xed\xfe': 'Mach-O 64-bit Reversed (macOS)',
        b'\xca\xfe\xba\xbe': 'Mach-O Universal Binary (macOS)',
        b'\xca\xfe\xba\xbf': 'Mach-O Universal Binary 64 (macOS)',
        
        # Java
        b'\xca\xfe\xba\xbe': 'Java Class File',
        
        # Databases
        b'SQLite format 3': 'SQLite Database',
        
        # Other binary formats
        b'\x00\x00\x01\x00': 'Windows Icon (ICO)',
        b'\x00\x00\x02\x00': 'Windows Cursor (CUR)',
        b'RIFF': 'RIFF Container (AVI/WAV)',
        b'OggS': 'Ogg Container',
        b'fLaC': 'FLAC Audio',
        b'\x1a\x45\xdf\xa3': 'Matroska/WebM',
        b'\x00\x00\x00\x14ftypqt': 'QuickTime Movie',
        b'\x00\x00\x00\x18ftypmp4': 'MP4 Video',
        b'\x00\x00\x00\x1cftypisom': 'MP4 ISO Base Media',
        b'%PDF': 'PDF Document',
        b'PK\x03\x04': 'ZIP Archive',
        b'\x1f\x8b': 'GZIP Compressed',
        b'BZ': 'BZIP2 Compressed',
        b'\xfd7zXZ': 'XZ Compressed',
        b'Rar!': 'RAR Archive',
        b'7z\xbc\xaf': '7-Zip Archive',
    }
    
    # PE (Windows) machine types
    PE_MACHINE_TYPES = {
        0x0: 'Unknown',
        0x14c: 'Intel 386 (x86)',
        0x8664: 'AMD64 (x64)',
        0x1c0: 'ARM',
        0xaa64: 'ARM64',
        0x1c4: 'ARM Thumb-2',
        0x5032: 'RISC-V 32-bit',
        0x5064: 'RISC-V 64-bit',
        0x5128: 'RISC-V 128-bit',
    }
    
    # PE subsystem types
    PE_SUBSYSTEMS = {
        0: 'Unknown',
        1: 'Native',
        2: 'Windows GUI',
        3: 'Windows Console',
        5: 'OS/2 Console',
        7: 'POSIX Console',
        9: 'Windows CE GUI',
        10: 'EFI Application',
        11: 'EFI Boot Service Driver',
        12: 'EFI Runtime Driver',
        13: 'EFI ROM',
        14: 'Xbox',
        16: 'Windows Boot Application',
    }
    
    # ELF machine types
    ELF_MACHINE_TYPES = {
        0x00: 'No specific',
        0x02: 'SPARC',
        0x03: 'Intel 386 (x86)',
        0x08: 'MIPS',
        0x14: 'PowerPC',
        0x15: 'PowerPC64',
        0x16: 'S390',
        0x28: 'ARM',
        0x2A: 'SuperH',
        0x32: 'IA-64',
        0x3E: 'AMD64 (x64)',
        0xB7: 'ARM64',
        0xF3: 'RISC-V',
    }
    
    # ELF types
    ELF_TYPES = {
        0: 'None',
        1: 'Relocatable',
        2: 'Executable',
        3: 'Shared Object (Library)',
        4: 'Core Dump',
    }
    
    def analyze(
        self,
        file_info: FileInfo,
        ai_provider=None
    ) -> AnalysisResult:
        """Analyze a binary file."""
        
        try:
            # Read file header
            with open(file_info.path, 'rb') as f:
                header = f.read(512)
            
            # Detect binary type and analyze accordingly
            binary_info = self._analyze_binary(file_info.path, header, file_info.extension)
            
            # Create binary analysis
            binary_analysis = BinaryAnalysis(
                binary_type=binary_info.get('binary_type', 'Unknown'),
                format_details=binary_info.get('format_details'),
                architecture=binary_info.get('architecture'),
                bit_depth=binary_info.get('bit_depth'),
                is_executable=binary_info.get('is_executable', False),
                is_library=binary_info.get('is_library', False),
                is_database=binary_info.get('is_database', False),
                endianness=binary_info.get('endianness'),
                entry_point=binary_info.get('entry_point'),
                sections=binary_info.get('sections', []),
                imports=binary_info.get('imports', []),
                exports=binary_info.get('exports', []),
                strings_preview=binary_info.get('strings_preview', []),
                # Database-specific
                db_tables=binary_info.get('db_tables', []),
                db_row_counts=binary_info.get('db_row_counts', {}),
                db_size_info=binary_info.get('db_size_info'),
                # Metadata
                file_version=binary_info.get('file_version'),
                product_name=binary_info.get('product_name'),
                company_name=binary_info.get('company_name'),
                created_date=binary_info.get('created_date'),
                entropy=binary_info.get('entropy'),
                is_packed=binary_info.get('is_packed'),
                magic_bytes=binary_info.get('magic_bytes'),
            )
            
            # Generate AI description if provider available
            ai_description = None
            if ai_provider:
                ai_description = self._generate_ai_description(
                    file_info, binary_analysis, ai_provider
                )
            
            return AnalysisResult(
                file_info=file_info,
                analysis_type="binary",
                analyzed_at=datetime.now(),
                binary=binary_analysis,
                ai_description=ai_description
            )
            
        except Exception as e:
            return AnalysisResult(
                file_info=file_info,
                analysis_type="binary",
                analyzed_at=datetime.now(),
                error=str(e)
            )
    
    def _analyze_binary(self, path: Path, header: bytes, extension: str) -> dict:
        """Analyze binary file based on type."""
        
        binary_type = self._detect_binary_type(header)
        magic_hex = header[:16].hex() if header else ''
        
        result = {
            'binary_type': binary_type,
            'magic_bytes': magic_hex,
        }
        
        if header[:2] == b'MZ':
            result.update(self._analyze_pe(path, header))
        elif header[:4] == b'\x7fELF':
            result.update(self._analyze_elf(path, header))
        elif header[:4] in (b'\xfe\xed\xfa\xce', b'\xfe\xed\xfa\xcf', 
                           b'\xce\xfa\xed\xfe', b'\xcf\xfa\xed\xfe',
                           b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf'):
            result.update(self._analyze_macho(path, header))
        elif header[:16] == b'SQLite format 3\x00' or extension.lower() in ('.db', '.sqlite', '.sqlite3'):
            result.update(self._analyze_sqlite(path))
        elif extension.lower() == '.class' or header[:4] == b'\xca\xfe\xba\xbe':
            result.update(self._analyze_java_class(path, header))
        else:
            result.update(self._analyze_generic_binary(path, header))
        
        
        result['entropy'] = self._calculate_entropy(path)
        result['is_packed'] = result.get('entropy', 0) > 7.0
        
        result['strings_preview'] = self._extract_strings(path)
        
        return result
    
    def _detect_binary_type(self, header: bytes) -> str:
        """Detect binary type from magic bytes."""
        
        if header[:16] == b'SQLite format 3\x00':
            return 'SQLite Database'
        
        for magic, name in self.MAGIC_SIGNATURES.items():
            if header.startswith(magic):
                return name
        
        return 'Unknown Binary'
    
    def _analyze_pe(self, path: Path, header: bytes) -> dict:
        """Analyze Windows PE (Portable Executable) file."""
        
        result = {
            'format_details': 'Windows Portable Executable',
            'is_executable': True,
        }
        
        try:
            with open(path, 'rb') as f:
                dos_header = f.read(64)
                if len(dos_header) < 64:
                    return result
                
                pe_offset = struct.unpack('<I', dos_header[60:64])[0]
                
                f.seek(pe_offset)
                pe_sig = f.read(4)
                if pe_sig != b'PE\x00\x00':
                    return result
                
                coff_header = f.read(20)
                if len(coff_header) < 20:
                    return result
                
                machine = struct.unpack('<H', coff_header[0:2])[0]
                num_sections = struct.unpack('<H', coff_header[2:4])[0]
                timestamp = struct.unpack('<I', coff_header[4:8])[0]
                characteristics = struct.unpack('<H', coff_header[18:20])[0]
                
                result['architecture'] = self.PE_MACHINE_TYPES.get(machine, f'Unknown (0x{machine:x})')
                
                is_dll = bool(characteristics & 0x2000)
                result['is_library'] = is_dll
                result['is_executable'] = not is_dll
                
                optional_header_size = struct.unpack('<H', coff_header[16:18])[0]
                optional_header = f.read(optional_header_size)
                
                if len(optional_header) >= 2:
                    magic = struct.unpack('<H', optional_header[0:2])[0]
                    if magic == 0x10b:
                        result['bit_depth'] = 32
                    elif magic == 0x20b:
                        result['bit_depth'] = 64
                
                if len(optional_header) >= 68:
                    if result.get('bit_depth') == 64 and len(optional_header) >= 88:
                        subsystem = struct.unpack('<H', optional_header[68:70])[0]
                    else:
                        subsystem = struct.unpack('<H', optional_header[68:70])[0]
                    result['format_details'] = self.PE_SUBSYSTEMS.get(subsystem, 'Unknown Subsystem')
                
                if len(optional_header) >= 20:
                    entry_point = struct.unpack('<I', optional_header[16:20])[0]
                    result['entry_point'] = f'0x{entry_point:08x}'
                
                if timestamp > 0:
                    try:
                        result['created_date'] = datetime.fromtimestamp(timestamp).isoformat()
                    except (OSError, ValueError):
                        pass
                
                sections = []
                for _ in range(min(num_sections, 20)):  
                    section_header = f.read(40)
                    if len(section_header) >= 8:
                        name = section_header[:8].rstrip(b'\x00').decode('ascii', errors='ignore')
                        if name:
                            sections.append(name)
                
                result['sections'] = sections
                
        except Exception as e:
            result['format_details'] = f'PE file (parse error: {str(e)[:50]})'
        
        return result
    
    def _analyze_elf(self, path: Path, header: bytes) -> dict:
        """Analyze Linux ELF (Executable and Linkable Format) file."""
        
        result = {
            'format_details': 'Unix/Linux ELF',
        }
        
        try:
            with open(path, 'rb') as f:
                elf_header = f.read(64)
                
                if len(elf_header) < 52:
                    return result
                
                ei_class = elf_header[4]
                if ei_class == 1:
                    result['bit_depth'] = 32
                elif ei_class == 2:
                    result['bit_depth'] = 64
                
                ei_data = elf_header[5]
                if ei_data == 1:
                    result['endianness'] = 'Little Endian'
                    endian = '<'
                elif ei_data == 2:
                    result['endianness'] = 'Big Endian'
                    endian = '>'
                else:
                    endian = '<'
                
                e_type = struct.unpack(f'{endian}H', elf_header[16:18])[0]
                elf_type_name = self.ELF_TYPES.get(e_type, 'Unknown')
                result['format_details'] = f'ELF {elf_type_name}'
                
                result['is_executable'] = e_type == 2
                result['is_library'] = e_type == 3
                
                e_machine = struct.unpack(f'{endian}H', elf_header[18:20])[0]
                result['architecture'] = self.ELF_MACHINE_TYPES.get(e_machine, f'Unknown (0x{e_machine:x})')
                
                if result.get('bit_depth') == 64:
                    entry = struct.unpack(f'{endian}Q', elf_header[24:32])[0]
                else:
                    entry = struct.unpack(f'{endian}I', elf_header[24:28])[0]
                
                if entry > 0:
                    result['entry_point'] = f'0x{entry:x}'
                
                if result.get('bit_depth') == 64:
                    e_shoff = struct.unpack(f'{endian}Q', elf_header[40:48])[0]
                    e_shentsize = struct.unpack(f'{endian}H', elf_header[58:60])[0]
                    e_shnum = struct.unpack(f'{endian}H', elf_header[60:62])[0]
                    e_shstrndx = struct.unpack(f'{endian}H', elf_header[62:64])[0]
                else:
                    e_shoff = struct.unpack(f'{endian}I', elf_header[32:36])[0]
                    e_shentsize = struct.unpack(f'{endian}H', elf_header[46:48])[0]
                    e_shnum = struct.unpack(f'{endian}H', elf_header[48:50])[0]
                    e_shstrndx = struct.unpack(f'{endian}H', elf_header[50:52])[0]
                
                sections = []
                if e_shoff > 0 and e_shnum > 0 and e_shnum < 100:
                    try:
                        f.seek(e_shoff + e_shstrndx * e_shentsize)
                        strtab_header = f.read(e_shentsize)
                        
                        if result.get('bit_depth') == 64:
                            strtab_offset = struct.unpack(f'{endian}Q', strtab_header[24:32])[0]
                            strtab_size = struct.unpack(f'{endian}Q', strtab_header[32:40])[0]
                        else:
                            strtab_offset = struct.unpack(f'{endian}I', strtab_header[16:20])[0]
                            strtab_size = struct.unpack(f'{endian}I', strtab_header[20:24])[0]
                        
                        f.seek(strtab_offset)
                        strtab = f.read(min(strtab_size, 4096))
                        
                        for i in range(min(e_shnum, 30)):
                            f.seek(e_shoff + i * e_shentsize)
                            sh_header = f.read(e_shentsize)
                            
                            name_offset = struct.unpack(f'{endian}I', sh_header[0:4])[0]
                            if name_offset < len(strtab):
                                name_end = strtab.find(b'\x00', name_offset)
                                if name_end > name_offset:
                                    name = strtab[name_offset:name_end].decode('ascii', errors='ignore')
                                    if name and not name.startswith('.'):
                                        continue
                                    if name:
                                        sections.append(name)
                    except Exception:
                        pass
                
                result['sections'] = sections[:20]
                
        except Exception as e:
            result['format_details'] = f'ELF file (parse error: {str(e)[:50]})'
        
        return result
    
    def _analyze_macho(self, path: Path, header: bytes) -> dict:
        """Analyze macOS Mach-O file."""
        
        result = {
            'format_details': 'macOS Mach-O',
        }
        
        try:
            magic = struct.unpack('>I', header[:4])[0]
            
            # Determine endianness and bit depth
            if magic in (0xfeedface, 0xfeedfacf):  # Big endian
                result['endianness'] = 'Big Endian'
                endian = '>'
                result['bit_depth'] = 64 if magic == 0xfeedfacf else 32
            elif magic in (0xcefaedfe, 0xcffaedfe):  # Little endian
                result['endianness'] = 'Little Endian'
                endian = '<'
                result['bit_depth'] = 64 if magic == 0xcffaedfe else 32
            elif magic in (0xcafebabe, 0xcafebabf):  # Universal binary
                result['format_details'] = 'macOS Universal Binary'
                result['architecture'] = 'Multiple (Fat Binary)'
                return result
            else:
                return result
            
            with open(path, 'rb') as f:
                f.read(4)  
                
                cputype = struct.unpack(f'{endian}I', f.read(4))[0]
                cpusubtype = struct.unpack(f'{endian}I', f.read(4))[0]
                
                cpu_names = {
                    1: 'VAX',
                    6: 'MC680x0',
                    7: 'Intel x86',
                    0x01000007: 'Intel x86_64',
                    12: 'ARM',
                    0x0100000c: 'ARM64',
                    18: 'PowerPC',
                    0x01000012: 'PowerPC64',
                }
                result['architecture'] = cpu_names.get(cputype, f'Unknown (0x{cputype:x})')
                
                filetype = struct.unpack(f'{endian}I', f.read(4))[0]
                type_names = {
                    1: 'Object File',
                    2: 'Executable',
                    3: 'Fixed VM Library',
                    4: 'Core Dump',
                    5: 'Preloaded Executable',
                    6: 'Dynamic Library',
                    7: 'Dynamic Linker',
                    8: 'Bundle',
                    9: 'Dynamic Library Stub',
                    10: 'Debug Symbols',
                    11: 'Kext Bundle',
                }
                result['format_details'] = f'Mach-O {type_names.get(filetype, "Unknown")}'
                result['is_executable'] = filetype == 2
                result['is_library'] = filetype in (6, 7)
                
        except Exception as e:
            result['format_details'] = f'Mach-O file (parse error: {str(e)[:50]})'
        
        return result
    
    def _analyze_sqlite(self, path: Path) -> dict:
        """Analyze SQLite database file."""
        
        result = {
            'binary_type': 'SQLite Database',
            'format_details': 'SQLite 3 Database',
            'is_database': True,
            'is_executable': False,
            'is_library': False,
        }
        
        try:
            conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            result['db_tables'] = tables[:50]
            
            row_counts = {}
            for table in tables[:20]:
                try:
                    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
                    count = cursor.fetchone()[0]
                    row_counts[table] = count
                except Exception:
                    row_counts[table] = -1
            
            result['db_row_counts'] = row_counts
            
            cursor.execute("PRAGMA page_count")
            page_count = cursor.fetchone()[0]
            cursor.execute("PRAGMA page_size")
            page_size = cursor.fetchone()[0]
            
            db_size = page_count * page_size
            result['db_size_info'] = {
                'pages': page_count,
                'page_size': page_size,
                'total_size': self._format_size(db_size),
            }
            
            cursor.execute("SELECT sqlite_version()")
            version = cursor.fetchone()[0]
            result['file_version'] = f'SQLite {version}'
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")
            indexes = [row[0] for row in cursor.fetchall()]
            if indexes:
                result['sections'] = indexes[:20]
            
            conn.close()
            
        except sqlite3.Error as e:
            result['format_details'] = f'SQLite Database (error: {str(e)[:50]})'
        except Exception as e:
            result['format_details'] = f'SQLite Database (error: {str(e)[:50]})'
        
        return result
    
    def _analyze_java_class(self, path: Path, header: bytes) -> dict:
        """Analyze Java class file."""
        
        result = {
            'binary_type': 'Java Class File',
            'format_details': 'Java Bytecode',
            'is_executable': True,
            'architecture': 'JVM (Platform Independent)',
        }
        
        try:
            with open(path, 'rb') as f:
                magic = f.read(4)
                if magic != b'\xca\xfe\xba\xbe':
                    return result
                
                minor = struct.unpack('>H', f.read(2))[0]
                major = struct.unpack('>H', f.read(2))[0]
                
                java_versions = {
                    45: 'Java 1.1',
                    46: 'Java 1.2',
                    47: 'Java 1.3',
                    48: 'Java 1.4',
                    49: 'Java 5',
                    50: 'Java 6',
                    51: 'Java 7',
                    52: 'Java 8',
                    53: 'Java 9',
                    54: 'Java 10',
                    55: 'Java 11',
                    56: 'Java 12',
                    57: 'Java 13',
                    58: 'Java 14',
                    59: 'Java 15',
                    60: 'Java 16',
                    61: 'Java 17',
                    62: 'Java 18',
                    63: 'Java 19',
                    64: 'Java 20',
                    65: 'Java 21',
                    66: 'Java 22',
                    67: 'Java 23',
                }
                
                java_ver = java_versions.get(major, f'Java (class version {major}.{minor})')
                result['file_version'] = java_ver
                result['format_details'] = f'Java Class File ({java_ver})'
                
        except Exception as e:
            result['format_details'] = f'Java Class File (parse error: {str(e)[:50]})'
        
        return result
    
    def _analyze_generic_binary(self, path: Path, header: bytes) -> dict:
        """Analyze generic/unknown binary file."""
        
        result = {
            'binary_type': 'Binary Data',
            'format_details': 'Unknown Binary Format',
            'is_executable': False,
            'is_library': False,
            'is_database': False,
        }
        
        file_size = path.stat().st_size
        
        byte_counts = Counter(header)
        null_ratio = byte_counts.get(0, 0) / len(header) if header else 0
        
        if null_ratio > 0.5:
            result['format_details'] = 'Binary Data (high null content)'
        elif all(b < 128 for b in header[:100] if b != 0):
            result['format_details'] = 'Binary Data (mostly ASCII)'
        
        return result
    
    def _calculate_entropy(self, path: Path, sample_size: int = 65536) -> float:
        """Calculate Shannon entropy of file (0-8 scale)."""
        
        import math
        
        try:
            with open(path, 'rb') as f:
                data = f.read(sample_size)
            
            if not data:
                return 0.0
            
            byte_counts = Counter(data)
            total = len(data)
            
            entropy = 0.0
            for count in byte_counts.values():
                if count > 0:
                    p = count / total
                    entropy -= p * math.log2(p)
            
            return round(entropy, 2)
            
        except Exception:
            return 0.0
    
    def _extract_strings(self, path: Path, min_length: int = 6, max_strings: int = 50) -> list[str]:
        """Extract readable strings from binary file."""
        
        strings = []
        
        try:
            with open(path, 'rb') as f:
                # Read up to 1MB
                data = f.read(1024 * 1024)
            
            current_string = []
            for byte in data:
                if 32 <= byte < 127:
                    current_string.append(chr(byte))
                else:
                    if len(current_string) >= min_length:
                        s = ''.join(current_string)
                        if not s.startswith('\\x') and not all(c == s[0] for c in s):
                            strings.append(s[:100])
                    current_string = []
                
                if len(strings) >= max_strings:
                    break
            
            if len(current_string) >= min_length and len(strings) < max_strings:
                s = ''.join(current_string)
                if not s.startswith('\\x') and not all(c == s[0] for c in s):
                    strings.append(s[:100])
                    
        except Exception:
            pass
        
        return strings
    
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
        analysis: BinaryAnalysis,
        ai_provider
    ) -> Optional[str]:
        """Generate AI description of the binary file."""
        
        from file_organizer.prompts.analysis import build_binary_analysis_prompt, ANALYSIS_SYSTEM_PROMPT
        
        prompt = build_binary_analysis_prompt(
            file_info=file_info,
            binary_type=analysis.binary_type,
            format_details=analysis.format_details,
            architecture=analysis.architecture,
            bit_depth=analysis.bit_depth,
            is_executable=analysis.is_executable,
            is_library=analysis.is_library,
            is_database=analysis.is_database,
            sections=analysis.sections,
            strings_preview=analysis.strings_preview,
            db_tables=analysis.db_tables,
            db_row_counts=analysis.db_row_counts,
            entropy=analysis.entropy,
            is_packed=analysis.is_packed,
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