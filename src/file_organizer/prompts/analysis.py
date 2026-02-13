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
from file_organizer.core.models import FileInfo, TabularAnalysis, DocumentAnalysis
from typing import Optional

ANALYSIS_SYSTEM_PROMPT = """You are a data analyst assistant. Your task is to provide clear, concise descriptions and insights about files and datasets.

Keep your responses:
- Concise but informative
- Focused on key insights
- Written in plain language
- Actionable when possible"""


def build_tabular_analysis_prompt(file_info: FileInfo, analysis: TabularAnalysis) -> str:
    """Build prompt for tabular data analysis."""
    
    high_missing = [
        f"{col} ({pct:.1f}%)"
        for col, pct in analysis.missing_percentage.items()
        if pct > 5
    ]
    
    prompt = f"""Analyze this dataset and provide a brief description:

FILE: {file_info.name}

STRUCTURE:
- Rows: {analysis.row_count:,}
- Columns: {analysis.column_count}
- Memory: {analysis.memory_usage}

COLUMNS:
{', '.join(analysis.columns[:20])}{'...' if len(analysis.columns) > 20 else ''}

DATA TYPES:
{chr(10).join(f'- {col}: {dtype}' for col, dtype in list(analysis.dtypes.items())[:15])}

MISSING VALUES:
{chr(10).join(f'- {col}' for col in high_missing[:10]) if high_missing else 'No significant missing values'}

Provide:
1. A one-sentence description of what this dataset likely contains
2. Key observations about data quality
3. Potential use cases or analyses that could be done

Keep response under 150 words."""
    
    return prompt


def build_code_analysis_prompt(
    file_info,
    code_preview: str,
    imports: list[str],
    functions: list[str],
    classes: list[str],
    language: str,
    line_count: int
) -> str:
    """Build prompt for code analysis."""
    
    imports_str = '\n'.join(f"  • {imp}" for imp in imports[:15]) if imports else "  None found"
    functions_str = '\n'.join(f"  • {func}()" for func in functions[:15]) if functions else "  None found"
    classes_str = '\n'.join(f"  • {cls}" for cls in classes[:10]) if classes else "  None found"
    
    prompt = f"""Analyze this code file and provide a brief description:

FILE: {file_info.name}
LANGUAGE: {language}
LINES: {line_count}

IMPORTS/DEPENDENCIES:
{imports_str}
{f'  ... and {len(imports) - 15} more' if len(imports) > 15 else ''}

FUNCTIONS/METHODS:
{functions_str}
{f'  ... and {len(functions) - 15} more' if len(functions) > 15 else ''}

CLASSES/TYPES:
{classes_str}
{f'  ... and {len(classes) - 10} more' if len(classes) > 10 else ''}

CODE PREVIEW:
```{language.lower()}
{code_preview[:2000]}
```

Provide:
1. A brief description of what this code does (1-2 sentences)
2. Main purpose/functionality
3. Key technologies or frameworks used
4. Any notable patterns or architectural observations

Keep response under 150 words."""
    
    return prompt


def build_document_analysis_prompt(
    file_info: FileInfo, 
    analysis: DocumentAnalysis,
    text_preview: str
) -> str:
    """Build prompt for document analysis."""
    
    # Format extracted topics if available from heuristic step
    topics_list = analysis.key_topics or []
    topics_str = ', '.join(topics_list[:10]) if topics_list else "None detected"
    
    # Handle page count formatting (might be None for text files)
    pages_str = f"{analysis.page_count}" if analysis.page_count else "N/A"
    
    prompt = f"""Analyze this document and provide a brief description:

FILE: {file_info.name}
TYPE: {file_info.extension}

STATISTICS:
- Pages: {pages_str}
- Words: {analysis.word_count:,}
- Characters: {analysis.char_count:,}
- Language: {analysis.language or 'Unknown'}

DETECTED TOPICS (Heuristic):
{topics_str}

TEXT PREVIEW:
```text
{text_preview[:2500]}
...
Please provide your analysis using exactly this format:

SUMMARY: A concise summary of the content (1-2 sentences).
KEY POINTS: A comma-separated list of the main themes or findings.
LANGUAGE: The Language that the document is written.

Keep the total response under 150 words."""
    return prompt



