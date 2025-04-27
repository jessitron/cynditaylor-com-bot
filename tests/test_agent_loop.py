import unittest
from unittest.mock import MagicMock, patch
import json
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agent.agent import Agent
from src.agent.anthropic_adapter import AnthropicAdapter

class TestAgentLoop(unittest.TestCase):
    def setUp(self):
        self.mock_anthropic = MagicMock(spec=AnthropicAdapter)

        self.mock_anthropic.generate_response.return_value = {
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

        self.agent = Agent(anthropic_adapter=self.mock_anthropic)

    def test_agent_loop_with_hardcoded_instructions(self):
        instructions = "Update the website title to 'Cyndi Taylor - Artist'"

        with patch('src.agent.agent.execute_tool') as mock_execute_tool:
            mock_execute_tool.return_value = "File content or tool result"

            result = self.agent.run(instructions)

            self.mock_anthropic.generate_response.assert_called()

            call_args = self.mock_anthropic.generate_response.call_args[0]
            self.assertIn(instructions, str(call_args))

            mock_execute_tool.assert_called_with("read_file", {"path": "src/index.js"})

            self.assertIsNotNone(result)

if __name__ == '__main__':
    unittest.main()