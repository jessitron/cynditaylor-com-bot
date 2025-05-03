import os
from typing import Dict, Any, Optional

from src.llm.frank_provider import FrankProvider, ToolDefinition
from src.agent.tools.file_tools import FileTools
from src.agent.tools.git_tools import GitTools

from opentelemetry import trace

tracer = trace.get_tracer("cynditaylor-com-bot")

class WebsiteAgent:
    """
    Agent that can modify code in the cynditaylor-com website using an LLM with tools.
    """

    @tracer.start_as_current_span("Initialize agent")
    def __init__(self, llm_provider: FrankProvider, website_dir: str = "cynditaylor-com"):
        """
        Initialize the website agent.

        Args:
            llm_provider: The LLM provider to use for generating responses
            website_dir: Directory containing the website code
        """
        self.llm = llm_provider
        self.website_dir = website_dir
        self.file_tools = FileTools()
        self.git_tools = GitTools()

        # Ensure the website directory exists
        if not os.path.isdir(website_dir):
            raise ValueError(f"Website directory '{website_dir}' does not exist")

        # Register tools with the LLM provider
        self._register_tools()

    def _register_tools(self):
        """Register tools with the LLM provider."""
        # File tools
        self.llm.register_tool(ToolDefinition(
            name="list_files",
            description="List files in a directory",
            function=self._list_files
        ))

        self.llm.register_tool(ToolDefinition(
            name="read_file",
            description="Read the contents of a file",
            function=self._read_file
        ))

        self.llm.register_tool(ToolDefinition(
            name="write_file",
            description="Write content to a file",
            function=self._write_file
        ))

        # Git tools
        self.llm.register_tool(ToolDefinition(
            name="commit_changes",
            description="Commit changes to the repository",
            function=self._commit_changes
        ))

        # TODO: remove this tool
        self.llm.register_tool(ToolDefinition(
            name="push_changes",
            description="Push changes to the remote repository",
            function=self._push_changes
        ))

    def _list_files(self, directory: str = ".", pattern: Optional[str] = None) -> Dict[str, Any]:
        """
        List files in a directory.

        Args:
            directory: Directory to list files from (relative to website_dir)
            pattern: Optional glob pattern to filter files

        Returns:
            Dictionary with the list of files
        """
        full_dir = os.path.join(self.website_dir, directory)
        try:
            files = self.file_tools.list_files(full_dir, pattern)
            # Convert absolute paths to relative paths
            relative_files = [os.path.relpath(f, self.website_dir) for f in files]
            return {
                "success": True,
                "files": relative_files
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    # TODO: move all tools to their own classes in their own files in a tools module
    def _read_file(self, file_path: str) -> Dict[str, Any]:
        """
        Read the contents of a file.

        Args:
            file_path: Path to the file to read (relative to website_dir)

        Returns:
            Dictionary with the file content
        """
        full_path = os.path.join(self.website_dir, file_path)
        try:
            if not self.file_tools.file_exists(full_path):
                return {
                    "success": False,
                    "message": f"File does not exist: {file_path}"
                }

            content = self.file_tools.read_file(full_path)
            return {
                "success": True,
                "content": content
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    def _write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """
        Write content to a file.

        Args:
            file_path: Path to the file to write (relative to website_dir)
            content: Content to write to the file

        Returns:
            Dictionary with the result of the operation
        """
        full_path = os.path.join(self.website_dir, file_path)
        try:
            success = self.file_tools.write_file(full_path, content)
            return {
                "success": success,
                "message": f"File {'written' if success else 'failed to write'}: {file_path}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    def _commit_changes(self, message: str) -> Dict[str, Any]:
        """
        Commit changes to the repository.

        Args:
            message: Commit message

        Returns:
            Dictionary with the result of the operation
        """
        try:
            success, result_message = self.git_tools.commit_changes(self.website_dir, message)
            return {
                "success": success,
                "message": result_message
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    def _push_changes(self, branch: str = "main") -> Dict[str, Any]:
        """
        Push changes to the remote repository.

        Args:
            branch: Branch to push to

        Returns:
            Dictionary with the result of the operation
        """
        try:
            success, result_message = self.git_tools.push_changes(self.website_dir, branch)
            return {
                "success": success,
                "message": result_message
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }

    @tracer.start_as_current_span("Execute instruction")
    def execute_instruction(self, instruction: str) -> str:
        """
        Execute an instruction using the LLM with tools.

        Args:
            instruction: The instruction to execute

        Returns:
            The final response from the LLM
        """
        # Create the initial prompt
        prompt = f"""
        You are an agent that modifies code in the cynditaylor-com website.
        You have access to tools that allow you to list files, read and write file contents, and commit changes to the repository.

        INSTRUCTION:
        {instruction}

        Please analyze the instruction and use the available tools to make the necessary changes.
        When you're done, provide a summary of what you did.
        """

        # Generate a response using the LLM with tools
        response = self.llm.generate(prompt)

        return response
