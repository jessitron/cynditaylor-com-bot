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

    def _normalize_text(self, text: str) -> str:
        """Normalize text by removing extra whitespace for comparison"""
        # Replace multiple whitespace with a single space
        normalized = ' '.join(text.split())
        return normalized

    def _extract_instruction(self, prompt: str) -> str:
        """Extract the instruction part from a prompt"""
        import re
        instruction_match = re.search(r"INSTRUCTION:\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)
        return instruction_match.group(1).strip() if instruction_match else ""

    def _prompts_match(self, expected: str, received: str) -> bool:
        """Check if prompts match using various strategies"""
        # Strategy 1: Exact match after normalization
        if self._normalize_text(expected) == self._normalize_text(received):
            return True

        # Strategy 2: Check if the instructions match
        expected_instruction = self._extract_instruction(expected)
        received_instruction = self._extract_instruction(received)

        if expected_instruction and received_instruction and expected_instruction == received_instruction:
            logger.info("Prompts match based on identical instructions")
            return True

        # Strategy 3: Check if one contains the other
        norm_expected = self._normalize_text(expected)
        norm_received = self._normalize_text(received)

        if norm_expected in norm_received or norm_received in norm_expected:
            logger.info("Prompts match based on substring containment")
            return True

        # No match found
        return False

    def get_response_for_prompt(self, prompt: str) -> Optional[str]:
        # Check if we've reached the end of the conversation
        if self.current_exchange_index >= len(self.conversation["exchanges"]):
            logger.error("End of conversation reached, no more exchanges available")
            raise ValueError("End of conversation reached, no more exchanges available")

        # Get the current exchange
        current_exchange = self.conversation["exchanges"][self.current_exchange_index]
        expected_prompt = current_exchange["prompt"]["text"]

        # Check if the prompts match using our flexible matching
        if self._prompts_match(expected_prompt, prompt):
            # Move to the next exchange for the next call
            self.current_exchange_index += 1
            logger.info(f"Matched prompt at exchange index {self.current_exchange_index - 1}")
            return current_exchange["response"]["text"]
        else:
            # Log the mismatch details for debugging
            logger.error(f"Prompt mismatch at exchange index {self.current_exchange_index}")
            logger.error(f"Expected (normalized): {self._normalize_text(expected_prompt)[:100]}...")
            logger.error(f"Received (normalized): {self._normalize_text(prompt)[:100]}...")

            # Extract and compare instructions
            expected_instruction = self._extract_instruction(expected_prompt)
            received_instruction = self._extract_instruction(prompt)
            logger.error(f"Expected instruction: {expected_instruction}")
            logger.error(f"Received instruction: {received_instruction}")

            # Raise an error with details about the mismatch
            raise ValueError(
                f"Prompt does not match the expected prompt at position {self.current_exchange_index}. "
                f"Expected instruction: '{expected_instruction}' "
                f"Received instruction: '{received_instruction}'"
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
