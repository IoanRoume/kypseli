from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import (
    ExtractedContent,
    FoldersToClassify,
    ClassificationResult
)
from file_organizer.prompts.classification import build_classification_prompt, SYSTEM_PROMPT
from langchain_openai import ChatOpenAI
import json


class OpenAICompatibleProvider(BaseAIProvider):
    """
    Generic provider for any OpenAI-compatible API.
    Works with:
    - LM Studio (http://localhost:1234/v1)
    - vLLM (http://localhost:8000/v1)
    - LocalAI (http://localhost:8080/v1)
    - Ollama (http://localhost:11434/v1)
    - Any other OpenAI-compatible server
    """
    name: str = "openai-compatible"
    llm = None
    base_llm = None
    
    def initialize_model(
        self,
        model: str = "local-model",
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "not-needed"
    ):

        self.base_llm = ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=0,
            max_tokens=1024,
        )
        
        self.llm = self.base_llm
        self._base_url = base_url
    
    def classify(
        self,
        extracted_content: ExtractedContent,
        categories: FoldersToClassify
    ) -> ClassificationResult:
        """Classify with manual JSON parsing."""
        
        system_prompt = SYSTEM_PROMPT
        user_prompt = build_classification_prompt(
            extracted_content=extracted_content,
            folders_to_classify=categories
        )
        
        messages = [
            ("system", system_prompt),
            ("user", user_prompt),
        ]
        
        response = self.base_llm.invoke(messages)
        
        try:
            content = response.content.strip()
            
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
            
        except json.JSONDecodeError:
            result = {
                "folder_name": categories.default_folder.name,
                "confidence": 0.0,
                "reasoning": "Failed to parse response"
            }
        
        classified_path = categories.default_folder
        for folder_info in categories.folders:
            if result.get("folder_name", "").lower() == folder_info.folder_path.name.lower():
                classified_path = folder_info.folder_path
                break
        
        return ClassificationResult(
            extracted_content=extracted_content,
            category=result.get("folder_name"),
            confidence=float(result.get("confidence", 0.0)),
            reasoning=result.get("reasoning"),
            generated_summary=None,
            classified_path=classified_path
        )
    
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Generate free-form text response."""
        
        messages = [
            ("system", system_prompt),
            ("user", user_prompt),
        ]
        
        response = self.base_llm.invoke(messages)
        return response.content if hasattr(response, 'content') else str(response)