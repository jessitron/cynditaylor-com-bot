import logging
import os
import time
from opentelemetry import trace
import requests

from src.llm.conversation_partner import ConversationPartner
from src.conversation.types import Prompt, Response

logger = logging.getLogger(__name__)
tracer = trace.get_tracer("opentelemetry-conversation-partner")

class OpenTelemetryConversationPartnerDecorator(ConversationPartner):

    def __init__(self, conversation_partner: ConversationPartner):
        self.conversation_partner = conversation_partner
        self.trace_start_time = int(time.time())

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

    def finish_conversation(self) -> dict:
        with tracer.start_as_current_span("LLM Finish Conversation") as span:

            # Delegate to the wrapped conversation partner
            metadata = self.conversation_partner.finish_conversation()

            metadata["honeycomb_trace_url"] = self.link_to_current_trace()

            return metadata

    def link_to_current_trace(self) -> str:
        """
        Create a link to the current trace in Honeycomb.

        Returns:
            A URL to the current trace in Honeycomb, or None if there was an error
        """
        # Call Honeycomb Auth API to find out our team name
        try:
            response = requests.get(
                "https://api.honeycomb.io/1/auth",
                headers={"X-Honeycomb-Team": os.environ.get("HONEYCOMB_API_KEY")}
            )
            team_slug = response.json()["team"]["slug"]
            environment_slug = response.json()["environment"]["slug"]
        except Exception as e:
            logger.error(f"Failed to get team slug: {e}")
            return None

        # Get the current span
        current_span_context = trace.get_current_span().get_span_context()

        trace_id = current_span_context.trace_id
        trace_id = hex(trace_id)[2:]
        span_id = current_span_context.span_id
        span_id = hex(span_id)[2:]

        trace_start_ts = self.trace_start_time - 300  # 5 minutes in seconds
        trace_end_ts = int(time.time()) + 300  # 5 minutes in seconds

        url = f"https://ui.honeycomb.io/{team_slug}/environments/{environment_slug}/trace?trace_id={trace_id}&span_id={span_id}&trace_start_ts={trace_start_ts}&trace_end_ts={trace_end_ts}"
        logger.info(f"LLM conversation trace: {url}")

        return url


