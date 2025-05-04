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
                prompt=Prompt(prompt_text="What is your name?", metadata=PromptMetadata()),
                response=Response(response_text="My name is Frank.")
            ),
            Exchange(
                id="exchange-2",
                prompt=Prompt(prompt_text="What is your favorite color?", metadata=PromptMetadata()),
                response=Response(response_text="My favorite color is blue.")
            )
        ]
        frank = Frank(exchanges)

        # Test the get_response_for_prompt method
        prompt1 = Prompt(prompt_text="What is your name?", metadata=PromptMetadata())
        response1 = frank.get_response_for_prompt(prompt1)
        self.assertEqual(response1.response_text, "My name is Frank.")

        prompt2 = Prompt(prompt_text="What is your favorite color?", metadata=PromptMetadata())
        response2 = frank.get_response_for_prompt(prompt2)
        self.assertEqual(response2.response_text, "My favorite color is blue.")
