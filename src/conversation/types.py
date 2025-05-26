"""
Type definitions for conversation exchanges and related structures.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Union
import datetime


@dataclass
class Tool:
    """Definition of a tool available in the conversation."""
    name: str
    description: str


@dataclass
class TextPrompt:
    """A text prompt sent to an LLM."""
    text: str


@dataclass
class ToolUse:
    """A request to use a tool."""
    tool_name: str
    id: str
    parameters: Dict[str, Any]


@dataclass
class ToolUseRequests:
    """A collection of tool use requests with optional accompanying text."""
    requests: List[ToolUse] = field(default_factory=list)
    text: Optional[str] = None


@dataclass
class ToolUseResult:
    """The result of a tool use."""
    id: str
    result: Any


@dataclass
class ToolUseResults:
    """A collection of tool use results."""
    results: List[ToolUseResult] = field(default_factory=list)


@dataclass
class FinalResponse:
    """A final text response from an LLM."""
    text: str


@dataclass
class Exchange:
    """A single exchange between a user and an LLM."""
    id: str
    prompt: Union[TextPrompt, ToolUseResults]
    response: Union[FinalResponse, ToolUseRequests]


@dataclass
class Conversation:
    """A complete conversation consisting of multiple exchanges."""
    tool_list: List[Tool]
    exchanges: List[Exchange]
    system_prompt: str = ""
    version: str = "2.0"
    conversation_id: str = ""
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the conversation to a dictionary for serialization."""
        exchanges_data = []
        for exchange in self.exchanges:
            # Handle prompt serialization
            if isinstance(exchange.prompt, TextPrompt):
                prompt_data = {"type": "text", "text": exchange.prompt.text}
            elif isinstance(exchange.prompt, ToolUseResults):
                prompt_data = {
                    "type": "tool_results",
                    "results": [{"id": r.id, "result": r.result} for r in exchange.prompt.results]
                }
            
            # Handle response serialization
            if isinstance(exchange.response, FinalResponse):
                response_data = {"type": "final", "text": exchange.response.text}
            elif isinstance(exchange.response, ToolUseRequests):
                response_data = {
                    "type": "tool_requests",
                    "requests": [{"tool_name": r.tool_name, "id": r.id, "parameters": r.parameters} for r in exchange.response.requests]
                }
                if exchange.response.text:
                    response_data["text"] = exchange.response.text
            
            exchanges_data.append({
                "id": exchange.id,
                "prompt": prompt_data,
                "response": response_data
            })
        
        return {
            "tool_list": [{"name": tool.name, "description": tool.description} for tool in self.tool_list],
            "exchanges": exchanges_data,
            "system_prompt": self.system_prompt,
            "version": self.version,
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Conversation':
        """Create a Conversation object from a dictionary."""
        # Parse the timestamp
        timestamp = datetime.datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.datetime.now()

        # Create tool list
        tool_list = []
        for tool_data in data.get("tool_list", []):
            tool_list.append(Tool(
                name=tool_data["name"],
                description=tool_data["description"]
            ))

        # Create exchanges
        exchanges = []
        for exchange_data in data.get("exchanges", []):
            # Create the prompt
            prompt_data = exchange_data.get("prompt", {})
            prompt = None
            if prompt_data.get("type") == "text":
                prompt = TextPrompt(text=prompt_data.get("text", ""))
            elif prompt_data.get("type") == "tool_results":
                results = []
                for result_data in prompt_data.get("results", []):
                    results.append(ToolUseResult(
                        id=result_data.get("id", ""),
                        result=result_data.get("result")
                    ))
                prompt = ToolUseResults(results=results)
            else:
                # Default to empty text prompt if type is unknown
                prompt = TextPrompt(text="")

            # Create the response
            response_data = exchange_data.get("response", {})
            response = None
            if response_data.get("type") == "final":
                response = FinalResponse(text=response_data.get("text", ""))
            elif response_data.get("type") == "tool_requests":
                requests = []
                for request_data in response_data.get("requests", []):
                    requests.append(ToolUse(
                        tool_name=request_data.get("tool_name", ""),
                        id=request_data.get("id", ""),
                        parameters=request_data.get("parameters", {})
                    ))
                response = ToolUseRequests(
                    requests=requests,
                    text=response_data.get("text")
                )
            else:
                # Default to empty final response if type is unknown
                response = FinalResponse(text="")

            # Create the exchange
            exchange = Exchange(
                id=exchange_data.get("id", f"exchange-{len(exchanges) + 1}"),
                prompt=prompt,
                response=response
            )
            exchanges.append(exchange)

        # Create the conversation
        return cls(
            tool_list=tool_list,
            exchanges=exchanges,
            system_prompt=data.get("system_prompt", ""),
            version=data.get("version", "2.0"),
            conversation_id=data.get("conversation_id", ""),
            timestamp=timestamp,
            metadata=data.get("metadata", {})
        )
