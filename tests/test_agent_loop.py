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
        
        # Verify that the LLM client was called
        mock_llm_client.messages.create.assert_called_once()
        
        # Verify that the tools were called in the expected order
        assert mock_tools["git_pull"].call_count == 1
        assert mock_tools["read_file"].call_count == 1
        assert mock_tools["modify_file"].call_count == 1
        assert mock_tools["git_push"].call_count == 1
        
        # Verify that the actions list contains the expected actions
        assert len(actions) == 4
        assert actions[0]["tool"] == "git_pull"
        assert actions[1]["tool"] == "read_file"
        assert actions[2]["tool"] == "modify_file"
        assert actions[3]["tool"] == "git_push"
        
        # Verify the arguments passed to the tools
        mock_tools["git_pull"].assert_called_with(repo_path="./website_repo")
        mock_tools["read_file"].assert_called_with(file_path="./website_repo/index.html")
        mock_tools["modify_file"].assert_called_with(
            file_path="./website_repo/index.html",
            content="<!DOCTYPE html>\n<html>\n<head>\n  <title>Cyndi Taylor - Artist</title>\n</head>\n<body>\n  <h1>Welcome to Cyndi Taylor's Art Gallery</h1>\n</body>\n</html>"
        )
        mock_tools["git_push"].assert_called_with(
            repo_path="./website_repo",
            commit_message="Update homepage title to 'Cyndi Taylor - Artist'"
        )
