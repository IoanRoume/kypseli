from ai.base import BaseAIProvider
from core.models import LLMClassificationResponse
import os
from langchain_openai import ChatOpenAI


class OpenaiProvider(BaseAIProvider):
    name: str = "openai"
    llm = None
    
    def initialize_model(self, model: str = "gpt-4o-mini"):
        llm = ChatOpenAI(
            model = model,
            temperature = 0,
            max_tokens = 1024
        )

        structured_llm = llm.with_structured_output(LLMClassificationResponse)
        self.llm = structured_llm