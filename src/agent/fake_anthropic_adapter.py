from .anthropic_adapter import AnthropicAdapter

class FakeAnthropicAdapter(AnthropicAdapter):
    """
    Fake implementation of the Anthropic API adapter for testing.
    Instead of making real API calls, it returns predefined responses based on input.
    """

    def __init__(self):
        super().__init__()
        self.response_map = {}

    def add_response(self, instruction_pattern, response):
        """
        Add a predefined response for a specific instruction pattern.

        Args:
            instruction_pattern (str): A substring to match in the user's instructions
            response (dict): The response to return when the pattern is matched
        """
        self.response_map[instruction_pattern] = response

    def generate_response(self, messages, tools=None):
        """
        Generate a fake response based on predefined patterns.

        Args:
            messages (list): List of message objects
            tools (list, optional): List of tools to make available to the model

        Returns:
            dict: A predefined response that matches the input
        """
        # Extract the user's instructions from the messages
        user_instructions = ""
        for message in messages:
            if message.get("role") == "user":
                user_instructions = message.get("content", "")
                break

        # Find a matching response based on the instructions
        for pattern, response in self.response_map.items():
            if pattern in user_instructions:
                return response

        # Default response if no pattern matches
        return {
            "content": [
                {
                    "type": "text",
                    "text": "I don't know how to respond to that instruction."
                }
            ]
        }
