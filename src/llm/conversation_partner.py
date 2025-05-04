from abc import ABC, abstractmethod

from src.llm.prompt import Prompt # TODO: use a structured prompt

class ConversationPartner(ABC):
    """
    Please get one of theses from an LLMProvider.
    """

    @abstractmethod
    def get_response_for_prompt(self, prompt: str) -> str:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

