from file_organizer.core.models import FileInfo, TabularAnalysis, DocumentAnalysis

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
Provide:

A concise summary of the document's content (1-2 sentences)

The main themes or key points discussed

The intended audience or purpose of the document

Any notable entities (people, organizations, dates) mentioned

Keep response under 150 words."""
    return prompt