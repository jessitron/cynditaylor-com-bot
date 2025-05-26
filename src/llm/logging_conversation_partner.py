import logging
import os

from src.llm.conversation_partner import ConversationPartner
from src.conversation.logger import ConversationLogger
from src.conversation.types import Prompt, Response

logger = logging.getLogger(__name__)

class LoggingConversationPartner(ConversationPartner):
    """
    A decorator for ConversationPartner that logs conversations.
    This implements the Decorator Pattern to add logging functionality
    to any ConversationPartner implementation.
    """

    def __init__(self, conversation_partner: ConversationPartner, conversation_logger=None, output_dir: str = "conversation_history"):
        self.conversation_partner = conversation_partner
        self.conversation_logger = conversation_logger or ConversationLogger(output_dir=output_dir)
        logger.info(f"Initialized LoggingConversationPartner with logger: {self.conversation_logger.filename()}") # TODO: give the conversation logger a describe method instead, so it can say whatever is relevant

    def get_response_for_prompt(self, prompt: Prompt) -> Response:
        # Get the response from the wrapped conversation partner
        response = self.conversation_partner.get_response_for_prompt(prompt)

        # Log the exchange with the prompt and response objects directly
        self.conversation_logger.log_exchange(prompt, response)

        return response

    def get_name(self) -> str:
        return f"Logging-{self.conversation_partner.get_name()}"

    def record_metadata(self, key: str, value) -> None:
        """Record metadata for this conversation."""
        self.conversation_logger.add_metadata({key: value})

    def finish_conversation(self) -> dict:
        # Save the final conversation state

        # Get metadata from downstream conversation partner
        metadata = self.conversation_partner.finish_conversation()
        self.conversation_logger.add_metadata(metadata)

        output_file = self.conversation_logger.save()

        # print the full path of the file we saved to
        logger.info(f"Conversation saved to: {output_file}")

        return metadata
