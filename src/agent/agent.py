"""
Main agent module for the Cyndi Taylor Website Bot.

This module implements the core agent functionality, including the main loop
for processing instructions, making LLM calls, and executing tools.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Callable

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WebsiteAgent:
    """
    Agent that processes instructions to update the Cyndi Taylor website.
    
    This agent handles the main loop of:
    1. Receiving instructions
    2. Making LLM calls to determine actions
    3. Executing tools based on LLM decisions
    4. Repeating until the task is complete
    """
    
    def __init__(self, llm_client, tools: Dict[str, Callable]):
        """
        Initialize the agent with an LLM client and available tools.
        
        Args:
            llm_client: Client for making calls to the LLM (e.g., Anthropic)
            tools: Dictionary mapping tool names to tool functions
        """
        self.llm_client = llm_client
        self.tools = tools
        self.conversation_history = []
        
    def add_to_history(self, role: str, content: str):
        """
        Add a message to the conversation history.
        
        Args:
            role: The role of the message sender (e.g., "user", "assistant")
            content: The content of the message
        """
        self.conversation_history.append({"role": role, "content": content})
        
    def run_agent_loop(self, initial_instructions: str) -> List[Dict[str, Any]]:
        """
        Run the main agent loop to process instructions and execute tools.
        
        Args:
            initial_instructions: The initial instructions to process
            
        Returns:
            List of actions taken by the agent
        """
        # Add initial instructions to conversation history
        self.add_to_history("user", initial_instructions)
        
        # List to track actions taken
        actions_taken = []
        
        # Main agent loop
        max_iterations = 10  # Safety limit to prevent infinite loops
        for i in range(max_iterations):
            logger.info(f"Agent loop iteration {i+1}")
            
            # Make LLM call to get next action
            response = self._make_llm_call()
            
            # Add LLM response to history
            self.add_to_history("assistant", response)
            
            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(response)
            
            if not tool_calls:
                logger.info("No tool calls found, agent loop complete")
                break
                
            # Execute tool calls
            for tool_call in tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("arguments", {})
                
                if tool_name in self.tools:
                    logger.info(f"Executing tool: {tool_name}")
                    try:
                        result = self.tools[tool_name](**tool_args)
                        
                        # Record the action
                        action = {
                            "tool": tool_name,
                            "arguments": tool_args,
                            "result": result
                        }
                        actions_taken.append(action)
                        
                        # Add tool result to conversation history
                        tool_result_msg = f"Tool {tool_name} executed with result: {json.dumps(result)}"
                        self.add_to_history("user", tool_result_msg)
                        
                    except Exception as e:
                        error_msg = f"Error executing tool {tool_name}: {str(e)}"
                        logger.error(error_msg)
                        self.add_to_history("user", error_msg)
                else:
                    error_msg = f"Unknown tool: {tool_name}"
                    logger.error(error_msg)
                    self.add_to_history("user", error_msg)
        
        return actions_taken
    
    def _make_llm_call(self) -> str:
        """
        Make a call to the LLM with the current conversation history.
        
        Returns:
            The LLM's response as a string
        """
        # This is a placeholder for the actual LLM call
        # In a real implementation, this would use the llm_client to make an API call
        
        try:
            # Convert conversation history to the format expected by the LLM client
            messages = self.conversation_history
            
            # Make the LLM call
            response = self.llm_client.messages.create(
                messages=messages,
                max_tokens=4096
            )
            
            # Extract and return the content from the response
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error making LLM call: {str(e)}")
            return f"Error: {str(e)}"
    
    def _parse_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse tool calls from the LLM response.
        
        Args:
            response: The LLM response text
            
        Returns:
            List of tool calls, each with a name and arguments
        """
        # This is a simplified parser that looks for tool calls in a specific format
        # In a real implementation, this would use a more robust parser
        
        tool_calls = []
        
        # Simple parsing logic - look for tool calls in the format:
        # <tool>tool_name</tool>
        # <arguments>
        # {
        #   "arg1": "value1",
        #   "arg2": "value2"
        # }
        # </arguments>
        
        # Split the response by tool tags
        parts = response.split("<tool>")
        
        for part in parts[1:]:  # Skip the first part (before any tool tag)
            try:
                # Extract tool name
                tool_name_end = part.find("</tool>")
                if tool_name_end == -1:
                    continue
                    
                tool_name = part[:tool_name_end].strip()
                
                # Extract arguments
                args_start = part.find("<arguments>")
                args_end = part.find("</arguments>")
                
                if args_start == -1 or args_end == -1:
                    continue
                    
                args_json = part[args_start + len("<arguments>"):args_end].strip()
                arguments = json.loads(args_json)
                
                tool_calls.append({
                    "name": tool_name,
                    "arguments": arguments
                })
                
            except Exception as e:
                logger.error(f"Error parsing tool call: {str(e)}")
        
        return tool_calls
