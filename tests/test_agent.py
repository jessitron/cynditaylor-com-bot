import unittest
import os
from unittest.mock import MagicMock

from src.llm.frank_provider import FrankProvider
from src.agent.agent import WebsiteAgent


class TestWebsiteAgent(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory structure for testing
        os.makedirs("test_website", exist_ok=True)
        with open("test_website/index.html", "w") as f:
            f.write('<html><body><div class="hero-content"><h2>Title</h2><p>Old tagline</p></div></body></html>')

    def tearDown(self):
        # Clean up the temporary directory
        if os.path.exists("test_website/index.html"):
            os.remove("test_website/index.html")
        if os.path.exists("test_website"):
            os.rmdir("test_website")

    def test_init(self):
        """Test initialization of WebsiteAgent."""
        llm = FrankProvider()
        agent = WebsiteAgent(llm, website_dir="test_website")
        self.assertEqual(agent.website_dir, "test_website")
        self.assertEqual(agent.llm, llm)

    def test_init_with_nonexistent_dir(self):
        """Test initialization with non-existent directory raises ValueError."""
        llm = FrankProvider()
        with self.assertRaises(ValueError):
            WebsiteAgent(llm, website_dir="nonexistent_dir")

    def test_execute_tool(self):
        """Test the _execute_tool method."""
        llm = FrankProvider()
        agent = WebsiteAgent(llm, website_dir="test_website")

        # Test with list_files tool
        result = agent._execute_tool("list_files", {"directory": "."})
        self.assertTrue(result["success"])
        # The file path will include the website_dir prefix
        self.assertIn("test_website/./index.html", result["files"])

    def test_execute_instruction_with_tool_call(self):
        """Test executing an instruction that results in a tool call."""
        # Create a custom FrankProvider that returns a response with a tool call
        class TestFrankProvider(FrankProvider):
            def generate(self, *args, **kwargs):
                return """I'll help you with that. First, I need to see what files are available.

```tool
{
  "name": "list_files",
  "arguments": {
    "directory": "."
  }
}
```"""

        # Create a mock for the _execute_tool method
        original_execute_tool = WebsiteAgent._execute_tool

        try:
            # Replace _execute_tool with a mock that returns a predefined result
            WebsiteAgent._execute_tool = MagicMock(return_value={
                "success": True,
                "files": ["index.html", "styles.css"]
            })

            llm = TestFrankProvider()
            agent = WebsiteAgent(llm, website_dir="test_website")

            # Execute the instruction
            result = agent.execute_instruction("Update the website")

            # Verify the result contains the expected information
            self.assertIn("list_files", result)

        finally:
            # Restore the original method
            WebsiteAgent._execute_tool = original_execute_tool

    def test_execute_instruction_without_tool_call(self):
        """Test executing an instruction that doesn't result in a tool call."""
        # Create a custom FrankProvider that returns a response without a tool call
        class TestFrankProvider(FrankProvider):
            def generate(self, *args, **kwargs):
                return "I've analyzed the instruction and completed the task."

        llm = TestFrankProvider()
        agent = WebsiteAgent(llm, website_dir="test_website")

        # Execute the instruction
        result = agent.execute_instruction("Update the website")

        # Verify the result is the expected response
        self.assertEqual(result, "I've analyzed the instruction and completed the task.")

    def test_extract_tool_call(self):
        """Test extracting a tool call from a response."""
        llm = FrankProvider()
        agent = WebsiteAgent(llm, website_dir="test_website")

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

        tool_call = agent._extract_tool_call(response)
        self.assertIsNotNone(tool_call)
        self.assertEqual(tool_call["name"], "list_files")
        self.assertEqual(tool_call["arguments"], {"directory": "."})

        # Test with no tool call
        response = "I'll help you with that. Let me think about it."
        tool_call = agent._extract_tool_call(response)
        self.assertIsNone(tool_call)


if __name__ == "__main__":
    unittest.main()
