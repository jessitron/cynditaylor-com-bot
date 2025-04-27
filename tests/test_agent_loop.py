import unittest
from unittest.mock import patch
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent.agent import Agent
from src.agent.fake_anthropic_adapter import FakeAnthropicAdapter

class TestAgentLoop(unittest.TestCase):
    def setUp(self):
        self.fake_anthropic = FakeAnthropicAdapter()

        # Add predefined responses for different test instructions
        self.fake_anthropic.add_response(
            "Update the website title",
            {
                "content": [
                    {
                        "type": "text",
                        "text": "I'll help you update the website."
                    },
                    {
                        "type": "tool_use",
                        "id": "tool_1",
                        "name": "read_file",
                        "input": {
                            "path": "src/index.js"
                        }
                    }
                ]
            }
        )

        self.fake_anthropic.add_response(
            "Add a new painting",
            {
                "content": [
                    {
                        "type": "text",
                        "text": "I'll help you add a new painting."
                    },
                    {
                        "type": "tool_use",
                        "id": "tool_2",
                        "name": "read_file",
                        "input": {
                            "path": "src/paintings.json"
                        }
                    }
                ]
            }
        )

        self.agent = Agent(anthropic_adapter=self.fake_anthropic)

    def test_agent_loop_with_hardcoded_instructions(self):
        instructions = "Update the website title to 'Cyndi Taylor - Artist'"

        with patch('src.agent.agent.execute_tool') as mock_execute_tool:
            mock_execute_tool.return_value = "File content or tool result"

            result = self.agent.run(instructions)

            # Verify the result contains the expected actions
            self.assertIsNotNone(result)
            self.assertIn("actions", result)
            self.assertEqual(1, len(result["actions"]))

            # Verify the tool was executed with the right parameters
            mock_execute_tool.assert_called_with("read_file", {"path": "src/index.js"})

            # Verify the action in the result
            action = result["actions"][0]
            self.assertEqual("read_file", action["tool"])
            self.assertEqual({"path": "src/index.js"}, action["input"])
            self.assertEqual("File content or tool result", action["result"])

    def test_agent_loop_with_different_instructions(self):
        instructions = "Add a new painting called 'Sunset'"

        with patch('src.agent.agent.execute_tool') as mock_execute_tool:
            mock_execute_tool.return_value = "Paintings JSON content"

            result = self.agent.run(instructions)

            # Verify the result contains the expected actions
            self.assertIsNotNone(result)
            self.assertIn("actions", result)
            self.assertEqual(1, len(result["actions"]))

            # Verify the tool was executed with the right parameters
            mock_execute_tool.assert_called_with("read_file", {"path": "src/paintings.json"})

            # Verify the action in the result
            action = result["actions"][0]
            self.assertEqual("read_file", action["tool"])
            self.assertEqual({"path": "src/paintings.json"}, action["input"])
            self.assertEqual("Paintings JSON content", action["result"])

    def test_agent_loop_with_unknown_instructions(self):
        instructions = "Do something completely different"

        result = self.agent.run(instructions)

        # Verify the result contains no actions for unknown instructions
        self.assertIsNotNone(result)
        self.assertIn("actions", result)
        self.assertEqual(0, len(result["actions"]))

if __name__ == '__main__':
    unittest.main()