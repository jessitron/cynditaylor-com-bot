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
    if tool_name == "read_file":
        return f"Content of {tool_input['path']}"

    return f"Executed {tool_name} with {tool_input}"

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