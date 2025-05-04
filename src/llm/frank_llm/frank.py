import os
import logging

from opentelemetry import trace

from src.llm.conversation_partner import ConversationPartner
from ..conversation_reader import ConversationReader

logger = logging.getLogger(__name__)



class Frank(ConversationPartner):

    def __init__(self, exchanges: list[dict]):
        self.exchanges = exchanges
        self.index = 0

    def get_response_for_prompt(self, prompt: str, **kwargs) -> str:
        span = trace.get_current_span()
        span.set_attribute("app.frank.current_exchange", str(self.exchanges[self.index]))
        span.set_attribute("app.frank.index", self.index)
        if self.exchanges[self.index]["prompt"]["text"] != prompt:
            logger.warning(f"Prompt mismatch at index {self.index}", extra={"prompt.expected": self.exchanges[self.index]["prompt"]["text"], "prompt.received": prompt})
        if self.index >= len(self.exchanges):
            raise ValueError("End of conversation reached, no more exchanges available")
        response = self.exchanges[self.index]["response"]
        self.index += 1
        return response
    
    def finish_conversation(self) -> None:
        if self.index < len(self.exchanges):
            logger.warning(f"Conversation ended before all exchanges were used. Unused exchanges: {len(self.exchanges) - self.index}")

    def get_name(self) -> str:
        return f"Frank"
