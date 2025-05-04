import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ConversationReader:
    def __init__(self, conversation_file: str):
        self.conversation_file = conversation_file

    def load_conversation(self) -> Dict[str, Any]:
        try:
            with open(self.conversation_file, "r") as f:
                conversation = json.load(f)

            # Validate the conversation format
            if "version" not in conversation or "exchanges" not in conversation:
                raise ValueError(f"Invalid conversation format in file: {self.conversation_file}")

            return conversation
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading conversation file: {e}")
            raise
