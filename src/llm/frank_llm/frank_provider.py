import os
import logging

from opentelemetry import trace

from src.llm.frank_llm.frank import Frank

from ..provider import LLMProvider
from src.conversation.logger import ConversationLogger
from ..conversation_reader import ConversationReader

class FrankProvider(LLMProvider):

    def start_conversation(self) -> Frank:
        return Frank()