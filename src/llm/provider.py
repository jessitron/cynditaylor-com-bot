from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    This allows for easy swapping of different LLM backends.

    Important:
    - LLM providers should make exactly one call to the LLM
    - LLM providers should not execute tools or handle tool loops
    - Tool execution is the responsibility of the agent
    """

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a response from the LLM based on the prompt.
        Makes exactly one call to the LLM and returns the response.

        Args:
            prompt: The input prompt to send to the LLM
            **kwargs: Additional parameters specific to the LLM provider

        Returns:
            The generated text response from the LLM
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        Get the name of the LLM provider.

        Returns:
            The name of the LLM provider
        """
        pass
