import os
import json
import uuid
import datetime
from typing import Dict, Any, List, Optional

from src.conversation.types import Conversation, Exchange, Prompt, Response, PromptMetadata, ToolCall


class ConversationLogger:
    def __init__(self, output_dir: str = "conversation_history"):
        self.output_dir = output_dir
        self.conversation = Conversation(
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

    def log_exchange(self, prompt_text: str, response_text: str, metadata: Dict[str, Any] = None,
                    prompt_tool_calls: List[Dict[str, Any]] = None,
                    response_tool_calls: List[Dict[str, Any]] = None) -> None:
        if metadata is None:
            metadata = {}

        if prompt_tool_calls is None:
            prompt_tool_calls = []

        if response_tool_calls is None:
            response_tool_calls = []

        # Find the new portion of the prompt
        new_text = self.find_new_portion(prompt_text, self.previous_prompt_text)

        # Create prompt metadata
        prompt_metadata = PromptMetadata(
            temperature=metadata.get("temperature", 0.7),
            max_tokens=metadata.get("max_tokens", 1000),
            model=metadata.get("model")
        )

        # Create the prompt tool calls
        prompt_tool_call_objects = []
        for tc in prompt_tool_calls:
            tool_call = ToolCall(
                tool_name=tc.get("tool_name", ""),
                parameters=tc.get("parameters", {}),
                result=tc.get("result")
            )
            prompt_tool_call_objects.append(tool_call)

        # Create the prompt
        prompt = Prompt(
            prompt_text=prompt_text,
            metadata=prompt_metadata,
            new_text=new_text,
            tool_calls=prompt_tool_call_objects
        )

        # Create the response tool calls
        response_tool_call_objects = []
        for tc in response_tool_calls:
            tool_call = ToolCall(
                tool_name=tc.get("tool_name", ""),
                parameters=tc.get("parameters", {}),
                result=tc.get("result")
            )
            response_tool_call_objects.append(tool_call)

        # Create the response
        response = Response(
            response_text=response_text,
            tool_calls=response_tool_call_objects
        )

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
        self.previous_prompt_text = prompt_text

        # Save the conversation after each exchange
        self.save()

    # The log_tool_call method has been removed as tool calls are now included in the prompt structure

    def filename(self) -> str:
        date_str = self.conversation.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"conversation_{date_str}_{self.conversation.conversation_id[:8]}.json"

    def save(self) -> str:
        # Convert the conversation to a dictionary
        conversation_dict = self.conversation.to_dict()

        file_path = os.path.join(self.output_dir, self.filename())

        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Write the conversation history to the file
        with open(file_path, "w") as f:
            json.dump(conversation_dict, f, indent=2)

        return file_path
