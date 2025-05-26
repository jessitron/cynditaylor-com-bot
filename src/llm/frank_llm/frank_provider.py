import os
import logging

from opentelemetry import trace

from src.llm.opentelemetry_conversation_partner import OpenTelemetryConversationPartnerDecorator
from src.llm.conversation_reader import ConversationReader
from src.llm.frank_llm.frank import Frank
from src.llm.logging_conversation_partner import LoggingConversationPartner
from src.llm.conversation_partner import ConversationPartner

from ..provider import LLMProvider


tracer = trace.get_tracer("frank-the-fake-llm")
logger = logging.getLogger(__name__)

# Hard-coded conversation file path
CONVERSATION_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "test_conversations", "test_conversation.json")

class FrankProvider(LLMProvider):

    @tracer.start_as_current_span("Initialize Frank") # TODO: move this part into the OpenTelemetryLLMProviderDecorator
    def start_conversation(self, system_prompt: str = "") -> ConversationPartner:
        # Read the conversation
        span = trace.get_current_span()
        span.set_attribute("app.conversation-reader.filename", CONVERSATION_FILE) # TODO: move this into the LoggingConversationPartner
        try:
            conversation = ConversationReader(CONVERSATION_FILE).load_conversation()
        except (FileNotFoundError, ValueError) as e:
            logger.error(f"Error loading conversation file: {e}")
            raise

        return LoggingConversationPartner(OpenTelemetryConversationPartnerDecorator(Frank(conversation.exchanges)), system_prompt=system_prompt)