import os
import json
from pathlib import Path
import subprocess
from .anthropic_adapter import AnthropicAdapter

def execute_tool(tool_name, tool_input):
    """
    Execute a tool based on its name and input.

    Args:
        tool_name (str): The name of the tool to execute
        tool_input (dict): The input parameters for the tool

    Returns:
        str: The result of the tool execution
    """
    try:
        if tool_name == "read_file":
            path = tool_input.get('path')
            if not path:
                return "Error: No path provided"

            try:
                with open(path, 'r') as file:
                    content = file.read()
                return content
            except Exception as e:
                return f"Error reading file {path}: {str(e)}"

        elif tool_name == "write_file":
            path = tool_input.get('path')
            content = tool_input.get('content')

            if not path or content is None:
                return "Error: Path and content are required"

            try:
                # Ensure directory exists
                directory = os.path.dirname(path)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory)

                with open(path, 'w') as file:
                    file.write(content)
                return f"Successfully wrote to {path}"
            except Exception as e:
                return f"Error writing to file {path}: {str(e)}"

        elif tool_name == "list_files":
            directory = tool_input.get('directory', '.')

            try:
                files = []
                for item in Path(directory).glob('**/*'):
                    if item.is_file():
                        files.append(str(item))
                return json.dumps(files)
            except Exception as e:
                return f"Error listing files in {directory}: {str(e)}"

        elif tool_name == "git_pull":
            try:
                result = subprocess.run(
                    ["git", "pull"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout
            except subprocess.CalledProcessError as e:
                return f"Error executing git pull: {e.stderr}"

        elif tool_name == "git_push":
            try:
                # First commit any changes
                message = tool_input.get('message', 'Update website - auggie')

                # Add all changes
                add_result = subprocess.run(
                    ["git", "add", "."],
                    capture_output=True,
                    text=True,
                    check=True
                )

                # Commit changes
                commit_result = subprocess.run(
                    ["git", "commit", "-m", message],
                    capture_output=True,
                    text=True
                )

                # Push changes
                push_result = subprocess.run(
                    ["git", "push"],
                    capture_output=True,
                    text=True,
                    check=True
                )

                return f"Add: {add_result.stdout}\nCommit: {commit_result.stdout}\nPush: {push_result.stdout}"
            except subprocess.CalledProcessError as e:
                return f"Error executing git operations: {e.stderr}"

        return f"Unknown tool: {tool_name}"
    except Exception as e:
        return f"Error executing tool {tool_name}: {str(e)}"

class Agent:
    """
    Agent that processes instructions, calls the Anthropic API, and executes tools.
    """

    def __init__(self, anthropic_adapter=None):
        """
        Args:
            anthropic_adapter (AnthropicAdapter): Adapter for the Anthropic API
        """
        self.anthropic_adapter = anthropic_adapter or AnthropicAdapter()

    def run(self, instructions):
        """
        Run the agent loop with the given instructions.

        Args:
            instructions (str): The instructions to process

        Returns:
            dict: The result of the agent's work
        """
        tools = [
            {
                "name": "read_file",
                "description": "Read the content of a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file"}
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "write_file",
                "description": "Write content to a file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to the file"},
                        "content": {"type": "string", "description": "Content to write to the file"}
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "list_files",
                "description": "List all files in a directory recursively",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "directory": {"type": "string", "description": "Directory to list files from. Defaults to current directory."}
                    }
                }
            },
            {
                "name": "git_pull",
                "description": "Pull the latest changes from the remote repository",
                "input_schema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "git_push",
                "description": "Commit and push changes to the remote repository",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Commit message. Defaults to 'Update website - auggie'."}
                    }
                }
            }
        ]

        messages = [
            {"role": "user", "content": instructions}
        ]

        response = self.anthropic_adapter.generate_response(messages, tools)

        result = {"actions": []}

        for content_item in response.get("content", []):
            if content_item.get("type") == "tool_use":
                tool_name = content_item.get("name")
                tool_input = content_item.get("input")

                tool_result = execute_tool(tool_name, tool_input)

                result["actions"].append({
                    "tool": tool_name,
                    "input": tool_input,
                    "result": tool_result
                })

        return result