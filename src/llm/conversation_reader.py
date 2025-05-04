import json
import logging
from typing import Dict, Any, Optional, List

from src.conversation.hash_util import hash_prompt

logger = logging.getLogger(__name__)


class ConversationReader:
    """
    Reader for conversation history files.
    Used by Frank to replay responses from recorded conversations.
    """

    def __init__(self, conversation_file: str):
        """
        Initialize the conversation reader.

        Args:
            conversation_file: Path to the conversation history file
        """
        self.conversation_file = conversation_file
        self.conversation = self._load_conversation()
        self.current_exchange_index = 0

    def _load_conversation(self) -> Dict[str, Any]:
        """
        Load the conversation history from the file.

        Returns:
            The conversation history as a dictionary
        """
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

    def find_matching_exchange(self, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Find an exchange in the conversation history that matches the given prompt.

        Args:
            prompt: The prompt to match

        Returns:
            The matching exchange, or None if no match is found
        """
        # Calculate the hash of the prompt
        prompt_hash = hash_prompt(prompt)

        # Extract the instruction from the prompt for more flexible matching
        import re
        instruction_match = re.search(r"INSTRUCTION:\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)
        instruction = instruction_match.group(1).strip() if instruction_match else ""

        # Look for a matching exchange
        for exchange in self.conversation["exchanges"]:
            # First try exact match
            if exchange["prompt"]["text"] == prompt:
                return exchange

            # Then try hash match if it's not the placeholder
            if exchange["prompt"]["hash"] != "sha256-hash-of-prompt-for-verification" and exchange["prompt"]["hash"] == prompt_hash:
                return exchange

            # Finally, try matching by instruction
            if instruction and instruction in exchange["prompt"]["text"]:
                logger.info(f"Found matching exchange by instruction: {instruction[:50]}...")
                return exchange

        return None

    def get_response_for_prompt(self, prompt: str) -> Optional[str]:
        """
        Get the response for a prompt from the conversation history.

        Args:
            prompt: The prompt to match

        Returns:
            The response text, or None if no match is found
        """
        exchange = self.find_matching_exchange(prompt)

        if exchange:
            return exchange["response"]["text"]

        return None

    def get_tool_calls_for_prompt(self, prompt: str) -> List[Dict[str, Any]]:
        """
        Get the tool calls for a prompt from the conversation history.

        Args:
            prompt: The prompt to match

        Returns:
            The list of tool calls, or an empty list if no match is found
        """
        exchange = self.find_matching_exchange(prompt)

        if exchange and "tool_calls" in exchange["response"]:
            return exchange["response"]["tool_calls"]

        return []
