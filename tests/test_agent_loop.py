"""
Test for the main agent loop.

This test uses hard-coded instructions to test the agent loop functionality.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch

from src.agent.agent import WebsiteAgent
from src.agent.tools import AVAILABLE_TOOLS

class TestAgentLoop:
    """Test cases for the agent loop."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client for testing."""
        mock_client = MagicMock()

        # Mock the messages.create method
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = """
        I'll help you update the title of the homepage.

        First, let's pull the latest changes from the repository:

        <tool>git_pull</tool>
        <arguments>
        {
          "repo_path": "./website_repo"
        }
        </arguments>

        Now, let's read the current homepage file:

        <tool>read_file</tool>
        <arguments>
        {
          "file_path": "./website_repo/index.html"
        }
        </arguments>

        Now I'll update the title in the HTML file:

        <tool>modify_file</tool>
        <arguments>
        {
          "file_path": "./website_repo/index.html",
          "content": "<!DOCTYPE html>\\n<html>\\n<head>\\n  <title>Cyndi Taylor - Artist</title>\\n</head>\\n<body>\\n  <h1>Welcome to Cyndi Taylor's Art Gallery</h1>\\n</body>\\n</html>"
        }
        </arguments>

        Finally, let's commit and push the changes:

        <tool>git_push</tool>
        <arguments>
        {
          "repo_path": "./website_repo",
          "commit_message": "Update homepage title to 'Cyndi Taylor - Artist'"
        }
        </arguments>

        I've updated the title of the homepage to 'Cyndi Taylor - Artist'. The changes have been committed and pushed to the repository.
        """
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        return mock_client

    @pytest.fixture
    def mock_tools(self):
        """Create mock tools for testing."""
        mock_git_pull = MagicMock(return_value={"success": True, "output": "Already up to date."})
        mock_read_file = MagicMock(return_value={
            "success": True,
            "file_path": "./website_repo/index.html",
            "content": "<!DOCTYPE html>\n<html>\n<head>\n  <title>Cyndi Taylor</title>\n</head>\n<body>\n  <h1>Welcome to Cyndi Taylor's Art Gallery</h1>\n</body>\n</html>"
        })
        mock_modify_file = MagicMock(return_value={"success": True, "file_path": "./website_repo/index.html"})
        mock_git_push = MagicMock(return_value={"success": True, "commit_output": "1 file changed", "push_output": "Everything up-to-date"})

        return {
            "git_pull": mock_git_pull,
            "read_file": mock_read_file,
            "modify_file": mock_modify_file,
            "git_push": mock_git_push
        }

    def test_agent_loop_with_hardcoded_instructions(self, mock_llm_client, mock_tools):
        """Test the agent loop with hard-coded instructions."""
        # Create agent with mock LLM client and tools
        agent = WebsiteAgent(mock_llm_client, mock_tools)

        # Hard-coded instructions
        instructions = "Update the title of the homepage to 'Cyndi Taylor - Artist'"

        # Run agent loop
        actions = agent.run_agent_loop(instructions)

        # Verify that the LLM client was called at least once
        assert mock_llm_client.messages.create.call_count >= 1

        # Verify that the tools were called at least once
        assert mock_tools["git_pull"].call_count >= 1
        assert mock_tools["read_file"].call_count >= 1
        assert mock_tools["modify_file"].call_count >= 1
        assert mock_tools["git_push"].call_count >= 1

        # Verify that the actions list contains the expected actions
        # Since the agent might call the tools multiple times, we need to check
        # that the actions list contains at least one of each expected action
        assert len(actions) >= 4

        # Get the tool names from the actions
        tool_names = [action["tool"] for action in actions]

        # Check that each required tool was called at least once
        assert "git_pull" in tool_names
        assert "read_file" in tool_names
        assert "modify_file" in tool_names
        assert "git_push" in tool_names

        # Verify that the tools were called with the expected arguments at least once
        # We can't use assert_called_with because the tools might be called multiple times
        # with different arguments, so we need to check the call args

        # Check git_pull was called with the expected arguments
        git_pull_called_with_expected_args = False
        for call_args in mock_tools["git_pull"].call_args_list:
            if call_args[1] == {"repo_path": "./website_repo"}:
                git_pull_called_with_expected_args = True
                break
        assert git_pull_called_with_expected_args

        # Check read_file was called with the expected arguments
        read_file_called_with_expected_args = False
        for call_args in mock_tools["read_file"].call_args_list:
            if call_args[1] == {"file_path": "./website_repo/index.html"}:
                read_file_called_with_expected_args = True
                break
        assert read_file_called_with_expected_args

        # Check modify_file was called with the expected arguments
        expected_modify_args = {
            "file_path": "./website_repo/index.html",
            "content": "<!DOCTYPE html>\n<html>\n<head>\n  <title>Cyndi Taylor - Artist</title>\n</head>\n<body>\n  <h1>Welcome to Cyndi Taylor's Art Gallery</h1>\n</body>\n</html>"
        }
        modify_file_called_with_expected_args = False
        for call_args in mock_tools["modify_file"].call_args_list:
            if call_args[1] == expected_modify_args:
                modify_file_called_with_expected_args = True
                break
        assert modify_file_called_with_expected_args

        # Check git_push was called with the expected arguments
        expected_push_args = {
            "repo_path": "./website_repo",
            "commit_message": "Update homepage title to 'Cyndi Taylor - Artist'"
        }
        git_push_called_with_expected_args = False
        for call_args in mock_tools["git_push"].call_args_list:
            if call_args[1] == expected_push_args:
                git_push_called_with_expected_args = True
                break
        assert git_push_called_with_expected_args
