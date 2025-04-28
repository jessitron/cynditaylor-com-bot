import os
import anthropic
from .anthropic_adapter import AnthropicAdapter

class RealAnthropicAdapter(AnthropicAdapter):
    """
    Real implementation of the Anthropic API adapter.
    Makes actual API calls to the Anthropic API.
    """

    def __init__(self, api_key=None, model="claude-3-opus-20240229"):
        """
        Initialize the Anthropic API adapter.

        Args:
            api_key (str, optional): The Anthropic API key. If not provided, it will be read from the ANTHROPIC_API_KEY environment variable.
            model (str, optional): The model to use. Defaults to "claude-3-opus-20240229".
        """
        super().__init__()
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("Anthropic API key is required. Set the ANTHROPIC_API_KEY environment variable or pass it to the constructor.")
        
        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate_response(self, messages, tools=None):
        """
        Generate a response from the Anthropic API.

        Args:
            messages (list): List of message objects to send to the API
            tools (list, optional): List of tools to make available to the model

        Returns:
            dict: The response from the API
        """
        try:
            if tools:
                response = self.client.messages.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    max_tokens=4096
                )
            else:
                response = self.client.messages.create(
                    model=self.model,
                    messages=messages,
                    max_tokens=4096
                )
            
            # Convert the response to the expected format
            return {
                "content": response.content
            }
        except Exception as e:
            # Log the error and return a simple error response
            print(f"Error calling Anthropic API: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error calling Anthropic API: {e}"
                    }
                ]
            }
