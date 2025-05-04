import os
import logging

from opentelemetry import trace

from .provider import LLMProvider
from src.conversation.logger import ConversationLogger
from .conversation_reader import ConversationReader

tracer = trace.get_tracer("cynditaylor-com-bot")
logger = logging.getLogger(__name__)

# Hard-coded conversation file path
CONVERSATION_FILE = os.path.join(os.path.dirname(__file__), "conversations", "test_conversation.json")


class FrankProvider(LLMProvider):

    def __init__(self, model: str = "default"):
        self.model = model
        self.conversation_logger = ConversationLogger(output_dir="conversation_history")

        try:
            self.conversation_reader = ConversationReader(CONVERSATION_FILE)
            logger.info(f"Frank initialized using conversation file: {CONVERSATION_FILE}")
        except Exception as e:
            logger.error(f"Error initializing conversation reader: {e}")
            raise ValueError(f"Failed to initialize Frank: {e}")

    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.conversation_reader.get_response_for_prompt(prompt)
            if response:
                logger.info("Found matching prompt in conversation history")
                # Log the exchange
                metadata = {
                    "model": self.model,
                    "temperature": kwargs.get("temperature", 0.7),
                    "max_tokens": kwargs.get("max_tokens", 1000)
                }
                self.conversation_logger.log_exchange(prompt, response, metadata)
                return response
            else:
                logger.error("No matching prompt found in conversation history")
                raise ValueError(f"No matching prompt found in conversation history. Prompt: {prompt[:100]}...")
        except Exception as e:
            logger.error(f"Error in Frank: {e}")
            raise

    def get_name(self) -> str:
        return f"Frank ({self.model})"
