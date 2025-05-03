import unittest
import os
import json
from unittest.mock import patch, MagicMock

from src.llm.frank_provider_with_tools import FrankProviderWithTools
from src.agent.agent_with_tools import WebsiteAgentWithTools


class TestWebsiteAgentWithTools(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory structure for testing
        os.makedirs("test_website", exist_ok=True)
        with open("test_website/index.html", "w") as f:
            f.write('<html><body><div class="hero-content"><h2>Title</h2><p>Old tagline</p></div></body></html>')

    def tearDown(self):
        # Clean up the temporary directory
        if os.path.exists("test_website/index.html"):
            os.remove("test_website/index.html")
        if os.path.exists("test_website"):
            os.rmdir("test_website")

    def test_init(self):
        """Test initialization of WebsiteAgentWithTools."""
        llm = FrankProviderWithTools()
        agent = WebsiteAgentWithTools(llm, website_dir="test_website")
        self.assertEqual(agent.website_dir, "test_website")
        self.assertEqual(agent.llm, llm)

    def test_init_with_nonexistent_dir(self):
        """Test initialization with non-existent directory raises ValueError."""
        llm = FrankProviderWithTools()
        with self.assertRaises(ValueError):
            WebsiteAgentWithTools(llm, website_dir="nonexistent_dir")

    def test_list_files_tool(self):
        """Test the list_files tool."""
        llm = FrankProviderWithTools()
        agent = WebsiteAgentWithTools(llm, website_dir="test_website")

        result = agent._list_files()
        self.assertTrue(result["success"])
        self.assertIn("index.html", result["files"])

    def test_read_file_tool(self):
        """Test the read_file tool."""
        llm = FrankProviderWithTools()
        agent = WebsiteAgentWithTools(llm, website_dir="test_website")

        result = agent._read_file("index.html")
        self.assertTrue(result["success"])
        self.assertIn('<div class="hero-content">', result["content"])

    def test_write_file_tool(self):
        """Test the write_file tool."""
        llm = FrankProviderWithTools()
        agent = WebsiteAgentWithTools(llm, website_dir="test_website")

        new_content = '<html><body><div class="hero-content"><h2>Title</h2><p>New tagline</p></div></body></html>'
        result = agent._write_file("index.html", new_content)
        self.assertTrue(result["success"])

        # Verify the file was updated
        with open("test_website/index.html", "r") as f:
            content = f.read()
        self.assertEqual(content, new_content)

    @patch("src.agent.agent_with_tools.GitTools")
    def test_commit_changes_tool(self, mock_git_tools):
        """Test the commit_changes tool."""
        # Set up mock
        mock_git_tools_instance = MagicMock()
        mock_git_tools.return_value = mock_git_tools_instance
        mock_git_tools_instance.commit_changes.return_value = (True, "Changes committed")

        llm = FrankProviderWithTools()
        agent = WebsiteAgentWithTools(llm, website_dir="test_website")

        result = agent._commit_changes("Test commit")
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Changes committed")

        # Verify the mock was called
        mock_git_tools_instance.commit_changes.assert_called_once_with("test_website", "Test commit")

    @patch("src.agent.agent_with_tools.GitTools")
    def test_push_changes_tool(self, mock_git_tools):
        """Test the push_changes tool."""
        # Set up mock
        mock_git_tools_instance = MagicMock()
        mock_git_tools.return_value = mock_git_tools_instance
        mock_git_tools_instance.push_changes.return_value = (True, "Changes pushed")

        llm = FrankProviderWithTools()
        agent = WebsiteAgentWithTools(llm, website_dir="test_website")

        result = agent._push_changes()
        self.assertTrue(result["success"])
        self.assertEqual(result["message"], "Changes pushed")

        # Verify the mock was called
        mock_git_tools_instance.push_changes.assert_called_once_with("test_website", "main")

    @patch("src.agent.agent_with_tools.WebsiteAgentWithTools._list_files")
    @patch("src.agent.agent_with_tools.WebsiteAgentWithTools._read_file")
    @patch("src.agent.agent_with_tools.WebsiteAgentWithTools._write_file")
    @patch("src.agent.agent_with_tools.WebsiteAgentWithTools._commit_changes")
    def test_execute_instruction(self, mock_commit, mock_write, mock_read, mock_list):
        """Test executing an instruction."""
        # Set up mocks
        mock_list.return_value = {"success": True, "files": ["index.html"]}
        mock_read.return_value = {
            "success": True,
            "content": '<html><body><div class="hero-content"><h2>Title</h2><p>Old tagline</p></div></body></html>'
        }
        mock_write.return_value = {"success": True, "message": "File written: index.html"}
        mock_commit.return_value = {"success": True, "message": "Changes committed"}

        # Create a custom FrankProviderWithTools that returns predefined responses
        class TestFrankProvider(FrankProviderWithTools):
            def generate(self, prompt, **kwargs):
                return "I've successfully updated the hero section with the new tagline and committed the changes."

        llm = TestFrankProvider()
        agent = WebsiteAgentWithTools(llm, website_dir="test_website")

        result = agent.execute_instruction("Update the hero section with a new tagline")

        # Verify the result
        self.assertIn("successfully updated", result.lower())


if __name__ == "__main__":
    unittest.main()
