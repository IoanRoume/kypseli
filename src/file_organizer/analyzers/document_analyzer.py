import re
import warnings
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Tuple
from collections import Counter

import pypdf
from docx import Document
from pptx import Presentation
from striprtf.striprtf import rtf_to_text
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from file_organizer.analyzers.base import BaseAnalyzer
from file_organizer.core.models import (
    FileInfo,
    AnalysisResult,
    DocumentAnalysis,
    ContentType
)

# Suppress common ebooklib warnings
warnings.filterwarnings("ignore", category=UserWarning, module='ebooklib')
warnings.filterwarnings("ignore", category=FutureWarning, module='ebooklib')


class DocumentAnalyzer(BaseAnalyzer):
    """Analyzer for document files (PDF, Word, PowerPoint, RTF, EPUB)."""
    
    supported_content_types = [ContentType.DOCUMENT]
    name = "document"
    
    supported_extensions = [
        ".pdf",
        ".docx",
        ".pptx",
        ".rtf",
        ".epub"
    ]

    def analyze(
        self,
        file_info: FileInfo,
        ai_provider=None
    ) -> AnalysisResult:
        """Analyze a document file."""
        
        try:
            content, page_count = self._extract_content(file_info.path, file_info.extension)
            

            clean_content = " ".join(content.split())
            word_count = len(clean_content.split())
            char_count = len(content)
            

            key_topics = self._extract_key_topics(clean_content)
            
            summary = (clean_content[:300] + "...") if len(clean_content) > 300 else clean_content
            if not summary.strip():
                summary = "No extractable text found."

            doc_analysis = DocumentAnalysis(
                page_count=page_count,
                word_count=word_count,
                char_count=char_count,
                summary=summary,
                key_topics=key_topics,
                language="en" 
            )
            
            ai_description = None
            ai_result = {}
            if ai_provider and word_count > 10:
                ai_result = self._generate_ai_analysis(
                    file_info, doc_analysis, clean_content[:4000], ai_provider
                )
                
                if ai_result:
                    doc_analysis.summary = ai_result.get('summary', doc_analysis.summary)
                    doc_analysis.key_topics = ai_result.get('key_topics', doc_analysis.key_topics)
                    doc_analysis.language = ai_result.get('language', doc_analysis.language)
                    ai_description = ai_result.get('description')

            return AnalysisResult(
                file_info=file_info,
                analysis_type="document",
                analyzed_at=datetime.now(),
                document=doc_analysis, 
                ai_description=ai_result.get('summary', ai_description)
            )
            
        except Exception as e:
            return AnalysisResult(
                file_info=file_info,
                analysis_type="document",
                analyzed_at=datetime.now(),
                error=f"Document analysis failed: {str(e)}"
            )

    def _extract_content(self, path: Path, extension: str) -> Tuple[str, Optional[int]]:
        """Dispatcher for content extraction based on file type."""
        ext = extension.lower()
        
        try:
            if ext == '.pdf':
                return self._extract_pdf(path)
            elif ext == '.docx':
                return self._extract_docx(path)
            elif ext == '.pptx':
                return self._extract_pptx(path)
            elif ext == '.rtf':
                return self._extract_rtf(path)
            elif ext == '.epub':
                return self._extract_epub(path)
            else:
                return "", 0
        except Exception as e:
            return f"Error extracting content: {str(e)}", 0

    def _extract_pdf(self, path: Path) -> Tuple[str, int]:
        """Extract text from PDF using pypdf."""
        reader = pypdf.PdfReader(path)
        text = []
        page_count = len(reader.pages)
        
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text.append(extracted)
                
        return "\n".join(text), page_count

    def _extract_docx(self, path: Path) -> Tuple[str, Optional[int]]:
        """Extract text from DOCX using python-docx."""
        doc = Document(path)
        text = []
        for paragraph in doc.paragraphs:
            text.append(paragraph.text)
            

        return "\n".join(text), None

    def _extract_pptx(self, path: Path) -> Tuple[str, int]:
        """Extract text from PPTX using python-pptx."""
        prs = Presentation(path)
        text = []
        page_count = len(prs.slides)
        
        for slide in prs.slides:
            slide_text = []
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    slide_text.append(shape.text)
            text.append("\n".join(slide_text))
            
        return "\n\n--- Slide ---\n\n".join(text), page_count

    def _extract_rtf(self, path: Path) -> Tuple[str, None]:
        """Extract text from RTF using striprtf."""
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            return rtf_to_text(content), None

    def _extract_epub(self, path: Path) -> Tuple[str, Optional[int]]:
        """Extract text from EPUB using ebooklib and BeautifulSoup."""
        book = epub.read_epub(path)
        text = []
        chapters = 0
        
        # Iterate over documents in the EPUB
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                chapters += 1
                soup = BeautifulSoup(item.get_content(), 'html.parser')
                
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.extract()
                    
                text.append(soup.get_text())
                
        return "\n".join(text), chapters

    def _extract_key_topics(self, text: str) -> List[str]:
        """Extract simple key topics (capitalized phrases) as a fallback."""
        if not text:
            return []
            
        words = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
        
        stop_words = {'The', 'And', 'But', 'For', 'With', 'This', 'That'}
        filtered = [w for w in words if w not in stop_words]
        
        counts = Counter(filtered)
        return [word for word, count in counts.most_common(5)]

    def _generate_ai_analysis(
        self,
        file_info: FileInfo,
        current_data: DocumentAnalysis,
        text_preview: str,
        ai_provider
    ) -> Optional[dict]:
        """Generate AI analysis using the standardized prompt."""
        
        from file_organizer.prompts.analysis import (
            build_document_analysis_prompt, 
            ANALYSIS_SYSTEM_PROMPT
        )
        
        prompt = build_document_analysis_prompt(
            file_info,
            current_data,
            text_preview
        )
        
        try:
            messages = [
                ("system", ANALYSIS_SYSTEM_PROMPT),
                ("user", prompt),
            ]
            
            response = ai_provider.base_llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)
            

            summary_match = re.search(
                r'(?:^|\n)(?:1\.\s*)?(?:\*\*)?SUMMARY(?:\*\*)?[:\.]?\s*(.*?)(?=\n(?:2\.\s*)?(?:\*\*)?KEY POINTS|\n(?:3\.\s*)?(?:\*\*)?AUDIENCE|$)', 
                content, 
                re.DOTALL | re.IGNORECASE
            )
            summary = summary_match.group(1).strip() if summary_match else content[:300]
            
            topics = current_data.key_topics 
            topics_match = re.search(
                r'(?:^|\n)(?:2\.\s*)?(?:\*\*)?KEY POINTS(?:\*\*)?[:\.]?\s*(.*?)(?=\n(?:3\.\s*)?(?:\*\*)?LANGUAGE|\n(?:4\.\s*)?(?:\*\*)?ENTITIES|$)', 
                content, 
                re.DOTALL | re.IGNORECASE
            )
            
            if topics_match:
                raw_topics = topics_match.group(1)
                extracted = [
                    t.strip().strip('-•').strip() 
                    for t in re.split(r'[,;\n]', raw_topics) 
                    if t.strip()
                ]
                if extracted:
                    topics = extracted[:8]

            language_match = re.search(
                r'(?:^|\n)(?:3\.\s*)?(?:\*\*)?LANGUAGE(?:\*\*)?[:\.]?\s*(.*)', 
                content, 
                re.DOTALL | re.IGNORECASE
            )
            language = language_match.group(1).strip() if language_match else current_data.language

            return {
                'description': content,  
                'summary': summary,      
                'key_topics': topics,   
                'language': language
            }
            
        except Exception as e:
            return None