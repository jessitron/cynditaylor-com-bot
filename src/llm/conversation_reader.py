import json
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class ConversationReader:
    def __init__(self, conversation_file: str):
        self.conversation_file = conversation_file
        self.conversation = self._load_conversation()
        self.current_exchange_index = 0

    def _load_conversation(self) -> Dict[str, Any]:
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

    def get_response_for_prompt(self, prompt: str) -> Optional[str]:
        # Check if we've reached the end of the conversation
        if self.current_exchange_index >= len(self.conversation["exchanges"]):
            logger.error("End of conversation reached, no more exchanges available")
            raise ValueError("End of conversation reached, no more exchanges available")

        # Get the current exchange
        current_exchange = self.conversation["exchanges"][self.current_exchange_index]

        # Check if the prompt matches exactly
        if current_exchange["prompt"]["text"] == prompt:
            # Move to the next exchange for the next call
            self.current_exchange_index += 1
            logger.info(f"Matched prompt at exchange index {self.current_exchange_index - 1}")
            return current_exchange["response"]["text"]
        else:
            # Log the mismatch details for debugging
            logger.error(f"Prompt mismatch at exchange index {self.current_exchange_index}")
            logger.error(f"Expected: {current_exchange['prompt']['text'][:100]}...")
            logger.error(f"Received: {prompt[:100]}...")

            # Raise an error with details about the mismatch
            raise ValueError(
                f"Prompt does not match the expected prompt at position {self.current_exchange_index}. "
                f"Expected: {current_exchange['prompt']['text'][:50]}... "
                f"Received: {prompt[:50]}..."
            )

    def get_tool_calls_for_prompt(self) -> List[Dict[str, Any]]:
        # Since we're using sequential access, we need to check the previous exchange
        # (the one we just returned a response for)
        if self.current_exchange_index == 0:
            return []

        previous_exchange = self.conversation["exchanges"][self.current_exchange_index - 1]

        if "tool_calls" in previous_exchange["response"]:
            return previous_exchange["response"]["tool_calls"]

        return []
