import unittest
import os
from src.llm.conversation_reader import ConversationReader
from src.conversation.types import Prompt, Response

class TestConversationReader(unittest.TestCase):
    
    def test_load_conversation_history(self):
        # Test loading the conversation history file
        reader = ConversationReader("conversation_history/test_conversation.json")
        conversation = reader.load_conversation()
        
        # Check that the conversation was loaded correctly
        self.assertEqual(conversation.conversation_id, "test-conversation-id")
        self.assertEqual(len(conversation.exchanges), 2)
        
        # Check the first exchange
        first_exchange = conversation.exchanges[0]
        self.assertEqual(first_exchange.id, "exchange-1")
        self.assertEqual(first_exchange.prompt.prompt_text, "Update the hero section on the homepage to include a new tagline: 'Bringing your memories to life through art'")
        self.assertEqual(first_exchange.response.response_text, "I'll help you update the hero section with a new tagline. First, I need to see what files are available in the website directory.")
        
        # Check the second exchange
        second_exchange = conversation.exchanges[1]
        self.assertEqual(second_exchange.id, "exchange-2")
        self.assertTrue("Tool call:" in second_exchange.prompt.new_text)
        self.assertEqual(len(second_exchange.prompt.tool_calls), 1)
        self.assertEqual(second_exchange.prompt.tool_calls[0].tool_name, "list_files")
        
if __name__ == "__main__":
    unittest.main()
