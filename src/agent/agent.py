import os
import json
import re
from typing import Dict, Any, List, Union

from src.llm.frank_llm.frank_provider import FrankProvider
from src.agent.tools.file_tools import ListFilesTool, ReadFileTool, WriteFileTool
from src.agent.tools.git_tools import CommitChangesTool, PushChangesTool
from src.conversation.types import TextPrompt, ToolUseResults, FinalResponse, ToolUseRequests, ToolUse, ToolUseResult, Tool

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
        self.list_files_tool = ListFilesTool(self.website_dir)
        self.read_file_tool = ReadFileTool(self.website_dir)
        self.write_file_tool = WriteFileTool(self.website_dir)

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


        # For git operations, add the website_dir
        if tool_name in ["commit_changes", "push_changes"]:
            args["repo_dir"] = self.website_dir

        # Execute the tool
        tool = self.tools[tool_name]
        result = tool(**args)
        
        return result

    @tracer.start_as_current_span("Execute instruction")
    def execute_instruction(self, instruction: str) -> str:
        span = trace.get_current_span()
        span.set_attribute("app.instruction", instruction)
        
        # Define the system prompt separately
        system_prompt = """You are an agent that modifies code in the cynditaylor-com website.
You have access to tools that allow you to list files, read and write file contents, and commit changes to the repository."""
        
        llm = self.llm_provider.start_conversation(system_prompt)
        llm.record_metadata("instruction", instruction)

        try:
            # Start with a text prompt
            current_prompt: Union[TextPrompt, ToolUseResults] = TextPrompt(text=instruction)
            
            # Start the conversation loop
            max_iterations = 10

            for i in range(max_iterations):
                with tracer.start_as_current_span(f"Iteration {i+1}") as span:
                    span.set_attribute("app.iteration", i + 1)
                    
                    if isinstance(current_prompt, TextPrompt):
                        span.set_attribute("app.llm.prompt", current_prompt.text)
                    
                    # Call the LLM with the current prompt
                    response = llm.get_response_for_prompt(current_prompt)
                    
                    if isinstance(response, FinalResponse):
                        # Got a final response, return it
                        span.set_attribute("app.llm.response", response.text)
                        return response.text
                    elif isinstance(response, ToolUseRequests):
                        # Got tool use requests, execute them
                        span.set_attribute("app.llm.tool_requests_count", len(response.requests))
                        
                        # Execute all tool requests and collect results
                        tool_results = []
                        for tool_request in response.requests:
                            tool_name = tool_request.tool_name
                            tool_args = tool_request.parameters
                            
                            tool_result = self._execute_tool_by_name(tool_name, tool_args)
                            
                            tool_results.append(ToolUseResult(
                                id=tool_request.id,
                                result=tool_result
                            ))
                        
                        # Create the next prompt with tool results
                        current_prompt = ToolUseResults(results=tool_results)
                    else:
                        # Unexpected response type
                        return f"Unexpected response type: {type(response)}"

            # If we reach the maximum number of iterations, return a message
            return "Maximum iterations reached without a final response"
        finally:
            # Always call finish_conversation to ensure proper cleanup
            llm.finish_conversation()

    def _execute_tool_by_name(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        return self._execute_tool(tool_name, tool_args)

