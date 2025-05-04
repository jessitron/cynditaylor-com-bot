import unittest
import os
import json
import tempfile
from src.llm.conversation_reader import ConversationReader


class TestConversationReader(unittest.TestCase):

    def setUp(self):
        # Create a temporary conversation file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")

        # Create a test conversation
        self.test_prompt1 = "Test prompt 1"
        self.test_response1 = "Test response 1"
        self.test_prompt2 = "Test prompt 2"
        self.test_response2 = "Test response 2"

        self.test_conversation = {
            "version": "1.0",
            "conversation_id": "test-id",
            "timestamp": "2023-06-15T14:30:00Z",
            "exchanges": [
                {
                    "id": "exchange-1",
                    "prompt": {
                        "text": self.test_prompt1,
                        "metadata": {
                            "temperature": 0.7,
                            "max_tokens": 1000
                        }
                    },
                    "response": {
                        "text": self.test_response1,
                        "tool_calls": []
                    }
                },
                {
                    "id": "exchange-2",
                    "prompt": {
                        "text": self.test_prompt2,
                        "metadata": {
                            "temperature": 0.7,
                            "max_tokens": 1000
                        }
                    },
                    "response": {
                        "text": self.test_response2,
                        "tool_calls": [
                            {
                                "tool_name": "test_tool",
                                "parameters": {"param": "value"},
                                "result": {"success": True}
                            }
                        ]
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
        # Remove the temporary file
        os.unlink(self.temp_file.name)

    def test_init(self):
        self.assertEqual(self.reader.conversation_file, self.temp_file.name)
        self.assertEqual(self.reader.conversation, self.test_conversation)
        self.assertEqual(self.reader.current_exchange_index, 0)

    def test_get_response_for_prompt_sequential(self):
        # Test with the first prompt
        response = self.reader.get_response_for_prompt(self.test_prompt1)
        self.assertEqual(response, self.test_response1)
        self.assertEqual(self.reader.current_exchange_index, 1)

        # Test with the second prompt
        response = self.reader.get_response_for_prompt(self.test_prompt2)
        self.assertEqual(response, self.test_response2)
        self.assertEqual(self.reader.current_exchange_index, 2)

        # Test with a third prompt (should raise an error)
        with self.assertRaises(ValueError):
            self.reader.get_response_for_prompt("Test prompt 3")

    def test_get_response_for_prompt_mismatch(self):
        # Test with a non-matching prompt
        with self.assertRaises(ValueError):
            self.reader.get_response_for_prompt("Non-matching prompt")

    def test_get_tool_calls_for_prompt(self):
        # First get a response to advance the index
        self.reader.get_response_for_prompt(self.test_prompt1)

        # Now get tool calls for the previous exchange
        tool_calls = self.reader.get_tool_calls_for_prompt()
        self.assertEqual(tool_calls, [])

        # Get the next response to advance to the exchange with tool calls
        self.reader.get_response_for_prompt(self.test_prompt2)

        # Now get tool calls for the previous exchange
        tool_calls = self.reader.get_tool_calls_for_prompt()
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0]["tool_name"], "test_tool")


if __name__ == "__main__":
    unittest.main()
