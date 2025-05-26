import uuid
import datetime
from typing import Optional, Union, List

from src.conversation.types import Conversation, Exchange, TextPrompt, ToolUseResults, FinalResponse, ToolUseRequests, Tool


class InMemoryConversationLogger:
    def __init__(self, system_prompt: str = "", tools: List[Tool] = None):
        self.conversation = Conversation(
            tool_list=tools or [],
            system_prompt=system_prompt,
            conversation_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(),
            exchanges=[]
        )
        self.previous_prompt_text = None

    def find_new_portion(self, current_prompt: str, previous_prompt: Optional[str]) -> Optional[str]:
        if not previous_prompt:
            return None

        # Simple implementation: find the longest common prefix
        # and assume the rest is the new portion
        i = 0
        min_len = min(len(current_prompt), len(previous_prompt))

        while i < min_len and current_prompt[i] == previous_prompt[i]:
            i += 1

        return current_prompt[i:].strip()

    def log_exchange(self, prompt: Union[TextPrompt, ToolUseResults], response: Union[FinalResponse, ToolUseRequests]) -> None:
        """
        Log an exchange between a user and an LLM.

        Args:
            prompt: The prompt sent to the LLM (TextPrompt or ToolUseResults)
            response: The response received from the LLM (FinalResponse or ToolUseRequests)
        """
        # Track text for finding new portions (only applies to TextPrompt)
        if isinstance(prompt, TextPrompt):
            # We could enhance TextPrompt to track new portions if needed
            pass

        # Create the exchange
        exchange_id = f"exchange-{len(self.conversation.exchanges) + 1}"
        exchange = Exchange(
            id=exchange_id,
            prompt=prompt,
            response=response
        )

        # Add the exchange to the conversation
        self.conversation.exchanges.append(exchange)

        # Update the previous prompt (only for TextPrompt)
        if isinstance(prompt, TextPrompt):
            self.previous_prompt_text = prompt.text

    def get_conversation(self) -> Conversation:
        """Return the logged conversation."""
        return self.conversation

    def filename(self) -> str:
        """Return a filename for compatibility, but doesn't create files."""
        date_str = self.conversation.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"conversation_{date_str}_{self.conversation.conversation_id[:8]}.json"

    def add_metadata(self, metadata: dict) -> None:
        """Add metadata to the conversation."""
        self.conversation.metadata.update(metadata)

    def save(self, metadata: Optional[dict] = None) -> str:
        """Return the filename for compatibility, but doesn't save files."""
        return self.filename()