import unittest
import os
from unittest.mock import patch

from llm.frank_provider import FrankProvider


class TestFrankProvider(unittest.TestCase):
    
    @patch.dict(os.environ, {"FRANK_API_KEY": "test_api_key"})
    def test_init_with_env_var(self):
        """Test initialization with API key from environment variable."""
        provider = FrankProvider()
        self.assertEqual(provider.api_key, "test_api_key")
        self.assertEqual(provider.model, "default")
    
    def test_init_with_direct_api_key(self):
        """Test initialization with directly provided API key."""
        provider = FrankProvider(api_key="direct_api_key", model="custom_model")
        self.assertEqual(provider.api_key, "direct_api_key")
        self.assertEqual(provider.model, "custom_model")
    
    @patch.dict(os.environ, {}, clear=True)
    def test_init_without_api_key(self):
        """Test initialization without API key raises ValueError."""
        with self.assertRaises(ValueError):
            FrankProvider()
    
    def test_generate(self):
        """Test generate method returns a string."""
        provider = FrankProvider(api_key="test_api_key")
        response = provider.generate("Test prompt")
        self.assertIsInstance(response, str)
        self.assertTrue("placeholder response" in response)
    
    def test_get_name(self):
        """Test get_name method returns the expected name."""
        provider = FrankProvider(api_key="test_api_key", model="test_model")
        self.assertEqual(provider.get_name(), "Frank (test_model)")


if __name__ == "__main__":
    unittest.main()
