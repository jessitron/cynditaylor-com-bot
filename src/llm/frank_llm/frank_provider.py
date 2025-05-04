import os
import logging

from opentelemetry import trace

from src.llm.frank_llm.frank import Frank
from src.llm.logging_conversation_partner import LoggingConversationPartner
from src.llm.conversation_partner import ConversationPartner

from ..provider import LLMProvider

class FrankProvider(LLMProvider):

    def start_conversation(self) -> ConversationPartner:
        # Create a Frank instance
        frank = Frank()

        # Wrap it with a LoggingConversationPartner
        return LoggingConversationPartner(frank)