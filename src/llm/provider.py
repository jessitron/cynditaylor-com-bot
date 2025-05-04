from abc import ABC, abstractmethod

from src.llm.conversation_partner import ConversationPartner

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    This allows for easy swapping of different LLM backends.
    """

    @abstractmethod
    def start_conversation(self) -> ConversationPartner:
        pass
