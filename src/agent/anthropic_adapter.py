class AnthropicAdapter:
    """
    Adapter for the Anthropic API.
    This allows us to swap between real API calls and mock responses for testing.
    """

    def __init__(self):
        pass

    def generate_response(self, messages, tools=None):
        """
        Generate a response from the Anthropic API.

        Args:
            messages (list): List of message objects to send to the API
            tools (list, optional): List of tools to make available to the model

        Returns:
            dict: The response from the API
        """
        raise NotImplementedError("This method should be implemented by concrete adapters")