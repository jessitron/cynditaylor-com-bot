import unittest
from unittest.mock import MagicMock, patch

from src.llm.frank_provider import FrankProvider


class TestFrankProvider(unittest.TestCase):

    @patch('src.llm.frank_provider.ConversationReader')
    def test_init(self, mock_reader_class):
        provider = FrankProvider(model="custom_model")
        self.assertEqual(provider.model, "custom_model")
        mock_reader_class.assert_called_once()

    @patch('src.llm.frank_provider.ConversationReader')
    def test_init_default_model(self, mock_reader_class):
        provider = FrankProvider()
        self.assertEqual(provider.model, "default")
        mock_reader_class.assert_called_once()

    @patch('src.llm.frank_provider.ConversationReader')
    def test_generate(self, mock_reader_class):
        # Setup mock reader
        mock_reader = MagicMock()
        mock_reader.get_response_for_prompt.return_value = "Replayed response from conversation history"
        mock_reader_class.return_value = mock_reader

        # Create provider
        provider = FrankProvider()

        # Test the generate method
        prompt = "Test prompt"
        response = provider.generate(prompt)

        # Verify the response is the one from the conversation history
        self.assertEqual(response, "Replayed response from conversation history")
        mock_reader.get_response_for_prompt.assert_called_once_with(prompt)

    @patch('src.llm.frank_provider.ConversationReader')
    def test_generate_no_match(self, mock_reader_class):
        # Setup mock reader
        mock_reader = MagicMock()
        mock_reader.get_response_for_prompt.return_value = None
        mock_reader_class.return_value = mock_reader

        # Create provider
        provider = FrankProvider()

        # Test the generate method
        prompt = "Test prompt"

        # When no matching prompt is found, the provider should raise an error
        with self.assertRaises(ValueError):
            provider.generate(prompt)

    @patch('src.llm.frank_provider.ConversationReader')
    def test_generate_error(self, mock_reader_class):
        # Setup mock reader
        mock_reader = MagicMock()
        mock_reader.get_response_for_prompt.side_effect = ValueError("Test error")
        mock_reader_class.return_value = mock_reader

        # Create provider
        provider = FrankProvider()

        # Test the generate method
        prompt = "Test prompt"

        # When an error occurs, the provider should raise it
        with self.assertRaises(ValueError):
            provider.generate(prompt)

    def test_get_name(self):
        with patch('src.llm.frank_provider.ConversationReader'):
            provider = FrankProvider(model="test_model")
            self.assertEqual(provider.get_name(), "Frank (test_model)")


if __name__ == "__main__":
    unittest.main()
