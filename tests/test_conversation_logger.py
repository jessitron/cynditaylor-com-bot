import unittest
import os
import json
import shutil
from src.conversation.logger import ConversationLogger


class TestConversationLogger(unittest.TestCase):

    def setUp(self):
        self.test_dir = "test_conversation_history"
        # Create a test directory
        os.makedirs(self.test_dir, exist_ok=True)
        self.logger = ConversationLogger(output_dir=self.test_dir)

    def tearDown(self):
        # Remove the test directory
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_init(self):
        self.assertEqual(self.logger.output_dir, self.test_dir)
        self.assertIsNotNone(self.logger.conversation_id)
        self.assertIsNotNone(self.logger.timestamp)
        self.assertEqual(self.logger.exchanges, [])
        self.assertIsNone(self.logger.previous_prompt)

    def test_find_new_portion(self):
        # Test with no previous prompt
        self.assertIsNone(self.logger.find_new_portion("Test prompt", None))

        # Test with identical prompts
        self.assertEqual(self.logger.find_new_portion("Test prompt", "Test prompt"), "")

        # Test with different prompts
        self.assertEqual(
            self.logger.find_new_portion("Test prompt with new text", "Test prompt"),
            "with new text"
        )

    def test_log_exchange(self):
        prompt = "Test prompt"
        response = "Test response"
        metadata = {"temperature": 0.7}

        self.logger.log_exchange(prompt, response, metadata)

        # Check that the exchange was added
        self.assertEqual(len(self.logger.exchanges), 1)
        exchange = self.logger.exchanges[0]
        self.assertEqual(exchange["id"], "exchange-1")
        self.assertEqual(exchange["prompt"]["text"], prompt)
        self.assertEqual(exchange["prompt"]["metadata"], metadata)
        self.assertEqual(exchange["response"]["text"], response)
        self.assertEqual(exchange["response"]["tool_calls"], [])

        # Check that the previous prompt was updated
        self.assertEqual(self.logger.previous_prompt, prompt)

    def test_log_exchange_with_new_portion(self):
        prompt1 = "Test prompt"
        response1 = "Test response"
        self.logger.log_exchange(prompt1, response1)

        prompt2 = "Test prompt with new text"
        response2 = "Test response 2"
        self.logger.log_exchange(prompt2, response2)

        # Check that the new portion was added
        self.assertEqual(len(self.logger.exchanges), 2)
        exchange = self.logger.exchanges[1]
        self.assertEqual(exchange["prompt"]["new_portion"], "with new text")

    def test_log_tool_call(self):
        prompt = "Test prompt"
        response = "Test response"
        self.logger.log_exchange(prompt, response)

        tool_name = "test_tool"
        parameters = {"param1": "value1"}
        result = {"success": True}

        self.logger.log_tool_call("exchange-1", tool_name, parameters, result)

        # Check that the tool call was added
        exchange = self.logger.exchanges[0]
        self.assertEqual(len(exchange["response"]["tool_calls"]), 1)
        tool_call = exchange["response"]["tool_calls"][0]
        self.assertEqual(tool_call["tool_name"], tool_name)
        self.assertEqual(tool_call["parameters"], parameters)
        self.assertEqual(tool_call["result"], result)

    def test_save(self):
        prompt = "Test prompt"
        response = "Test response"
        self.logger.log_exchange(prompt, response)

        file_path = self.logger.save()

        # Check that the file exists
        self.assertTrue(os.path.exists(file_path))

        # Check the file contents
        with open(file_path, "r") as f:
            data = json.load(f)

        self.assertEqual(data["version"], "1.0")
        self.assertEqual(data["conversation_id"], self.logger.conversation_id)
        self.assertEqual(data["timestamp"], self.logger.timestamp)
        self.assertEqual(len(data["exchanges"]), 1)


if __name__ == "__main__":
    unittest.main()
