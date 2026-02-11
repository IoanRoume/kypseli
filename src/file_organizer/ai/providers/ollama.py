
from langchain_ollama import ChatOllama
import requests
from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import (
    LLMClassificationResponse,
    ExtractedContent,
    FoldersToClassify,
    ClassificationResult
)
from file_organizer.prompts.classification import build_classification_prompt, SYSTEM_PROMPT
import json
import re
from typing import Optional

class OllamaProvider(BaseAIProvider):
    name: str = "ollama"
    llm = None
    base_llm = None


    def initialize_model(self, model: str = "llama3.1:8b", base_url: str = "http://localhost:11434"):

        if not self._check_ollama_running(base_url):
            raise ConnectionError(
                f"Ollama is not running at {base_url}. "
                "Please start Ollama with 'ollama serve' or install it from https://ollama.com"
            )
        
        if not self._check_model_available(model, base_url):
            raise ValueError(
                f"Model '{model}' is not available. "
                f"Pull it first with 'ollama pull {model}'"
            )
        
        self.base_llm = ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0,
            num_predict=1024,
            verbose=False,
        )
        
        self.llm = self.base_llm
        self._model_name = model

        success, error = self.validate_connection()
        if not success:
            raise ConnectionError(f"Ollama ({model}): {error}")
    
    def _check_ollama_running(self, base_url: str) -> bool:
        
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def _check_model_available(self, model: str, base_url: str) -> bool:
        
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                available_models = [m["name"] for m in data.get("models", [])]
                
                for available in available_models:
                    if model in available or available in model:
                        return True
                    # Handle model:tag format
                    if model.split(":")[0] == available.split(":")[0]:
                        return True
                        
                return False
        except requests.exceptions.RequestException:
            return False
        
        return True
    

    def classify(
        self,
        extracted_content: ExtractedContent,
        categories: FoldersToClassify
    ) -> ClassificationResult:
        """Classify a file using Ollama (with manual JSON parsing)."""
        
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
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
            
            content = content.strip()
            result = json.loads(content)
            
        except json.JSONDecodeError:
            result = self._extract_json_from_text(response.content)
            
            if result is None:
                result = {
                    "folder_name": categories.default_folder.name,
                    "confidence": 0.0,
                    "reasoning": "Failed to parse LLM response"
                }
        
        classified_path = categories.default_folder
        folder_name = result.get("folder_name", "")
        
        for folder_info in categories.folders:
            if folder_name.lower() == folder_info.folder_path.name.lower():
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
    
    def _extract_json_from_text(self, text: str) -> Optional[dict]:
        """Try to extract JSON object from text."""
        # Look for JSON-like pattern
        json_pattern = r'\{[^{}]*"folder_name"[^{}]*\}'
        matches = re.findall(json_pattern, text, re.DOTALL)
        
        for match in matches:
            try:
                return json.loads(match)
            except json.JSONDecodeError:
                continue
        
        return None
    
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """Generate free-form text response."""
        
        messages = [
            ("system", system_prompt),
            ("user", user_prompt),
        ]
        
        response = self.base_llm.invoke(messages)
        return response.content if hasattr(response, 'content') else str(response)
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        return self._check_ollama_running("http://localhost:11434")
    
    @staticmethod
    def list_available_models(base_url: str = "http://localhost:11434") -> list[str]:
        """List all models available in Ollama."""
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except requests.exceptions.RequestException:
            pass
        
        return []