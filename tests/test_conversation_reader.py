import unittest
import os
import json
import tempfile
from src.llm.conversation_reader import ConversationReader
from src.conversation.hash_util import hash_prompt


class TestConversationReader(unittest.TestCase):
    """Test the ConversationReader class."""

    def setUp(self):
        """Set up the test environment."""
        # Create a temporary conversation file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        
        # Create a test conversation
        self.test_prompt = "Test prompt"
        self.test_response = "Test response"
        self.test_conversation = {
            "version": "1.0",
            "conversation_id": "test-id",
            "timestamp": "2023-06-15T14:30:00Z",
            "exchanges": [
                {
                    "id": "exchange-1",
                    "prompt": {
                        "text": self.test_prompt,
                        "hash": hash_prompt(self.test_prompt),
                        "metadata": {
                            "temperature": 0.7,
                            "max_tokens": 1000
                        }
                    },
                    "response": {
                        "text": self.test_response,
                        "tool_calls": []
                    }
                }
            ]
        }
        
        # Write the test conversation to the file
        with open(self.temp_file.name, "w") as f:
            json.dump(self.test_conversation, f)
            
        # Create the reader
        self.reader = ConversationReader(self.temp_file.name)

    def tearDown(self):
        """Clean up after the test."""
        # Remove the temporary file
        os.unlink(self.temp_file.name)

    def test_init(self):
        """Test initialization of ConversationReader."""
        self.assertEqual(self.reader.conversation_file, self.temp_file.name)
        self.assertEqual(self.reader.conversation, self.test_conversation)
        self.assertEqual(self.reader.current_exchange_index, 0)

    def test_find_matching_exchange(self):
        """Test find_matching_exchange method."""
        # Test with a matching prompt
        exchange = self.reader.find_matching_exchange(self.test_prompt)
        self.assertIsNotNone(exchange)
        self.assertEqual(exchange["id"], "exchange-1")
        
        # Test with a non-matching prompt
        exchange = self.reader.find_matching_exchange("Non-matching prompt")
        self.assertIsNone(exchange)

    def test_get_response_for_prompt(self):
        """Test get_response_for_prompt method."""
        # Test with a matching prompt
        response = self.reader.get_response_for_prompt(self.test_prompt)
        self.assertEqual(response, self.test_response)
        
        # Test with a non-matching prompt
        response = self.reader.get_response_for_prompt("Non-matching prompt")
        self.assertIsNone(response)

    def test_get_tool_calls_for_prompt(self):
        """Test get_tool_calls_for_prompt method."""
        # Test with a matching prompt
        tool_calls = self.reader.get_tool_calls_for_prompt(self.test_prompt)
        self.assertEqual(tool_calls, [])
        
        # Test with a non-matching prompt
        tool_calls = self.reader.get_tool_calls_for_prompt("Non-matching prompt")
        self.assertEqual(tool_calls, [])
        
        # Add a test conversation with tool calls
        tool_prompt = "Tool prompt"
        self.test_conversation["exchanges"].append({
            "id": "exchange-2",
            "prompt": {
                "text": tool_prompt,
                "hash": hash_prompt(tool_prompt),
                "metadata": {
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            },
            "response": {
                "text": "Tool response",
                "tool_calls": [
                    {
                        "tool_name": "test_tool",
                        "parameters": {"param": "value"},
                        "result": {"success": True}
                    }
                ]
            }
        })
        
        # Write the updated test conversation to the file
        with open(self.temp_file.name, "w") as f:
            json.dump(self.test_conversation, f)
            
        # Create a new reader with the updated file
        reader = ConversationReader(self.temp_file.name)
        
        # Test with a prompt that has tool calls
        tool_calls = reader.get_tool_calls_for_prompt(tool_prompt)
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0]["tool_name"], "test_tool")


if __name__ == "__main__":
    unittest.main()
