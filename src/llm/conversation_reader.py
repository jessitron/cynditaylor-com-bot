import json
import logging

from src.conversation.types import Conversation

logger = logging.getLogger(__name__)


class ConversationReader:
    def __init__(self, conversation_file: str):
        self.conversation_file = conversation_file

    def load_conversation(self) -> Conversation:
        try:
            with open(self.conversation_file, "r") as f:
                conversation_dict = json.load(f)

            # Validate the conversation format
            if "version" not in conversation_dict or "exchanges" not in conversation_dict:
                raise ValueError(f"Invalid conversation format in file: {self.conversation_file}")

            # Convert the dictionary to a Conversation object
            return Conversation.from_dict(conversation_dict)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading conversation file: {e}")
            raise
