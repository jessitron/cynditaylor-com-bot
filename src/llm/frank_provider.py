import re

from opentelemetry import trace

from .provider import LLMProvider

tracer = trace.get_tracer("cynditaylor-com-bot")


class FrankProvider(LLMProvider):
    """
    Implementation of LLMProvider for the 'Frank' LLM.
    This simulates an LLM that can suggest tool usage in its responses.

    Important:
    - This provider makes exactly one call to the LLM
    - It does not execute tools or handle tool loops
    - Tool execution is the responsibility of the agent
    """

    def __init__(self, model: str = "default"):
        """
        Initialize the Frank LLM provider.

        Args:
            model: The model to use for generation
        """
        self.model = model

    def generate(self, prompt: str, **_) -> str:
        """
        Generate a response from Frank LLM based on the prompt.
        Makes exactly one call to the LLM and returns the response.

        Args:
            prompt: The input prompt to send to the LLM
            **_: Additional parameters for the API call (ignored)

        Returns:
            The generated text response from the LLM
        """
        # Extract the instruction from the prompt
        instruction = self._extract_instruction(prompt)

        # Generate a response based on the instruction
        response = self._generate_response(instruction)

        return response

    def _extract_instruction(self, prompt: str) -> str:
        """
        Extract the instruction from the prompt.

        Args:
            prompt: The prompt to extract the instruction from

        Returns:
            The extracted instruction
        """
        # Extract the actual instruction from the prompt
        instruction_match = re.search(r"INSTRUCTION:\s*(.*?)(?:\n\n|$)", prompt, re.DOTALL)
        if instruction_match:
            return instruction_match.group(1).strip()
        return prompt

    def _generate_response(self, instruction: str) -> str:
        """
        Generate a response based on the instruction.
        This is where the actual LLM call would happen in a real implementation.

        Args:
            instruction: The instruction to generate a response for

        Returns:
            The generated response
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
