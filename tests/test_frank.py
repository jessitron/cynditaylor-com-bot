import unittest
from src.llm.frank_llm.frank import Frank
from src.llm.conversation_partner import ConversationPartner

class TestFrank(unittest.TestCase):

    def test_get_response_for_prompt(self):
        # Create a list of exchanges for testing    
        exchanges = [
            {"prompt": "What is your name?", "response": "My name is Frank."},
            {"prompt": "What is your favorite color?", "response": "My favorite color is blue."}
        ]
        frank = Frank(exchanges)

        # Test the get_response_for_prompt method
        response = frank.get_response_for_prompt("What is your name?")
        self.assertEqual(response, "My name is Frank.") 

        response = frank.get_response_for_prompt("What is your favorite color?")
        self.assertEqual(response, "My favorite color is blue.")
