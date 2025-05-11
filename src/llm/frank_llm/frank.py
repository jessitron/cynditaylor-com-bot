import os
import logging
import re

from opentelemetry import trace

from src.llm.conversation_partner import ConversationPartner
from src.conversation.types import Exchange, ToolCall, Prompt, Response

logger = logging.getLogger(__name__)


class Frank(ConversationPartner):

    def __init__(self, exchanges: list[Exchange]):
        self.exchanges = exchanges
        self.index = 0

    def _extract_instruction(self, prompt_text: str) -> str:
        """
        Extract the instruction part from a prompt text.

        This method looks for the instruction between "INSTRUCTION:" and the next section,
        or extracts the first line if no instruction marker is found.

        Args:
            prompt_text: The full prompt text

        Returns:
            The extracted instruction text
        """
        # Try to find the instruction between "INSTRUCTION:" and the next section
        instruction_match = re.search(r'INSTRUCTION:\s*(.*?)(?:\n\n|$)', prompt_text, re.DOTALL)
        if instruction_match:
            return instruction_match.group(1).strip()

        # If no instruction marker is found, use the first non-empty line
        # or the entire text if it's a single line
        lines = [line.strip() for line in prompt_text.split('\n') if line.strip()]
        if lines:
            return lines[0]

        # If all else fails, return the original text
        return prompt_text.strip()

    def get_response_for_prompt(self, prompt: Prompt, **_) -> Response:
        if self.index >= len(self.exchanges):
            raise ValueError("End of conversation reached, no more exchanges available")

        span = trace.get_current_span()
        span.set_attribute("app.frank.current_exchange", str(self.exchanges[self.index]))
        span.set_attribute("app.frank.index", self.index)

        current_exchange = self.exchanges[self.index]

        # Extract instructions from both prompts
        expected_instruction = self._extract_instruction(current_exchange.prompt.prompt_text)
        received_instruction = self._extract_instruction(prompt.prompt_text)

        # Compare the extracted instructions
        if expected_instruction != received_instruction:
            # Only log a warning if the instructions don't match
            logger.warning(f"Instruction mismatch at index {self.index}",
                          extra={"instruction.expected": expected_instruction,
                                "instruction.received": received_instruction})

        # Get the response from the current exchange
        response = Response(
            response_text=current_exchange.response.response_text,
            tool_calls=current_exchange.response.tool_calls
        )

        self.index += 1
        return response

    def finish_conversation(self) -> dict:
        if self.index < len(self.exchanges):
            logger.warning(f"Conversation ended before all exchanges were used. Unused exchanges: {len(self.exchanges) - self.index}")
        return {}

    def get_name(self) -> str:
        return "Frank"
