import os
import json
import uuid
import datetime
from typing import Dict, Any, List, Optional


class ConversationLogger:
    def __init__(self, output_dir: str = "conversation_history"):
        self.output_dir = output_dir
        self.conversation_id = str(uuid.uuid4())
        self.timestamp = datetime.datetime.now()
        self.exchanges = []
        self.previous_prompt = None # TODO: use a structured prompt so I don't have to retro this

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

    def log_exchange(self, prompt: str, response: str, metadata: Dict[str, Any] = None,
                    tool_calls: List[Dict[str, Any]] = None) -> None:
        if metadata is None:
            metadata = {}

        if tool_calls is None:
            tool_calls = []

        # Find the new portion of the prompt
        new_portion = self.find_new_portion(prompt, self.previous_prompt)

        # Create the exchange object
        exchange = {
            "id": f"exchange-{len(self.exchanges) + 1}",
            "prompt": {
                "text": prompt,
                "metadata": metadata
            },
            "response": {
                "text": response,
                "tool_calls": tool_calls
            }
        }

        # Add the new portion if it exists
        if new_portion:
            exchange["prompt"]["new_portion"] = new_portion

        # Add the exchange to the list
        self.exchanges.append(exchange)

        # Update the previous prompt
        self.previous_prompt = prompt

        # Save the conversation after each exchange
        self.save()

    def log_tool_call(self, exchange_id: str, tool_name: str, parameters: Dict[str, Any],
                     result: Any) -> None:
        # Find the exchange
        for exchange in self.exchanges:
            if exchange["id"] == exchange_id:
                # Add the tool call to the exchange
                exchange["response"]["tool_calls"].append({
                    "tool_name": tool_name,
                    "parameters": parameters,
                    "result": result
                })
                break

        # Save the conversation after logging the tool call
        self.save()

    def filename(self) -> str:
        date_str = self.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"conversation_{date_str}_{self.conversation_id[:8]}.json"

    def save(self) -> str:
        # Create the conversation history object
        conversation_history = {
            "version": "1.0",
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat(),
            "exchanges": self.exchanges
        }

        file_path = os.path.join(self.output_dir, self.filename())

        # Ensure the output directory exists
        os.makedirs(self.output_dir, exist_ok=True)

        # Write the conversation history to the file
        with open(file_path, "w") as f:
            json.dump(conversation_history, f, indent=2)

        return file_path
