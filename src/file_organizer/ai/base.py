from abc import ABC, abstractmethod
from file_organizer.core.models import ExtractedContent, FoldersToClassify, ClassificationResult
from file_organizer.prompts.classification import build_classification_prompt, SYSTEM_PROMPT
import json


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

        

    def is_available(self) -> bool:
       return True