def build_archive_analysis_prompt(
    file_info,
    file_count: int,
    total_size: str,
    file_types: dict,
    top_level_items: list,
    compression_ratio: Optional[float],
    archive_type: str,
    largest_file: Optional[dict],
) -> str:
    """Build prompt for archive analysis."""
    
    types_str = ", ".join([f"{ext}: {count}" for ext, count in list(file_types.items())[:10]])
    
    top_items_str = ", ".join(top_level_items[:15])
    if len(top_level_items) > 15:
        top_items_str += f"... and {len(top_level_items) - 15} more"
    
    largest_str = "N/A"
    if largest_file:
        largest_str = f"{largest_file.get('name', 'Unknown')} ({largest_file.get('size', 'Unknown')})"
    
    compression_str = f"{compression_ratio}% space saved" if compression_ratio else "Unknown"
    
    prompt = f"""Analyze this archive file and provide a brief description.

ARCHIVE INFORMATION:
- File name: {file_info.name}
- Archive type: {archive_type}
- File size (compressed): {file_info.size} bytes
- Total files: {file_count}
- Total uncompressed size: {total_size}
- Compression ratio: {compression_str}
- Largest file: {largest_str}

FILE TYPES IN ARCHIVE:
{types_str}

TOP-LEVEL CONTENTS:
{top_items_str}

Provide a brief analysis (under 150 words) covering:
1. What this archive likely contains (project, backup, dataset, etc.)
2. The primary content type (code, documents, media, mixed, etc.)
3. Any notable observations about the structure or contents
4. Potential use case or origin of this archive"""

    return prompt



def build_binary_analysis_prompt(
    file_info,
    binary_type: str,
    format_details: Optional[str],
    architecture: Optional[str],
    bit_depth: Optional[int],
    is_executable: bool,
    is_library: bool,
    is_database: bool,
    sections: list,
    strings_preview: list,
    db_tables: list,
    db_row_counts: dict,
    entropy: Optional[float],
    is_packed: Optional[bool],
) -> str:
    """Build prompt for binary file analysis."""
    
    # Format sections
    sections_str = ", ".join(sections[:15]) if sections else "None detected"
    
    # Format strings
    strings_str = "\n".join([f"  - {s[:80]}" for s in strings_preview[:20]]) if strings_preview else "None extracted"
    
    # Format database info
    db_info = ""
    if is_database and db_tables:
        db_info = f"\nDATABASE TABLES ({len(db_tables)}):\n"
        for table in db_tables[:15]:
            count = db_row_counts.get(table, 'unknown')
            db_info += f"  - {table}: {count:,} rows\n" if isinstance(count, int) and count >= 0 else f"  - {table}\n"
    
    # Determine file category
    if is_database:
        category = "Database"
    elif is_executable:
        category = "Executable"
    elif is_library:
        category = "Library/Shared Object"
    else:
        category = "Binary Data"
    
    # Packed indicator
    packed_str = ""
    if entropy is not None:
        packed_str = f"\nEntropy: {entropy}/8.0"
        if is_packed:
            packed_str += " (possibly packed/encrypted)"
    
    prompt = f"""Analyze this binary file and provide a brief description.

BINARY FILE INFORMATION:
- File name: {file_info.name}
- File size: {file_info.size:,} bytes
- Category: {category}
- Type: {binary_type}
- Format: {format_details or 'Unknown'}
- Architecture: {architecture or 'Unknown'}
- Bit depth: {bit_depth or 'Unknown'}-bit
{packed_str}

SECTIONS/SEGMENTS:
{sections_str}
{db_info}
EXTRACTED STRINGS (sample):
{strings_str}

Provide a brief analysis (under 150 words) covering:
1. What this binary file likely is (application, system file, database, etc.)
2. Its probable purpose or origin
3. Any notable characteristics based on the strings or structure
4. Platform compatibility and requirements"""

    return prompt