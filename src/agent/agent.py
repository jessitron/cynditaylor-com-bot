import os
import json
import re
from typing import Dict, Any, Optional, List

from src.llm.frank_llm.frank_provider import FrankProvider
from src.agent.tools.file_tools import ListFilesTool, ReadFileTool, WriteFileTool
from src.agent.tools.git_tools import CommitChangesTool, PushChangesTool

from opentelemetry import trace

from src.llm.provider import LLMProvider

tracer = trace.get_tracer("cynditaylor-com-bot")

# Define a simple class to represent tool definitions
class ToolDefinition:
    """Definition of a tool that the LLM can use."""

    def __init__(self, name: str, description: str, function=None):
        self.name = name
        self.description = description
        self.function = function

class WebsiteAgent:
    """
    Agent that can modify code in the cynditaylor-com website using an LLM with tools.
    """

    @tracer.start_as_current_span("Initialize agent")
    def __init__(self, llm_provider: LLMProvider, website_dir: str = "cynditaylor-com"):
        self.llm_provider = llm_provider
        self.website_dir = website_dir

        # Initialize tools
        self.tools = {}
        self._initialize_tools()

        # Ensure the website directory exists
        if not os.path.isdir(website_dir):
            raise ValueError(f"Website directory '{website_dir}' does not exist")

    def _initialize_tools(self):
        """Initialize tool instances."""
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

        # Do not create unused tool definitions for documentation purposes again, please

    @tracer.start_as_current_span("Execute tool")
    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
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
        span = trace.get_current_span()
        span.set_attribute("app.instruction", instruction)
        llm = self.llm_provider.start_conversation()

        try:
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
            max_iterations = 10
            conversation_history = []
            current_exchange_id = None

            # Add the initial prompt to the conversation history
            conversation_history.append({"role": "user", "content": prompt})

            for i in range(max_iterations):
                with tracer.start_as_current_span(f"Iteration {i+1}") as span:
                    # Generate a response using the LLM
                    span.set_attribute("app.llm.prompt", prompt)
                    span.set_attribute("app.iteration", i + 1)
                    response = llm.get_response_for_prompt(prompt)
                    span.set_attribute("app.llm.response", response)

                    # Add the response to the conversation history
                    conversation_history.append({"role": "assistant", "content": response})

                    # Get the current exchange ID from the conversation logger
                    if hasattr(llm, 'conversation_logger'):
                        current_exchange_id = f"exchange-{len(llm.conversation_logger.exchanges)}"

                    # Check if the response contains a tool call
                    tool_call = self._extract_tool_call(response)

                    if tool_call:
                        # Execute the tool
                        tool_name = tool_call["name"]
                        tool_args = tool_call["arguments"]

                        tool_result = self._execute_tool_by_name(tool_name, tool_args)

                        # Add the tool result to the conversation history
                        conversation_history.append({
                            "role": "tool",
                            "name": tool_name,
                            "content": tool_result
                        })

                        # Log the tool call in the conversation logger
                        if hasattr(llm, 'conversation_logger') and current_exchange_id:
                            llm.conversation_logger.log_tool_call(
                                current_exchange_id,
                                tool_name,
                                tool_args,
                                tool_result
                            )

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
        finally:
            # Always call finish_conversation to ensure proper cleanup
            llm.finish_conversation()

    def _execute_tool_by_name(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        return self._execute_tool(tool_name, tool_args)

    def _extract_tool_call(self, response: str) -> Optional[Dict[str, Any]]:
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
