from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import LLMClassificationResponse
from langchain_groq import ChatGroq


class GroqProvider(BaseAIProvider):
    
    name: str = "groq"
    llm = None
    base_llm = None
    
    def initialize_model(self, model: str = "llama-3.1-8b-instant"):
        self.base_llm = ChatGroq(
            model=model,
            temperature=0,
            max_tokens=1024,
        )
        
        self.llm = self.base_llm.with_structured_output(LLMClassificationResponse)