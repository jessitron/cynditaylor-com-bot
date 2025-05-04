import logging
from typing import Dict, Any

from src.llm.conversation_partner import ConversationPartner
from src.conversation.logger import ConversationLogger

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

    def get_response_for_prompt(self, prompt: str, **kwargs) -> str:
        # Get the response from the wrapped conversation partner
        response = self.conversation_partner.get_response_for_prompt(prompt, **kwargs)
        
        # Log the exchange
        metadata = {
            "model": self.get_name(),
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000)
        }
        self.conversation_logger.log_exchange(prompt, response, metadata)
        
        return response

    def get_name(self) -> str:
        return f"Logging-{self.conversation_partner.get_name()}"
    
    def finish_conversation(self) -> None:
        # Save the final conversation state
        self.conversation_logger.save()
        
        # Call finish_conversation on the wrapped partner if it implements it
        if hasattr(self.conversation_partner, 'finish_conversation'):
            self.conversation_partner.finish_conversation()
