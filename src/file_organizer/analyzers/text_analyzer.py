import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from collections import Counter

from file_organizer.analyzers.base import BaseAnalyzer
from file_organizer.core.models import (
    FileInfo,
    AnalysisResult,
    CodeAnalysis,
    ContentType
)


class TextAnalyzer(BaseAnalyzer):
    """Analyzer for text and code files (.py, .js, .txt, .md, etc.)"""
    
    supported_content_types = [ContentType.TEXT]
    name = "text"
    
    # Language detection based on extension
    LANGUAGE_MAP = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.ts': 'TypeScript',
        '.jsx': 'React JSX',
        '.tsx': 'React TSX',
        '.java': 'Java',
        '.c': 'C',
        '.cpp': 'C++',
        '.cc': 'C++',
        '.h': 'C/C++ Header',
        '.hpp': 'C++ Header',
        '.cs': 'C#',
        '.go': 'Go',
        '.rs': 'Rust',
        '.rb': 'Ruby',
        '.php': 'PHP',
        '.swift': 'Swift',
        '.kt': 'Kotlin',
        '.scala': 'Scala',
        '.r': 'R',
        '.R': 'R',
        '.sql': 'SQL',
        '.sh': 'Shell/Bash',
        '.bash': 'Bash',
        '.zsh': 'Zsh',
        '.ps1': 'PowerShell',
        '.lua': 'Lua',
        '.pl': 'Perl',
        '.pm': 'Perl Module',
        '.html': 'HTML',
        '.htm': 'HTML',
        '.css': 'CSS',
        '.scss': 'SCSS',
        '.sass': 'Sass',
        '.less': 'Less',
        '.xml': 'XML',
        '.yaml': 'YAML',
        '.yml': 'YAML',
        '.json': 'JSON',
        '.toml': 'TOML',
        '.ini': 'INI',
        '.cfg': 'Config',
        '.conf': 'Config',
        '.md': 'Markdown',
        '.markdown': 'Markdown',
        '.rst': 'reStructuredText',
        '.txt': 'Plain Text',
        '.log': 'Log File',
        '.csv': 'CSV',
        '.tsv': 'TSV',
        '.vue': 'Vue',
        '.svelte': 'Svelte',
        '.dart': 'Dart',
        '.ex': 'Elixir',
        '.exs': 'Elixir Script',
        '.erl': 'Erlang',
        '.hs': 'Haskell',
        '.ml': 'OCaml',
        '.fs': 'F#',
        '.clj': 'Clojure',
        '.lisp': 'Lisp',
        '.el': 'Emacs Lisp',
        '.vim': 'Vim Script',
        '.dockerfile': 'Dockerfile',
        '.tf': 'Terraform',
        '.proto': 'Protocol Buffers',
        '.graphql': 'GraphQL',
        '.gql': 'GraphQL',
    }
    
    # Import patterns for different languages
    IMPORT_PATTERNS = {
        'Python': [
            r'^import\s+(\S+)',
            r'^from\s+(\S+)\s+import',
        ],
        'JavaScript': [
            r'^import\s+.*\s+from\s+[\'"](.+)[\'"]',
            r'^import\s+[\'"](.+)[\'"]',
            r'require\s*\(\s*[\'"](.+)[\'"]\s*\)',
        ],
        'TypeScript': [
            r'^import\s+.*\s+from\s+[\'"](.+)[\'"]',
            r'^import\s+[\'"](.+)[\'"]',
        ],
        'Java': [
            r'^import\s+(.+);',
        ],
        'Go': [
            r'^import\s+[\'"](.+)[\'"]',
            r'^\s+[\'"](.+)[\'"]',  # Inside import block
        ],
        'Rust': [
            r'^use\s+(.+);',
        ],
        'C': [
            r'^#include\s*[<"](.+)[>"]',
        ],
        'C++': [
            r'^#include\s*[<"](.+)[>"]',
        ],
        'Ruby': [
            r'^require\s+[\'"](.+)[\'"]',
            r'^require_relative\s+[\'"](.+)[\'"]',
        ],
        'PHP': [
            r'^use\s+(.+);',
            r'^require\s+[\'"](.+)[\'"]',
            r'^include\s+[\'"](.+)[\'"]',
        ],
    }
    
    # Function/method patterns for different languages
    FUNCTION_PATTERNS = {
        'Python': [
            r'^def\s+(\w+)\s*\(',
            r'^\s+def\s+(\w+)\s*\(',  # Methods inside classes
        ],
        'JavaScript': [
            r'^function\s+(\w+)\s*\(',
            r'^const\s+(\w+)\s*=\s*(?:async\s*)?\(',
            r'^const\s+(\w+)\s*=\s*(?:async\s*)?\w+\s*=>\s*',
            r'^(\w+)\s*:\s*(?:async\s*)?function\s*\(',
        ],
        'TypeScript': [
            r'^function\s+(\w+)\s*[<(]',
            r'^const\s+(\w+)\s*=\s*(?:async\s*)?\(',
            r'^(?:public|private|protected)?\s*(?:async\s*)?(\w+)\s*\(',
        ],
        'Java': [
            r'(?:public|private|protected)\s+\w+\s+(\w+)\s*\(',
        ],
        'Go': [
            r'^func\s+(\w+)\s*\(',
            r'^func\s+\(\w+\s+\*?\w+\)\s+(\w+)\s*\(',  # Methods
        ],
        'Rust': [
            r'^fn\s+(\w+)\s*[<(]',
            r'^\s+fn\s+(\w+)\s*[<(]',
        ],
        'C': [
            r'^\w+\s+(\w+)\s*\([^)]*\)\s*{',
        ],
        'C++': [
            r'^\w+\s+(\w+)\s*\([^)]*\)\s*{',
            r'^\w+::\w+\s+(\w+)\s*\([^)]*\)',
        ],
        'Ruby': [
            r'^def\s+(\w+)',
        ],
        'PHP': [
            r'function\s+(\w+)\s*\(',
        ],
    }
    
    # Class patterns for different languages
    CLASS_PATTERNS = {
        'Python': [
            r'^class\s+(\w+)',
        ],
        'JavaScript': [
            r'^class\s+(\w+)',
        ],
        'TypeScript': [
            r'^(?:export\s+)?(?:abstract\s+)?class\s+(\w+)',
            r'^(?:export\s+)?interface\s+(\w+)',
        ],
        'Java': [
            r'(?:public|private)?\s*class\s+(\w+)',
            r'(?:public|private)?\s*interface\s+(\w+)',
        ],
        'Go': [
            r'^type\s+(\w+)\s+struct',
            r'^type\s+(\w+)\s+interface',
        ],
        'Rust': [
            r'^struct\s+(\w+)',
            r'^enum\s+(\w+)',
            r'^trait\s+(\w+)',
            r'^impl\s+(\w+)',
        ],
        'C++': [
            r'^class\s+(\w+)',
            r'^struct\s+(\w+)',
        ],
        'Ruby': [
            r'^class\s+(\w+)',
            r'^module\s+(\w+)',
        ],
        'PHP': [
            r'^class\s+(\w+)',
            r'^interface\s+(\w+)',
            r'^trait\s+(\w+)',
        ],
    }
    
    def analyze(
        self,
        file_info: FileInfo,
        ai_provider=None
    ) -> AnalysisResult:
        """Analyze a text or code file."""
        
        try:
            # Read file content
            content = self._read_file(file_info.path)
            
            # Detect language
            language = self._detect_language(file_info.extension, content)
            
            # Basic stats
            lines = content.split('\n')
            line_count = len(lines)
            non_empty_lines = len([l for l in lines if l.strip()])
            
            # Extract code elements
            imports = self._extract_imports(content, language)
            functions = self._extract_functions(content, language)
            classes = self._extract_classes(content, language)
            
            # Estimate complexity
            complexity = self._estimate_complexity(
                line_count, len(functions), len(classes), content
            )
            
            # Create code analysis
            code_analysis = CodeAnalysis(
                language=language,
                line_count=line_count,
                import_statements=imports,
                functions=functions,
                classes=classes,
                complexity_estimate=complexity,
                summary=None
            )
            
            # Generate AI description if provider available
            ai_description = None
            if ai_provider:
                ai_description = self._generate_ai_description(
                    file_info, code_analysis, content[:3000], ai_provider
                )
            
            return AnalysisResult(
                file_info=file_info,
                analysis_type="code",
                analyzed_at=datetime.now(),
                code=code_analysis,
                ai_description=ai_description
            )
            
        except Exception as e:
            return AnalysisResult(
                file_info=file_info,
                analysis_type="code",
                analyzed_at=datetime.now(),
                error=str(e)
            )
    
    def _read_file(self, path: Path, max_size: int = 1_000_000) -> str:
        """Read text file with size limit."""
        
        file_size = path.stat().st_size
        
        # For very large files, read only the beginning
        if file_size > max_size:
            with open(path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read(max_size)
        
        # Try different encodings
        encodings = ['utf-8', 'latin-1', 'cp1252', 'ascii']
        
        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    return f.read()
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        # Last resort: read with replacement
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    
    def _detect_language(self, extension: str, content: str) -> str:
        """Detect programming language from extension and content."""
        
        ext = extension.lower()
        
        # Check extension map first
        if ext in self.LANGUAGE_MAP:
            return self.LANGUAGE_MAP[ext]
        
        # Try to detect from shebang
        first_line = content.split('\n')[0] if content else ''
        
        if first_line.startswith('#!'):
            if 'python' in first_line.lower():
                return 'Python'
            elif 'node' in first_line.lower() or 'js' in first_line.lower():
                return 'JavaScript'
            elif 'bash' in first_line.lower() or 'sh' in first_line.lower():
                return 'Shell/Bash'
            elif 'ruby' in first_line.lower():
                return 'Ruby'
            elif 'perl' in first_line.lower():
                return 'Perl'
            elif 'php' in first_line.lower():
                return 'PHP'
        
        # Check for Dockerfile
        if 'FROM ' in content[:500] and ('RUN ' in content or 'CMD ' in content):
            return 'Dockerfile'
        
        return 'Plain Text'
    
    def _extract_imports(self, content: str, language: str) -> list[str]:
        """Extract import statements based on language."""
        
        imports = []
        patterns = self.IMPORT_PATTERNS.get(language, [])
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            imports.extend(matches)
        
        # Deduplicate and limit
        imports = list(dict.fromkeys(imports))[:50]
        
        return imports
    
    def _extract_functions(self, content: str, language: str) -> list[str]:
        """Extract function/method names based on language."""
        
        functions = []
        patterns = self.FUNCTION_PATTERNS.get(language, [])
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            functions.extend(matches)
        
        # Filter out common false positives
        exclude = {'if', 'for', 'while', 'switch', 'catch', 'with', 'else'}
        functions = [f for f in functions if f not in exclude]
        
        # Deduplicate and limit
        functions = list(dict.fromkeys(functions))[:100]
        
        return functions
    
    def _extract_classes(self, content: str, language: str) -> list[str]:
        """Extract class/struct/interface names based on language."""
        
        classes = []
        patterns = self.CLASS_PATTERNS.get(language, [])
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.MULTILINE)
            classes.extend(matches)
        
        # Deduplicate and limit
        classes = list(dict.fromkeys(classes))[:50]
        
        return classes
    
    def _estimate_complexity(
        self,
        line_count: int,
        function_count: int,
        class_count: int,
        content: str
    ) -> str:
        """Estimate code complexity."""
        
        # Count complexity indicators
        complexity_score = 0
        
        # Line count factor
        if line_count > 1000:
            complexity_score += 3
        elif line_count > 500:
            complexity_score += 2
        elif line_count > 100:
            complexity_score += 1
        
        # Function/class count factor
        if function_count > 20:
            complexity_score += 2
        elif function_count > 10:
            complexity_score += 1
        
        if class_count > 5:
            complexity_score += 2
        elif class_count > 2:
            complexity_score += 1
        
        # Nesting depth (rough estimate)
        max_indent = 0
        for line in content.split('\n'):
            stripped = line.lstrip()
            if stripped:
                indent = len(line) - len(stripped)
                spaces = indent if line[0] == ' ' else indent * 4  # tabs to spaces
                max_indent = max(max_indent, spaces)
        
        if max_indent > 20:  # Deep nesting
            complexity_score += 2
        elif max_indent > 12:
            complexity_score += 1
        
        # Control flow complexity
        control_keywords = ['if', 'else', 'elif', 'for', 'while', 'try', 'catch', 'except', 'switch', 'case']
        control_count = sum(len(re.findall(rf'\b{kw}\b', content)) for kw in control_keywords)
        
        if control_count > 50:
            complexity_score += 2
        elif control_count > 20:
            complexity_score += 1
        
        # Determine complexity level
        if complexity_score >= 7:
            return "complex"
        elif complexity_score >= 4:
            return "moderate"
        else:
            return "simple"
    
    def _generate_ai_description(
        self,
        file_info: FileInfo,
        analysis: CodeAnalysis,
        code_preview: str,
        ai_provider
    ) -> Optional[str]:
        """Generate AI description of the code."""
        
        from file_organizer.prompts.analysis import build_code_analysis_prompt, ANALYSIS_SYSTEM_PROMPT
        
        prompt = build_code_analysis_prompt(
            file_info,
            code_preview,
            analysis.import_statements,
            analysis.functions,
            analysis.classes,
            analysis.language,
            analysis.line_count
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