import os
import json
import hashlib
import uuid
import datetime
from typing import Dict, Any, List, Optional


class ConversationLogger:
    """
    Logger for tracking and recording conversations between the agent and LLM.
    Saves conversations in a standardized JSON format for later replay.
    """

    def __init__(self, output_dir: str = "conversation_history"):
        """
        Initialize the conversation logger.
        
        Args:
            output_dir: Directory where conversation history files will be saved
        """
        self.output_dir = output_dir
        self.conversation_id = str(uuid.uuid4())
        self.timestamp = datetime.datetime.now().isoformat()
        self.exchanges = []
        self.previous_prompt = None
        
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Add .gitignore to the output directory if it doesn't exist
        gitignore_path = os.path.join(output_dir, ".gitignore")
        if not os.path.exists(gitignore_path):
            with open(gitignore_path, "w") as f:
                f.write("*\n")
    
    def calculate_hash(self, text: str) -> str:
        """
        Calculate a SHA-256 hash of the given text.
        
        Args:
            text: The text to hash
            
        Returns:
            The SHA-256 hash as a hexadecimal string
        """
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def find_new_portion(self, current_prompt: str, previous_prompt: Optional[str]) -> Optional[str]:
        """
        Find the new portion of text that was added to the current prompt.
        
        Args:
            current_prompt: The current prompt text
            previous_prompt: The previous prompt text
            
        Returns:
            The new portion of text, or None if there is no previous prompt
        """
        if not previous_prompt:
            return None
            
        # Simple implementation: find the longest common prefix
        # and assume the rest is the new portion
        i = 0
        min_len = min(len(current_prompt), len(previous_prompt))
        
        while i < min_len and current_prompt[i] == previous_prompt[i]:
            i += 1
            
        # If the current prompt is entirely contained in the previous prompt,
        # or vice versa, this approach won't work well. In a real implementation,
        # we might want a more sophisticated diff algorithm.
        return current_prompt[i:].strip()
    
    def log_exchange(self, prompt: str, response: str, metadata: Dict[str, Any] = None, 
                    tool_calls: List[Dict[str, Any]] = None) -> None:
        """
        Log an exchange between the agent and the LLM.
        
        Args:
            prompt: The prompt sent to the LLM
            response: The response received from the LLM
            metadata: Optional metadata about the LLM call (temperature, max_tokens, etc.)
            tool_calls: Optional list of tool calls made during this exchange
        """
        if metadata is None:
            metadata = {}
            
        if tool_calls is None:
            tool_calls = []
            
        # Calculate the hash of the prompt
        prompt_hash = self.calculate_hash(prompt)
        
        # Find the new portion of the prompt
        new_portion = self.find_new_portion(prompt, self.previous_prompt)
        
        # Create the exchange object
        exchange = {
            "id": f"exchange-{len(self.exchanges) + 1}",
            "prompt": {
                "text": prompt,
                "hash": prompt_hash,
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
        """
        Log a tool call made during an exchange.
        
        Args:
            exchange_id: The ID of the exchange
            tool_name: The name of the tool
            parameters: The parameters passed to the tool
            result: The result returned by the tool
        """
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
    
    def save(self) -> str:
        """
        Save the conversation history to a JSON file.
        
        Returns:
            The path to the saved file
        """
        # Create the conversation history object
        conversation_history = {
            "version": "1.0",
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
            "exchanges": self.exchanges
        }
        
        # Generate a filename based on the timestamp
        date_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"conversation_{date_str}_{self.conversation_id[:8]}.json"
        file_path = os.path.join(self.output_dir, filename)
        
        # Write the conversation history to the file
        with open(file_path, "w") as f:
            json.dump(conversation_history, f, indent=2)
            
        return file_path
