from abc import ABC, abstractmethod
from file_organizer.core.models import ExtractedContent, FoldersToClassify, ClassificationResult
from file_organizer.prompts.classification import build_classification_prompt, SYSTEM_PROMPT
import json
from typing import Optional

class BaseAIProvider(ABC):
    name: str
    llm = None
    base_llm = None

    @abstractmethod
    def initialize_model(self):
        pass

    def classify(self, extracted_content: ExtractedContent, categories: FoldersToClassify) -> ClassificationResult:
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
        
        # Find the matching folder path
        classified_path = categories.default_folder
        for folder_info in categories.folders:
            if response.folder_name == folder_info.folder_path.name:
                classified_path = folder_info.folder_path
                break

        classification_result = ClassificationResult(
            extracted_content=extracted_content,
            category=response.folder_name,
            confidence=response.confidence,
            reasoning=response.reasoning,
            generated_summary=None,
            classified_path=classified_path
        )

        return classification_result
    

    def validate_connection(self) -> tuple[bool, Optional[str]]:
        try:
            messages = [
                ("system", "You are a helpful assistant."),
                ("user", "Say 'OK' and nothing else."),
            ]
            
            response = self.base_llm.invoke(messages)
            
            # Check if we got a response
            if response and (hasattr(response, 'content') or response):
                return True, None
            else:
                return False, "Empty response from API"
                
        except Exception as e:
            error_msg = str(e)
            
            # Parse common error types
            if "404" in error_msg or "not exist" in error_msg.lower() or "model_not_found" in error_msg.lower():
                return False, f"Model not found or you don't have access to it"
            elif "401" in error_msg or "unauthorized" in error_msg.lower() or "invalid_api_key" in error_msg.lower():
                return False, "Invalid API key or authentication failed"
            elif "403" in error_msg or "forbidden" in error_msg.lower():
                return False, "Access forbidden - check your API key permissions"
            elif "429" in error_msg or "rate_limit" in error_msg.lower():
                return False, "Rate limit exceeded - please wait and try again"
            elif "500" in error_msg or "502" in error_msg or "503" in error_msg:
                return False, "Server error - the provider may be experiencing issues"
            elif "connection" in error_msg.lower() or "connect" in error_msg.lower():
                return False, "Connection failed - check your internet connection"
            elif "timeout" in error_msg.lower():
                return False, "Request timed out - the server may be slow or unreachable"
            else:
                return False, error_msg[:200]

        

    def is_available(self) -> bool:
       return True