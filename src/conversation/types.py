"""
Type definitions for conversation exchanges and related structures.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import datetime


@dataclass
class PromptMetadata:
    """Metadata associated with a prompt."""
    temperature: float = 0.7
    max_tokens: int = 1000
    model: Optional[str] = None
    # Additional fields can be added as needed


@dataclass
class Prompt:
    """A prompt sent to an LLM."""
    text: str
    metadata: PromptMetadata = field(default_factory=PromptMetadata)
    new_portion: Optional[str] = None


@dataclass
class ToolCall:
    """A record of a tool call made by the LLM."""
    tool_name: str
    parameters: Dict[str, Any]
    result: Any


@dataclass
class Response:
    """A response from an LLM."""
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)


@dataclass
class Exchange:
    """A single exchange between a user and an LLM."""
    id: str
    prompt: Prompt
    response: Response


@dataclass
class Conversation:
    """A complete conversation consisting of multiple exchanges."""
    version: str = "1.0"
    conversation_id: str = ""
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    exchanges: List[Exchange] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the conversation to a dictionary for serialization."""
        return {
            "version": self.version,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat(),
            "exchanges": [
                {
                    "id": exchange.id,
                    "prompt": {
                        "text": exchange.prompt.text,
                        "metadata": {
                            "temperature": exchange.prompt.metadata.temperature,
                            "max_tokens": exchange.prompt.metadata.max_tokens,
                            **({"model": exchange.prompt.metadata.model} if exchange.prompt.metadata.model else {})
                        },
                        **({"new_portion": exchange.prompt.new_portion} if exchange.prompt.new_portion else {})
                    },
                    "response": {
                        "text": exchange.response.text,
                        "tool_calls": [
                            {
                                "tool_name": tool_call.tool_name,
                                "parameters": tool_call.parameters,
                                "result": tool_call.result
                            }
                            for tool_call in exchange.response.tool_calls
                        ]
                    }
                }
                for exchange in self.exchanges
            ]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create a Conversation object from a dictionary."""
        # Parse the timestamp
        timestamp = datetime.datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.datetime.now()
        
        # Create the exchanges
        exchanges = []
        for exchange_data in data.get("exchanges", []):
            # Create the prompt
            prompt_data = exchange_data.get("prompt", {})
            metadata = PromptMetadata(
                temperature=prompt_data.get("metadata", {}).get("temperature", 0.7),
                max_tokens=prompt_data.get("metadata", {}).get("max_tokens", 1000),
                model=prompt_data.get("metadata", {}).get("model")
            )
            prompt = Prompt(
                text=prompt_data.get("text", ""),
                metadata=metadata,
                new_portion=prompt_data.get("new_portion")
            )
            
            # Create the response
            response_data = exchange_data.get("response", {})
            tool_calls = []
            for tool_call_data in response_data.get("tool_calls", []):
                tool_call = ToolCall(
                    tool_name=tool_call_data.get("tool_name", ""),
                    parameters=tool_call_data.get("parameters", {}),
                    result=tool_call_data.get("result")
                )
                tool_calls.append(tool_call)
            
            response = Response(
                text=response_data.get("text", ""),
                tool_calls=tool_calls
            )
            
            # Create the exchange
            exchange = Exchange(
                id=exchange_data.get("id", f"exchange-{len(exchanges) + 1}"),
                prompt=prompt,
                response=response
            )
            
            exchanges.append(exchange)
        
        # Create the conversation
        return cls(
            version=data.get("version", "1.0"),
            conversation_id=data.get("conversation_id", ""),
            timestamp=timestamp,
            exchanges=exchanges
        )
