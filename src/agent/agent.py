import os
from typing import Dict, Any, Optional

from src.llm.frank_provider import FrankProvider, ToolDefinition
from src.agent.tools.tool import Tool
from src.agent.tools.file_tools import ListFilesTool, ReadFileTool, WriteFileTool
from src.agent.tools.git_tools import CommitChangesTool, PushChangesTool

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

        # Initialize tools
        self.tools = {}
        self._initialize_tools()

        # Ensure the website directory exists
        if not os.path.isdir(website_dir):
            raise ValueError(f"Website directory '{website_dir}' does not exist")

        # Register tools with the LLM provider
        self._register_tools()

    def _initialize_tools(self):
        """Initialize tool instances."""
        with tracer.start_as_current_span("Initialize tools"):
            # File tools
            self.list_files_tool = ListFilesTool()
            self.read_file_tool = ReadFileTool()
            self.write_file_tool = WriteFileTool()

            # Git tools
            self.commit_changes_tool = CommitChangesTool()
            self.push_changes_tool = PushChangesTool()

            # Add tools to the tools dictionary
            for tool in [
                self.list_files_tool,
                self.read_file_tool,
                self.write_file_tool,
                self.commit_changes_tool,
                self.push_changes_tool
            ]:
                self.tools[tool.name] = tool

    def _register_tools(self):
        """Register tools with the LLM provider."""
        with tracer.start_as_current_span("Register tools with LLM"):
            # File tools
            self.llm.register_tool(ToolDefinition(
                name="list_files",
                description="List files in a directory",
                function=lambda **kwargs: self._execute_tool("list_files", kwargs)
            ))

            self.llm.register_tool(ToolDefinition(
                name="read_file",
                description="Read the contents of a file",
                function=lambda **kwargs: self._execute_tool("read_file", kwargs)
            ))

            self.llm.register_tool(ToolDefinition(
                name="write_file",
                description="Write content to a file",
                function=lambda **kwargs: self._execute_tool("write_file", kwargs)
            ))

            # Git tools
            self.llm.register_tool(ToolDefinition(
                name="commit_changes",
                description="Commit changes to the repository",
                function=lambda **kwargs: self._execute_tool("commit_changes", kwargs)
            ))

            self.llm.register_tool(ToolDefinition(
                name="push_changes",
                description="Push changes to the remote repository",
                function=lambda **kwargs: self._execute_tool("push_changes", kwargs)
            ))

    @tracer.start_as_current_span("Execute tool")
    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            args: Arguments for the tool

        Returns:
            Result of the tool execution
        """
        if tool_name not in self.tools:
            return {
                "success": False,
                "message": f"Tool '{tool_name}' not found"
            }

        # For file operations, adjust paths to be relative to website_dir
        if tool_name in ["list_files", "read_file", "write_file"]:
            if "directory" in args:
                args["directory"] = os.path.join(self.website_dir, args["directory"])
            if "file_path" in args:
                args["file_path"] = os.path.join(self.website_dir, args["file_path"])

        # For git operations, add the website_dir
        if tool_name in ["commit_changes", "push_changes"]:
            args["repo_dir"] = self.website_dir

        # Execute the tool
        tool = self.tools[tool_name]
        return tool(**args)



    @tracer.start_as_current_span("Execute instruction")
    def execute_instruction(self, instruction: str) -> str:
        """
        Execute an instruction using the LLM with tools.

        Args:
            instruction: The instruction to execute

        Returns:
            The final response from the LLM
        """
        with tracer.start_as_current_span("Create prompt"):
            # Create the initial prompt
            prompt = f"""
            You are an agent that modifies code in the cynditaylor-com website.
            You have access to tools that allow you to list files, read and write file contents, and commit changes to the repository.

            INSTRUCTION:
            {instruction}

            Please analyze the instruction and use the available tools to make the necessary changes.
            When you're done, provide a summary of what you did.
            """

        # Start the conversation loop
        with tracer.start_as_current_span("LLM conversation loop"):
            max_iterations = 10
            conversation_history = []

            # Add the initial prompt to the conversation history
            conversation_history.append({"role": "user", "content": prompt})

            for i in range(max_iterations):
                with tracer.start_as_current_span(f"Iteration {i+1}"):
                    # Generate a response using the LLM with tool executor
                    response = self.llm.generate(
                        prompt,
                        tool_executor=self._execute_tool_by_name
                    )

                    # Check if the response contains a tool call
                    tool_call = self._extract_tool_call(response)

                    if tool_call:
                        # Execute the tool
                        with tracer.start_as_current_span(f"Execute tool: {tool_call['name']}"):
                            tool_name = tool_call["name"]
                            tool_args = tool_call["arguments"]

                            tool_result = self._execute_tool_by_name(tool_name, tool_args)

                            # Add the tool result to the conversation history
                            conversation_history.append({
                                "role": "tool",
                                "name": tool_name,
                                "content": tool_result
                            })

                            # Update the prompt with the tool result
                            prompt = self._update_prompt_with_tool_result(
                                prompt,
                                tool_name,
                                tool_args,
                                tool_result
                            )
                    else:
                        # No tool call, return the final response
                        return response

            # If we reach the maximum number of iterations, return the last response
            return response

    def _execute_tool_by_name(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with the given arguments.
        This method is used as a callback for the LLM provider.

        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments for the tool

        Returns:
            Result of the tool execution
        """
        return self._execute_tool(tool_name, tool_args)

    def _extract_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Extract a tool call from the response.

        Args:
            response: The response to extract the tool call from

        Returns:
            A dictionary containing the tool name and arguments, or None if no tool call is found
        """
        import re
        import json

        tool_match = re.search(r'```tool\s*(.*?)```', response, re.DOTALL)
        if not tool_match:
            return None

        try:
            tool_json = json.loads(tool_match.group(1))
            return {
                "name": tool_json.get("name", ""),
                "arguments": tool_json.get("arguments", {})
            }
        except json.JSONDecodeError:
            return None

    def _update_prompt_with_tool_result(self, prompt: str, tool_name: str, tool_args: Dict[str, Any], tool_result: Dict[str, Any]) -> str:
        """
        Update the prompt with the tool result.

        Args:
            prompt: The current prompt
            tool_name: Name of the tool that was executed
            tool_args: Arguments that were passed to the tool
            tool_result: Result of the tool execution

        Returns:
            Updated prompt with the tool result
        """
        import json

        # Add the tool call and result to the prompt
        tool_call_str = json.dumps({"name": tool_name, "arguments": tool_args}, indent=2)
        tool_result_str = json.dumps(tool_result, indent=2)

        updated_prompt = f"""{prompt}

Tool call:
```tool
{tool_call_str}
```

Tool result:
```
{tool_result_str}
```

Please continue with the instruction based on this result.
"""

        return updated_prompt
