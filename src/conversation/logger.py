import os
import json
import uuid
import datetime
from typing import Optional, Union, List

from src.conversation.types import Conversation, Exchange, Tool, TextPrompt, ToolUseResults, FinalResponse, ToolUseRequests


class ConversationLogger:
    def __init__(self, output_dir: str = "conversation_history", system_prompt: str = "", tools: List[Tool] = None):
        self.output_dir = output_dir
        self.conversation = Conversation(
            tool_list=tools or [],
            exchanges=[],
            system_prompt=system_prompt,
            conversation_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now()
        )
        self.previous_prompt_text = None

    
    def get_path_to_log(self) -> str:
        return os.path.join(self.output_dir, self.filename())

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
    
    def add_metadata(self, metadata: dict) -> None:
        self.conversation.metadata.update(metadata)

    def log_exchange(self, prompt: Union[TextPrompt, ToolUseResults], response: Union[FinalResponse, ToolUseRequests]) -> None:
        """
        Log an exchange between a user and an LLM.

        Args:
            prompt: The prompt sent to the LLM (TextPrompt or ToolUseResults)
            response: The response received from the LLM (FinalResponse or ToolUseRequests)
        """
        # Track text for finding new portions (only applies to TextPrompt)
        current_text = None
        if isinstance(prompt, TextPrompt):
            current_text = prompt.text
            if self.previous_prompt_text:
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

        # Update the previous prompt text
        if current_text:
            self.previous_prompt_text = current_text

        # Save the conversation after each exchange
        self.save()

    # The log_tool_call method has been removed as tool calls are now included in the prompt structure

    def filename(self) -> str:
        date_str = self.conversation.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"conversation_{date_str}_{self.conversation.conversation_id[:8]}.json"

    def save(self) -> str:
        # Convert the conversation to a dictionary
        conversation_dict = self.conversation.to_dict()

        file_path = self.get_path_to_log()

        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Write the conversation history to the file
        with open(file_path, "w") as f:
            json.dump(conversation_dict, f, indent=2)

        return file_path
