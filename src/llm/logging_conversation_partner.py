import logging

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

    def __init__(self, conversation_partner: ConversationPartner, output_dir: str = "conversation_history"):
        self.conversation_partner = conversation_partner
        self.conversation_logger = ConversationLogger(output_dir=output_dir)
        logger.info(f"Initialized LoggingConversationPartner with logger: {self.conversation_logger.filename()}")

    def get_response_for_prompt(self, prompt: Prompt, **kwargs) -> Response:
        # Get the response from the wrapped conversation partner
        response = self.conversation_partner.get_response_for_prompt(prompt, **kwargs)

        # Update metadata in the prompt if needed
        if kwargs.get("temperature") or kwargs.get("max_tokens") or kwargs.get("model"):
            # Only update if not already set
            if not prompt.metadata.model:
                prompt.metadata.model = self.get_name()
            if kwargs.get("temperature"):
                prompt.metadata.temperature = kwargs.get("temperature")
            if kwargs.get("max_tokens"):
                prompt.metadata.max_tokens = kwargs.get("max_tokens")

        # Log the exchange with the prompt and response objects directly
        self.conversation_logger.log_exchange(prompt, response)

        return response

    def get_name(self) -> str:
        return f"Logging-{self.conversation_partner.get_name()}"

    def finish_conversation(self) -> None:
        # Save the final conversation state
        self.conversation_logger.save()

        self.conversation_partner.finish_conversation()
