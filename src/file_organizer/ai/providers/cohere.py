from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import LLMClassificationResponse
from langchain_cohere import ChatCohere


class CohereProvider(BaseAIProvider):
    
    name: str = "cohere"
    llm = None
    base_llm = None
    
    def initialize_model(self, model: str = "command-r"):

        self.base_llm = ChatCohere(
            model=model,
            temperature=0,
            max_tokens=1024,
        )
        
        self.llm = self.base_llm.with_structured_output(LLMClassificationResponse)

        success, error = self.validate_connection()
        if not success:
            raise ConnectionError(f"Cohere ({model}): {error}")