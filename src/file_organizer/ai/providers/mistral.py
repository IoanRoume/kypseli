from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import LLMClassificationResponse
from langchain_mistralai import ChatMistralAI


class MistralProvider(BaseAIProvider):
    
    name: str = "mistral"
    llm = None
    base_llm = None
    
    def initialize_model(self, model: str = "mistral-small-latest"):
        self.base_llm = ChatMistralAI(
            model=model,
            temperature=0,
            max_tokens=1024,
        )
        
        self.llm = self.base_llm.with_structured_output(LLMClassificationResponse)