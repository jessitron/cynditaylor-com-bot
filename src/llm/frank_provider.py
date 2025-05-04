import re
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

    def __init__(self, model: str = "default", replay_mode: bool = True):
        self.model = model
        self.replay_mode = replay_mode
        self.conversation_logger = ConversationLogger(output_dir="conversation_history")

        # Initialize the conversation reader if in replay mode
        if self.replay_mode:
            try:
                self.conversation_reader = ConversationReader(CONVERSATION_FILE)
                logger.info(f"Frank initialized in replay mode using conversation file: {CONVERSATION_FILE}")
            except Exception as e:
                logger.error(f"Error initializing conversation reader: {e}")
                # Fall back to normal mode if there's an error
                self.replay_mode = False
                logger.warning("Falling back to normal mode due to error")

    def generate(self, prompt: str, **kwargs) -> str:
        # Try to get a response from the conversation history if in replay mode
        if self.replay_mode:
            try:
                response = self.conversation_reader.get_response_for_prompt(prompt)
                if response:
                    logger.info("Found matching prompt in conversation history")
                    # Log the exchange even in replay mode
                    metadata = {
                        "model": self.model,
                        "temperature": kwargs.get("temperature", 0.7),
                        "max_tokens": kwargs.get("max_tokens", 1000),
                        "replay_mode": True
                    }
                    self.conversation_logger.log_exchange(prompt, response, metadata)
                    return response
                else:
                    logger.warning("No matching prompt found in conversation history")
                    raise ValueError(f"No matching prompt found in conversation history. Prompt: {prompt[:100]}...")
            except Exception as e:
                logger.error(f"Error in replay mode: {e}")
                # Fall back to normal mode if there's an error
                logger.warning("Falling back to normal mode due to error")
                self.replay_mode = False

        # If not in replay mode or no matching prompt was found, generate a response normally
        # Extract the instruction from the prompt
        instruction = self._extract_instruction(prompt)

        # Generate a response based on the instruction
        response = self._generate_response(instruction)

        # Log the exchange
        metadata = {
            "model": self.model,
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", 1000),
            "replay_mode": False
        }

        self.conversation_logger.log_exchange(prompt, response, metadata)

        return response

    def _extract_instruction(self, prompt: str) -> str:
        """
        Extract the instruction from the prompt. Frank uses this to prove a hard-coded response.
        """
        # Extract the actual instruction from the prompt
        instruction_match = re.search(r"INSTRUCTION:\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)
        if instruction_match:
            instruction = instruction_match.group(1).strip()
            trace.get_current_span().set_attribute("app.frank.instruction", instruction)
            return instruction
        return prompt

    def _generate_response(self, instruction: str) -> str:
        """
        Generate a response based on the instruction.
        This is where the actual LLM call would happen in a real implementation.
        """
        # Determine what kind of response to generate based on the instruction
        if "hero section" in instruction.lower() or "tagline" in instruction.lower():
            return """I'll help you update the hero section with a new tagline. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""

        elif "contact" in instruction.lower() or "email" in instruction.lower():
            return """I'll help you update the contact information. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""

        elif "gallery" in instruction.lower() or "image" in instruction.lower() or "painting" in instruction.lower():
            return """I'll help you update the gallery. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""

        elif "style" in instruction.lower() or "color" in instruction.lower() or "design" in instruction.lower():
            return """I'll help you update the styling. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""

        # Default response for other instructions
        return """I'll help you with that. First, I need to see what files are available in the website directory.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""

    def get_name(self) -> str:
        """
        Get the name of the LLM provider.

        Returns:
            The name of the LLM provider
        """
        return f"Frank ({self.model})"
