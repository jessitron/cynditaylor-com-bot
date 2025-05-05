import logging
from opentelemetry import trace

from src.llm.conversation_partner import ConversationPartner
from src.conversation.types import Prompt, Response

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("opentelemetry-conversation-partner")

class OpenTelemetryConversationPartnerDecorator(ConversationPartner):

    def __init__(self, conversation_partner: ConversationPartner):
        self.conversation_partner = conversation_partner

    def get_response_for_prompt(self, prompt: Prompt) -> Response:
        # Create a span for this exchange
        with tracer.start_as_current_span("LLM Exchange") as span:
            # Add attributes to the span for the prompt
            span.set_attribute("app.llm.prompt.text", prompt.prompt_text[:10000])  # Truncate if too long
            span.set_attribute("app.llm.prompt.temperature", prompt.metadata.temperature)
            span.set_attribute("app.llm.prompt.max_tokens", prompt.metadata.max_tokens)
            if prompt.metadata.model:
                span.set_attribute("app.llm.model", prompt.metadata.model)
            
            # Add attributes for tool calls in the prompt if any
            if prompt.tool_calls:
                span.set_attribute("app.llm.prompt.tool_calls_count", len(prompt.tool_calls))
          
            # Get the response from the wrapped conversation partner
            response = self.conversation_partner.get_response_for_prompt(prompt)
            
            # Add attributes to the span for the response
            span.set_attribute("app.llm.response.text", response.response_text[:10000])  # Truncate if too long")
            
            # Add attributes for tool calls in the response if any
            if response.tool_calls:
                span.set_attribute("app.llm.response.tool_calls_count", len(response.tool_calls))

            return response

    def get_name(self) -> str:
        return f"OpenTelemetry-{self.conversation_partner.get_name()}"

    def finish_conversation(self) -> None:
        # Create a span for the finish_conversation call
        with tracer.start_as_current_span("LLM Finish Conversation"):
            # Delegate to the wrapped conversation partner
            self.conversation_partner.finish_conversation()
