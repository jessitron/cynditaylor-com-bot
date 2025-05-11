import os
import json
import uuid
import datetime
from typing import Optional

from src.conversation.types import Conversation, Exchange, Prompt, Response


class ConversationLogger:
    def __init__(self, output_dir: str = "conversation_history"):
        self.output_dir = output_dir
        self.conversation = Conversation(
            conversation_id=str(uuid.uuid4()),
            timestamp=datetime.datetime.now(),
            exchanges=[]
        )
        self.previous_prompt_text = None
        self.metadata = {}

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

    def log_exchange(self, prompt: Prompt, response: Response) -> None:
        """
        Log an exchange between a user and an LLM.

        Args:
            prompt: The Prompt object sent to the LLM
            response: The Response object received from the LLM
        """
        # Update the new_text field if it's not already set
        if not prompt.new_text and self.previous_prompt_text:
            prompt.new_text = self.find_new_portion(prompt.prompt_text, self.previous_prompt_text)

        # Create the exchange
        exchange_id = f"exchange-{len(self.conversation.exchanges) + 1}"
        exchange = Exchange(
            id=exchange_id,
            prompt=prompt,
            response=response
        )

        # Add the exchange to the conversation
        self.conversation.exchanges.append(exchange)

        # Update the previous prompt
        self.previous_prompt_text = prompt.prompt_text

        # Save the conversation after each exchange
        self.save()

    # The log_tool_call method has been removed as tool calls are now included in the prompt structure

    def filename(self) -> str:
        date_str = self.conversation.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"conversation_{date_str}_{self.conversation.conversation_id[:8]}.json"

    def add_metadata(self, metadata: dict) -> None:
        """
        Add metadata to the conversation log.

        Args:
            metadata: A dictionary of metadata to add to the conversation log
        """
        self.metadata.update(metadata)

    def save(self) -> str:
        # Convert the conversation to a dictionary
        conversation_dict = self.conversation.to_dict()

        # Add metadata if it exists
        if self.metadata:
            conversation_dict["metadata"] = self.metadata

        file_path = os.path.join(self.output_dir, self.filename())

        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Write the conversation history to the file
        with open(file_path, "w") as f:
            json.dump(conversation_dict, f, indent=2)

        return file_path
