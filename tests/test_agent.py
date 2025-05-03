import unittest
import os
import json
from unittest.mock import patch, MagicMock

from src.llm.provider import LLMProvider
from src.agent.agent import WebsiteAgent


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def generate(self, prompt, **kwargs):
        self.calls.append(prompt)

        # Return a predefined response if available, otherwise a default
        for key, response in self.responses.items():
            if key in prompt:
                return response

        return json.dumps({
            "files_to_modify": ["index.html"],
            "actions": ["Update the hero section with a new tagline"],
            "reasoning": "The instruction asks to update the hero section"
        })

    def get_name(self):
        return "MockLLM"


class TestWebsiteAgent(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory structure for testing
        os.makedirs("test_website", exist_ok=True)
        with open("test_website/index.html", "w") as f:
            f.write("<html><body><div class='hero'>Old content</div></body></html>")

    def tearDown(self):
        # Clean up the temporary directory
        if os.path.exists("test_website/index.html"):
            os.remove("test_website/index.html")
        if os.path.exists("test_website"):
            os.rmdir("test_website")

    def test_init(self):
        """Test initialization of WebsiteAgent."""
        llm = MockLLMProvider()
        agent = WebsiteAgent(llm, website_dir="test_website")
        self.assertEqual(agent.website_dir, "test_website")
        self.assertEqual(agent.llm, llm)

    def test_init_with_nonexistent_dir(self):
        """Test initialization with non-existent directory raises ValueError."""
        llm = MockLLMProvider()
        with self.assertRaises(ValueError):
            WebsiteAgent(llm, website_dir="nonexistent_dir")

    @patch("src.agent.agent.FileTools")
    @patch("src.agent.agent.GitTools")
    def test_process_instruction(self, mock_git_tools, mock_file_tools):
        """Test processing an instruction."""
        # Set up mocks
        mock_file_tools_instance = MagicMock()
        mock_file_tools.return_value = mock_file_tools_instance
        mock_file_tools_instance.file_exists.return_value = True
        mock_file_tools_instance.read_file.return_value = "<html><body><div class='hero'>Old content</div></body></html>"
        mock_file_tools_instance.write_file.return_value = True

        mock_git_tools_instance = MagicMock()
        mock_git_tools.return_value = mock_git_tools_instance
        mock_git_tools_instance.commit_changes.return_value = (True, "Changes committed")

        # Create agent with mock LLM
        llm = MockLLMProvider(responses={
            "Please provide the complete new content": "<html><body><div class='hero'>New content</div></body></html>"
        })
        agent = WebsiteAgent(llm, website_dir="test_website")

        # Process an instruction
        result = agent.process_instruction("Update the hero section")

        # Verify the result
        self.assertEqual(result["instruction"], "Update the hero section")
        self.assertEqual(len(result["results"]), 2)  # One file modification + one commit
        self.assertTrue(result["results"][0]["success"])
        self.assertEqual(result["results"][0]["file"], "index.html")
        self.assertTrue(result["results"][1]["success"])
        self.assertEqual(result["results"][1]["action"], "commit")

        # Verify the LLM was called
        self.assertEqual(len(llm.calls), 2)  # Analysis + modification

    @patch("src.agent.agent.WebsiteAgent.process_instruction")
    def test_execute_instruction(self, mock_process_instruction):
        """Test executing an instruction and generating a summary."""
        # Set up mock
        mock_process_instruction.return_value = {
            "instruction": "Test instruction",
            "results": [{"file": "index.html", "success": True}],
            "llm_provider": "MockLLM"
        }

        # Create agent with mock LLM
        llm = MockLLMProvider(responses={
            "Please provide a concise, human-readable summary": "Successfully updated the hero section."
        })
        agent = WebsiteAgent(llm, website_dir="test_website")

        # Execute an instruction
        result = agent.execute_instruction("Test instruction")

        # Verify the result
        self.assertEqual(result, "Successfully updated the hero section.")
        mock_process_instruction.assert_called_once_with("Test instruction")


if __name__ == "__main__":
    unittest.main()
