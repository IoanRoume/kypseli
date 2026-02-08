from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import LLMClassificationResponse
from langchain_google_genai import ChatGoogleGenerativeAI


class GeminiProvider(BaseAIProvider):
    name: str = "gemini"
    llm = None
    base_llm = None
    
    def initialize_model(self, model: str = "gemini-2.0-flash"):
        self.base_llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=0,
            max_tokens=1024
        )
        
        structured_llm = self.base_llm.with_structured_output(LLMClassificationResponse)
        self.llm = structured_llm