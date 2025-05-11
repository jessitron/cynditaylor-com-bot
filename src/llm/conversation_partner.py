from abc import ABC, abstractmethod

from src.conversation.types import Prompt, Response

class ConversationPartner(ABC):
    """
    Please get one of theses from an LLMProvider.
    """

    @abstractmethod
    def get_response_for_prompt(self, prompt: Prompt) -> Response:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    def finish_conversation(self) -> dict:
        """
        Called at the end of a conversation to perform any cleanup or finalization.
        This is an optional method with a default no-op implementation.

        Returns:
            A dictionary of metadata about the conversation, or None
        """
        return {}

