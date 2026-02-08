from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import LLMClassificationResponse
import os
from langchain_openai import ChatOpenAI


class OpenaiProvider(BaseAIProvider):
    name: str = "openai"
    llm = None
    base_llm = None
    
    def initialize_model(self, model: str = "gpt-4o-mini"):
        self.base_llm = ChatOpenAI(
            model = model,
            temperature = 0,
            max_tokens = 1024
        )

        structured_llm = self.base_llm.with_structured_output(LLMClassificationResponse)
        self.llm = structured_llm