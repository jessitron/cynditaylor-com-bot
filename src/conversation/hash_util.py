import hashlib
from typing import Dict, Any, Union


def calculate_hash(text: str) -> str:
    """
    Calculate a SHA-256 hash of the given text.
    
    Args:
        text: The text to hash
        
    Returns:
        The SHA-256 hash as a hexadecimal string
    """
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def normalize_prompt(prompt: Union[str, Dict[str, Any]]) -> str:
    """
    Normalize a prompt to ensure consistent hashing.
    
    Args:
        prompt: The prompt to normalize, either as a string or a dictionary
        
    Returns:
        The normalized prompt as a string
    """
    if isinstance(prompt, str):
        return prompt.strip()
    elif isinstance(prompt, dict):
        # If the prompt is a dictionary, convert it to a string
        # This is useful for structured prompts
        return str(prompt).strip()
    else:
        raise ValueError(f"Unsupported prompt type: {type(prompt)}")


def hash_prompt(prompt: Union[str, Dict[str, Any]]) -> str:
    """
    Hash a prompt using SHA-256.
    
    Args:
        prompt: The prompt to hash, either as a string or a dictionary
        
    Returns:
        The SHA-256 hash as a hexadecimal string
    """
    normalized_prompt = normalize_prompt(prompt)
    return calculate_hash(normalized_prompt)
