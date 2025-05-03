import unittest
import json
import re

from src.llm.frank_provider import FrankProvider


class TestFrankProvider(unittest.TestCase):

    def test_init(self):
        """Test initialization of FrankProvider."""
        provider = FrankProvider(model="custom_model")
        self.assertEqual(provider.model, "custom_model")

    def test_init_default_model(self):
        """Test initialization with default model."""
        provider = FrankProvider()
        self.assertEqual(provider.model, "default")

    def test_generate_with_tools(self):
        """Test generate method with tools."""
        provider = FrankProvider()

        # Register a test tool
        def test_tool(arg1: str) -> dict:
            return {"success": True, "result": f"Processed {arg1}"}

        from src.llm.frank_provider import ToolDefinition
        provider.register_tool(ToolDefinition(
            name="test_tool",
            description="A test tool",
            function=test_tool
        ))

        # Test the generate method
        prompt = """
        You are an agent that modifies code in the cynditaylor-com website.

        INSTRUCTION:
        Update the hero section on the homepage to include a new tagline
        """

        response = provider.generate(prompt)
        self.assertIsInstance(response, str)

    def test_handle_initial_instruction(self):
        """Test _handle_initial_instruction method."""
        provider = FrankProvider()

        # Test with a hero section instruction
        instruction = "Update the hero section with a new tagline"
        response = provider._handle_initial_instruction(instruction)
        self.assertIn("I'll help you update the hero section", response)
        self.assertIn("list_files", response)

        # Test with a contact information instruction
        instruction = "Update the contact email address"
        response = provider._handle_initial_instruction(instruction)
        self.assertIn("I'll help you update the contact information", response)
        self.assertIn("list_files", response)

    def test_handle_tool_results(self):
        """Test _handle_tool_results method."""
        provider = FrankProvider()

        # Test handling list_files results
        tool_result = {
            "name": "list_files",
            "content": json.dumps({
                "success": True,
                "files": ["index.html", "contact.html", "css/styles.css"]
            })
        }

        # Add a message to the conversation history
        provider.conversation_history = [
            {"role": "user", "content": "Update the hero section with a new tagline"}
        ]

        response = provider._handle_tool_results(tool_result, "Update the hero section with a new tagline")
        self.assertIn("I found the index.html file", response)
        self.assertIn("read_file", response)

        # Test handling read_file results for hero section
        tool_result = {
            "name": "read_file",
            "content": json.dumps({
                "success": True,
                "content": '<html><body><div class="hero-content"><h2>Title</h2><p>Old tagline</p></div></body></html>'
            })
        }

        # Add a message to the conversation history
        provider.conversation_history = [
            {"role": "user", "content": "Update the hero section with a new tagline"},
            {"role": "assistant", "content": 'I need to read the file\n```tool\n{"name":"read_file","arguments":{"file_path":"index.html"}}\n```'}
        ]

        response = provider._handle_tool_results(tool_result, "Update the hero section with a new tagline")
        self.assertIn("I found the hero section", response)
        self.assertIn("write_file", response)

    def test_get_name(self):
        """Test get_name method returns the expected name."""
        provider = FrankProvider(model="test_model")
        self.assertEqual(provider.get_name(), "Frank (test_model)")

    def test_register_tool(self):
        """Test registering a tool with the provider."""
        provider = FrankProvider()

        # Define a simple tool
        def dummy_tool(arg1: str) -> dict:
            return {"result": f"Processed {arg1}"}

        # Register the tool
        from src.llm.frank_provider import ToolDefinition
        provider.register_tool(ToolDefinition(
            name="dummy_tool",
            description="A dummy tool for testing",
            function=dummy_tool
        ))

        # Verify the tool was registered
        self.assertIn("dummy_tool", provider.tools)
        self.assertEqual(provider.tools["dummy_tool"].name, "dummy_tool")
        self.assertEqual(provider.tools["dummy_tool"].description, "A dummy tool for testing")

    def test_extract_tool_call(self):
        """Test extracting a tool call from a response."""
        provider = FrankProvider()

        # Test with a valid tool call
        response = """I'll help you with that. First, I need to see what files are available.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""

        tool_call = provider._extract_tool_call(response)
        self.assertIsNotNone(tool_call)
        self.assertEqual(tool_call["name"], "list_files")
        self.assertEqual(tool_call["arguments"], {"directory": "."})

        # Test with no tool call
        response = "I'll help you with that. Let me think about it."
        tool_call = provider._extract_tool_call(response)
        self.assertIsNone(tool_call)


if __name__ == "__main__":
    unittest.main()
