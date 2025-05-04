import unittest
from src.llm.frank_llm.frank import Frank
from src.llm.conversation_partner import ConversationPartner
from src.conversation.types import Exchange, Prompt, Response, PromptMetadata

class TestFrank(unittest.TestCase):

    def test_get_response_for_prompt(self):
        # Create a list of exchanges for testing using the new Exchange type
        exchanges = [
            Exchange(
                id="exchange-1",
                prompt=Prompt(text="What is your name?", metadata=PromptMetadata()),
                response=Response(text="My name is Frank.")
            ),
            Exchange(
                id="exchange-2",
                prompt=Prompt(text="What is your favorite color?", metadata=PromptMetadata()),
                response=Response(text="My favorite color is blue.")
            )
        ]
        frank = Frank(exchanges)

        # Test the get_response_for_prompt method
        response = frank.get_response_for_prompt("What is your name?")
        self.assertEqual(response, "My name is Frank.")

        response = frank.get_response_for_prompt("What is your favorite color?")
        self.assertEqual(response, "My favorite color is blue.")
