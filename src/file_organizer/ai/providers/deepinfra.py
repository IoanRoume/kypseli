from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import (
    LLMClassificationResponse,
    ExtractedContent,
    FoldersToClassify,
    ClassificationResult
)
from file_organizer.prompts.classification import build_classification_prompt, SYSTEM_PROMPT
import json
from langchain_community.chat_models import ChatDeepInfra


class DeepInfraProvider(BaseAIProvider):
    name: str = "deepinfra"
    llm = None
    
    def initialize_model(self, model: str = "google/gemma-3-27b-it"):
        self.llm = ChatDeepInfra(
            model=model,
            temperature=0,
            max_tokens=1024
        )
    
    def classify(
        self,
        extracted_content: ExtractedContent,
        categories: FoldersToClassify
    ) -> ClassificationResult:
        """Override classify to handle JSON parsing manually."""
        
        system_prompt = SYSTEM_PROMPT
        user_prompt = build_classification_prompt(
            extracted_content=extracted_content,
            folders_to_classify=categories
        )
        
        messages = [
            ("system", system_prompt),
            ("user", user_prompt),
        ]
        
        response = self.llm.invoke(messages)
        
        try:
            content = response.content.strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            result = json.loads(content)
            
        except json.JSONDecodeError as e:
            result = {
                "folder_name": categories.default_folder.name,
                "confidence": 0.0,
                "reasoning": f"Failed to parse LLM response: {str(e)}"
            }
        
        classified_path = categories.default_folder
        for folder_info in categories.folders:
            if result.get("folder_name") == folder_info.folder_path.name:
                classified_path = folder_info.folder_path
                break
        
        return ClassificationResult(
            extracted_content=extracted_content,
            category=result.get("folder_name"),
            confidence=result.get("confidence", 0.0),
            reasoning=result.get("reasoning"),
            generated_summary=None,
            classified_path=classified_path
        )