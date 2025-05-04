import unittest
from unittest.mock import MagicMock

from src.llm.frank_provider import FrankProvider


class TestFrankProvider(unittest.TestCase):

    def test_init(self):
        """Test initialization of FrankProvider."""
        provider = FrankProvider(model="custom_model", replay_mode=False)
        self.assertEqual(provider.model, "custom_model")
        self.assertFalse(provider.replay_mode)

    def test_init_default_model(self):
        """Test initialization with default model."""
        provider = FrankProvider(replay_mode=False)
        self.assertEqual(provider.model, "default")
        self.assertFalse(provider.replay_mode)

    def test_generate_normal_mode(self):
        """Test generate method in normal mode."""
        provider = FrankProvider(replay_mode=False)

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

    def test_generate_replay_mode(self):
        """Test generate method in replay mode."""
        # Create a provider with a mock conversation reader
        provider = FrankProvider(replay_mode=True)

        # Replace the conversation reader with a mock
        mock_reader = MagicMock()
        mock_reader.get_response_for_prompt.return_value = "Replayed response from conversation history"
        provider.conversation_reader = mock_reader

        # Test the generate method
        prompt = "Test prompt"
        response = provider.generate(prompt)

        # Verify the response is the one from the conversation history
        self.assertEqual(response, "Replayed response from conversation history")
        mock_reader.get_response_for_prompt.assert_called_once_with(prompt)

    def test_generate_replay_mode_no_match(self):
        """Test generate method in replay mode when no matching prompt is found."""
        # Create a provider with a mock conversation reader
        provider = FrankProvider(replay_mode=True)

        # Replace the conversation reader with a mock
        mock_reader = MagicMock()
        mock_reader.get_response_for_prompt.return_value = None
        provider.conversation_reader = mock_reader

        # Test the generate method
        prompt = "Test prompt"

        # When no matching prompt is found, the provider should fall back to normal mode
        response = provider.generate(prompt)

        # Verify that replay mode was disabled
        self.assertFalse(provider.replay_mode)

        # Verify that a response was generated using the normal mode
        self.assertIsNotNone(response)
        self.assertIn("I'll help you with that", response)

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
