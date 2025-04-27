"""
LLM client module for the Cyndi Taylor Website Bot.

This module handles interactions with the Anthropic API.
"""

import os
import logging
from typing import Dict, List, Any, Optional
from anthropic import Anthropic

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_anthropic_client() -> Anthropic:
    """
    Create and return an Anthropic client.
    
    Returns:
        Anthropic client instance
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    return Anthropic(api_key=api_key)

def get_system_prompt() -> str:
    """
    Get the system prompt for the agent.
    
    Returns:
        System prompt as a string
    """
    return """
    You are an AI assistant helping to update the Cyndi Taylor website based on instructions.
    
    You have access to the following tools:
    
    1. git_pull(repo_path: str) - Pull the latest changes from the GitHub repository
    2. git_push(repo_path: str, commit_message: str) - Commit and push changes to the GitHub repository
    3. modify_file(file_path: str, content: str) - Modify a file in the website repository
    4. read_file(file_path: str) - Read a file from the website repository
    
    When you need to use a tool, format your response like this:
    
    <tool>tool_name</tool>
    <arguments>
    {
      "arg1": "value1",
      "arg2": "value2"
    }
    </arguments>
    
    After using tools, explain what you did and why. If you need to use multiple tools, use them one at a time.
    
    Always start by pulling the latest changes from the repository, and end by pushing your changes with a descriptive commit message.
    """
