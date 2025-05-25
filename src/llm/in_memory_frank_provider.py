import logging

from opentelemetry import trace

from src.llm.opentelemetry_conversation_partner import OpenTelemetryConversationPartnerDecorator
from src.llm.in_memory_conversation_reader import InMemoryConversationReader
from src.llm.frank_llm.frank import Frank
from src.llm.logging_conversation_partner import LoggingConversationPartner
from src.llm.conversation_partner import ConversationPartner
from src.conversation.types import Conversation

from .provider import LLMProvider


tracer = trace.get_tracer("in-memory-frank-provider")
logger = logging.getLogger(__name__)


class InMemoryFrankProvider(LLMProvider):
    def __init__(self, conversation: Conversation, conversation_logger=None):
        self.conversation = conversation
        self.conversation_logger = conversation_logger

    @tracer.start_as_current_span("Initialize In-Memory Frank")
    def start_conversation(self) -> ConversationPartner:
        span = trace.get_current_span()
        span.set_attribute("app.conversation-reader.type", "in-memory")
        span.set_attribute("app.conversation.id", self.conversation.conversation_id)
        
        # Use in-memory conversation reader instead of file-based one
        conversation_reader = InMemoryConversationReader(self.conversation)
        conversation = conversation_reader.load_conversation()

        conversation_partner = LoggingConversationPartner(
            OpenTelemetryConversationPartnerDecorator(Frank(conversation.exchanges)),
            conversation_logger=self.conversation_logger
        )
        
        # Add a test trace URL to the conversation logger after setting up the conversation partner
        if self.conversation_logger and hasattr(self.conversation_logger, 'add_metadata'):
            self.conversation_logger.add_metadata({
                "honeycomb_trace_url": "https://ui.honeycomb.io/test-team/environments/test-env/trace?trace_id=test123&span_id=span456&trace_start_ts=1234567890&trace_end_ts=1234567900"
            })

        return conversation_partner