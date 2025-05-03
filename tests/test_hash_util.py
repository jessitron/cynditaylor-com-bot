import unittest
from src.conversation.hash_util import calculate_hash, normalize_prompt, hash_prompt


class TestHashUtil(unittest.TestCase):
    """Test the hash utility functions."""

    def test_calculate_hash(self):
        """Test calculate_hash function."""
        text = "Test prompt"
        hash_value = calculate_hash(text)
        self.assertEqual(len(hash_value), 64)  # SHA-256 hash is 64 characters long
        self.assertEqual(hash_value, "1439da2cb34b7c5b712b0cda7d879591a19fefcfedfd1c8bd7aa72364ac9fae7")

    def test_normalize_prompt_string(self):
        """Test normalize_prompt function with a string."""
        prompt = "  Test prompt  "
        normalized = normalize_prompt(prompt)
        self.assertEqual(normalized, "Test prompt")

    def test_normalize_prompt_dict(self):
        """Test normalize_prompt function with a dictionary."""
        prompt = {"text": "Test prompt", "metadata": {"temperature": 0.7}}
        normalized = normalize_prompt(prompt)
        self.assertEqual(normalized, str(prompt).strip())

    def test_normalize_prompt_invalid(self):
        """Test normalize_prompt function with an invalid type."""
        with self.assertRaises(ValueError):
            normalize_prompt(123)

    def test_hash_prompt_string(self):
        """Test hash_prompt function with a string."""
        prompt = "Test prompt"
        hash_value = hash_prompt(prompt)
        self.assertEqual(hash_value, calculate_hash(prompt))

    def test_hash_prompt_dict(self):
        """Test hash_prompt function with a dictionary."""
        prompt = {"text": "Test prompt", "metadata": {"temperature": 0.7}}
        hash_value = hash_prompt(prompt)
        self.assertEqual(hash_value, calculate_hash(str(prompt).strip()))


if __name__ == "__main__":
    unittest.main()
