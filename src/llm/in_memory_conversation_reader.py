from src.conversation.types import Conversation


class InMemoryConversationReader:
    def __init__(self, conversation: Conversation):
        self.conversation = conversation

    def load_conversation(self) -> Conversation:
        return self.conversation