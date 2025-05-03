import unittest

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

    def test_generate(self):
        """Test generate method."""
        provider = FrankProvider()

        # Test the generate method
        prompt = """
        You are an agent that modifies code in the cynditaylor-com website.

        INSTRUCTION:
        Update the hero section on the homepage to include a new tagline
        """

        response = provider.generate(prompt)
        self.assertIsInstance(response, str)
        # Verify the response contains a tool call suggestion
        self.assertIn("list_files", response)

    def test_extract_instruction(self):
        """Test _extract_instruction method."""
        provider = FrankProvider()

        # Test with a prompt containing an INSTRUCTION section
        prompt = """
        You are an agent that modifies code in the cynditaylor-com website.

        INSTRUCTION:
        Update the hero section with a new tagline
        """
        instruction = provider._extract_instruction(prompt)
        self.assertEqual(instruction, "Update the hero section with a new tagline")

        # Test with a prompt without an INSTRUCTION section
        prompt = "Update the hero section with a new tagline"
        instruction = provider._extract_instruction(prompt)
        self.assertEqual(instruction, prompt)

    def test_generate_response(self):
        """Test _generate_response method."""
        provider = FrankProvider()

        # Test with a hero section instruction
        instruction = "Update the hero section with a new tagline"
        response = provider._generate_response(instruction)
        self.assertIn("I'll help you update the hero section", response)
        self.assertIn("list_files", response)

        # Test with a contact information instruction
        instruction = "Update the contact email address"
        response = provider._generate_response(instruction)
        self.assertIn("I'll help you update the contact information", response)
        self.assertIn("list_files", response)

    def test_get_name(self):
        """Test get_name method returns the expected name."""
        provider = FrankProvider(model="test_model")
        self.assertEqual(provider.get_name(), "Frank (test_model)")


if __name__ == "__main__":
    unittest.main()
