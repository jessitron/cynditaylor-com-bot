import unittest
import json

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

    def test_generate_analysis_prompt(self):
        """Test generate method with an analysis prompt."""
        provider = FrankProvider()
        prompt = """
        You are an agent that modifies code in the cynditaylor-com website.
        Please analyze the following instruction and determine what changes need to be made:

        INSTRUCTION:
        Update the hero section on the homepage to include a new tagline

        Respond with a JSON object containing:
        1. "files_to_modify": List of files that need to be modified
        2. "actions": List of specific actions to take for each file
        3. "reasoning": Your reasoning for these changes
        """

        response = provider.generate(prompt)
        self.assertIsInstance(response, str)

        # Verify the response is valid JSON
        result = json.loads(response)
        self.assertIn("files_to_modify", result)
        self.assertIn("actions", result)
        self.assertIn("reasoning", result)
        self.assertIn("index.html", result["files_to_modify"])

    def test_generate_modification_prompt(self):
        """Test generate method with a modification prompt."""
        provider = FrankProvider()
        prompt = """
        You are an agent that modifies code in the cynditaylor-com website.
        You need to modify the following file according to this action:

        FILE: index.html
        ACTION: Update the hero section with the new tagline

        Current content of the file:
        ```
        <html><body><div class="hero-content"><h2>Title</h2><p>Old tagline</p></div></body></html>
        ```

        Please provide the complete new content for the file.
        Only output the new content, nothing else.
        """

        response = provider.generate(prompt)
        self.assertIsInstance(response, str)
        self.assertIn("Bringing your memories to life through art", response)

    def test_generate_summary_prompt(self):
        """Test generate method with a summary prompt."""
        provider = FrankProvider()
        prompt = """
        You are an agent that modifies code in the cynditaylor-com website.
        You have executed an instruction and need to provide a summary of what was done.

        INSTRUCTION:
        Update the hero section

        EXECUTION RESULT:
        {"instruction": "Update the hero section", "results": [{"file": "index.html", "success": true}], "llm_provider": "Frank (default)"}

        Please provide a concise, human-readable summary of what was done.
        """

        response = provider.generate(prompt)
        self.assertIsInstance(response, str)
        self.assertIn("successfully executed", response.lower())
        self.assertIn("index.html", response)

    def test_get_name(self):
        """Test get_name method returns the expected name."""
        provider = FrankProvider(model="test_model")
        self.assertEqual(provider.get_name(), "Frank (test_model)")


if __name__ == "__main__":
    unittest.main()
