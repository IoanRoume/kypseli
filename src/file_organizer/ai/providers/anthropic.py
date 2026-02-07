from file_organizer.ai.base import BaseAIProvider
from file_organizer.core.models import LLMClassificationResponse
from langchain_anthropic import ChatAnthropic


class AnthropicProvider(BaseAIProvider):
    name: str = "anthropic"
    llm = None
    
    def initialize_model(self, model: str = "claude-sonnet-4-20250514"):
        llm = ChatAnthropic(
            model=model,
            temperature=0,
            max_tokens=1024
        )
        
        structured_llm = llm.with_structured_output(LLMClassificationResponse)
        self.llm = structured_llm