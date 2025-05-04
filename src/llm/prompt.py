from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class Prompt:
    """Structured representation of a prompt to an LLM."""
    conversation_so_far: str
    new_portion: Optional[str] = None