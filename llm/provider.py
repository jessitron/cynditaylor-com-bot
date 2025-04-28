from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    This allows for easy swapping of different LLM backends.
    """
    
    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Generate a response from the LLM based on the prompt.
        
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
