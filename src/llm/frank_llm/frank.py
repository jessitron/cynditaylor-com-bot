import os
import logging

from opentelemetry import trace

from src.llm.conversation_partner import ConversationPartner
from ..conversation_reader import ConversationReader

tracer = trace.get_tracer("frank-the-fake-llm")
logger = logging.getLogger(__name__)

# Hard-coded conversation file path
CONVERSATION_FILE = os.path.join(os.path.dirname(__file__), "conversations", "test_conversation.json")

class Frank(ConversationPartner):

    @tracer.start_as_current_span("Initialize Frank")
    def __init__(self):
        span = trace.get_current_span()
        try:
            span.set_attribute("app.conversation-reader.filename", CONVERSATION_FILE)
            self.conversation_reader = ConversationReader(CONVERSATION_FILE)
        except Exception as e:
            logger.error(f"Error initializing conversation reader: {e}")
            raise ValueError(f"Failed to initialize Frank: {e}")

    def get_response_for_prompt(self, prompt: str, **kwargs) -> str:
        try:
            response = self.conversation_reader.get_response_for_prompt(prompt)
            if response:
                logger.info("Found matching prompt in conversation history")
                return response
            else:
                logger.error("No matching prompt found in conversation history")
                raise ValueError(f"No matching prompt found in conversation history. Prompt: {prompt[:100]}...")
        except Exception as e:
            logger.error(f"Error in Frank: {e}")
            raise

    def get_name(self) -> str:
        return f"Frank"
