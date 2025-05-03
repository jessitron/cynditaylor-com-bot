from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from opentelemetry import trace

tracer = trace.get_tracer("cynditaylor-com-bot")


class Tool(ABC):
    """
    Abstract base class for tools that can be used by the agent.
    Each tool provides a specific functionality and can be executed by the agent.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Get the name of the tool.
        
        Returns:
            The name of the tool
        """
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """
        Get the description of the tool.
        
        Returns:
            The description of the tool
        """
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with the provided arguments.
        This method should be implemented by each tool and will be wrapped
        with OpenTelemetry spans.
        
        Args:
            **kwargs: Arguments for the tool execution
            
        Returns:
            Dictionary with the result of the tool execution
        """
        pass
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        Make the tool callable. This wraps the execute method with OpenTelemetry spans.
        
        Args:
            **kwargs: Arguments for the tool execution
            
        Returns:
            Dictionary with the result of the tool execution
        """
        with tracer.start_as_current_span(f"Execute tool: {self.name}"):
            return self.execute(**kwargs)
