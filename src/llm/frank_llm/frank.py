import os
import logging
from typing import Union

from opentelemetry import trace

from src.llm.conversation_partner import ConversationPartner
from src.conversation.types import Exchange, TextPrompt, ToolUseResults, FinalResponse, ToolUseRequests

logger = logging.getLogger(__name__)


class Frank(ConversationPartner):

    def __init__(self, exchanges: list[Exchange]):
        self.exchanges = exchanges
        self.index = 0

    def get_response_for_prompt(self, prompt: Union[TextPrompt, ToolUseResults], **_) -> Union[FinalResponse, ToolUseRequests]:
        if self.index >= len(self.exchanges):
            raise ValueError("End of conversation reached, no more exchanges available")

        span = trace.get_current_span()
        span.set_attribute("app.frank.current_exchange", str(self.exchanges[self.index]))
        span.set_attribute("app.frank.index", self.index)

        current_exchange = self.exchanges[self.index]
        
        # Validate prompt matches expected type and content
        if isinstance(prompt, TextPrompt) and isinstance(current_exchange.prompt, TextPrompt):
            if current_exchange.prompt.text != prompt.text:
                logger.warning(f"Text prompt mismatch at index {self.index}",
                              extra={"prompt.expected": current_exchange.prompt.text,
                                    "prompt.received": prompt.text})
        elif isinstance(prompt, ToolUseResults) and isinstance(current_exchange.prompt, ToolUseResults):
            # Could add validation for tool results if needed
            pass
        else:
            logger.warning(f"Prompt type mismatch at index {self.index}: expected {type(current_exchange.prompt)}, got {type(prompt)}")

        # Return the response from the current exchange
        response = current_exchange.response
        self.index += 1
        return response

    def finish_conversation(self) -> dict:
        if self.index < len(self.exchanges):
            logger.warning(f"Conversation ended before all exchanges were used. Unused exchanges: {len(self.exchanges) - self.index}")
        return {}

    def get_name(self) -> str:
        return "Frank"
