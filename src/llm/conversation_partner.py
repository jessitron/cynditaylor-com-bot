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

    def finish_conversation(self) -> None:
        """
        Called at the end of a conversation to perform any cleanup or finalization.
        This is an optional method with a default no-op implementation.
        """
        pass

