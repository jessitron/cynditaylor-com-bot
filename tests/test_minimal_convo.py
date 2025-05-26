import unittest
import os

from requests import Response
from conversation.types import Conversation, Exchange, Prompt
from src.agent.agent import WebsiteAgent
from src.llm.in_memory_frank_provider import InMemoryFrankProvider
from src.llm.conversation_reader import ConversationReader
from src.conversation.in_memory_logger import InMemoryConversationLogger


class TestMinimalConvo(unittest.TestCase):
    def test_minimal_conversation_with_no_tool_calls(self):
        # create a Conversation with one exchange
        expected_conversation = Conversation(
            version="1.0",
            conversation_id="test-conversation-id",
            timestamp="2023-06-15T14:30:00Z",
            exchanges=[
                Exchange(
                    id="exchange-1",
                    prompt=Prompt(
                        prompt_text="Why did the monkey cross the road?",
                        metadata={"temperature": 0.7, "max_tokens": 1000},
                    ),
                    response=Response(
                        response_text="To get away with the food he just stole from you."
                    )
                )
            ]
        )

        # Create in-memory logger to capture what agent logs
        in_memory_logger = InMemoryConversationLogger()
        
        # Create in-memory Frank LLM provider with the logger
        frank_provider = InMemoryFrankProvider(expected_conversation, in_memory_logger)
        
        # Create agent with Frank provider
        agent = WebsiteAgent(frank_provider, website_dir="cynditaylor-com")
        
        # Execute the instruction (this should trigger Frank to replay the conversation)
        instruction = "answer the riddle"
        
        # Run the agent
        result = agent.execute_instruction(instruction)
        
        # Get the logged conversation
        logged_conversation = in_memory_logger.get_conversation()
        
        # Debug: print the metadata
        print(f"\nDEBUG: Logged conversation metadata: {logged_conversation.metadata}")
        
        # Compare conversations
        self.assert_conversations_match(expected_conversation, logged_conversation)
        
        # Verify we got a result
        self.assertIsNotNone(result)
        
    def assert_conversations_match(self, expected, actual):
        """
        Helper method to compare two conversations and provide detailed
        error messages when they don't match.
        """
        try:
            # Compare conversation-level fields
            if expected.version != actual.version:
                self._print_conversation_diff("version", expected.version, actual.version)
                self.fail(f"Version mismatch: expected '{expected.version}', got '{actual.version}'")
            
            
            # Compare exchange count
            if len(expected.exchanges) != len(actual.exchanges):
                self._print_conversation_diff("exchange_count", len(expected.exchanges), len(actual.exchanges))
                self.fail(f"Exchange count mismatch: expected {len(expected.exchanges)}, got {len(actual.exchanges)}")
            
            # Compare each exchange
            for i, (expected_exchange, actual_exchange) in enumerate(zip(expected.exchanges, actual.exchanges)):
                try:
                    self._assert_exchanges_match(expected_exchange, actual_exchange, i)
                except AssertionError as e:
                    self._print_exchange_diff(expected_exchange, actual_exchange, i)
                    raise e
        except AssertionError as e:
            # Print trace URL if available in actual conversation metadata
            self._print_trace_url_if_available(actual)
            raise e

    def _assert_exchanges_match(self, expected, actual, exchange_idx):
        """Compare two exchanges and raise detailed assertion errors."""
        # Compare exchange IDs
        if expected.id != actual.id:
            self.fail(f"Exchange {exchange_idx + 1} ID mismatch: expected '{expected.id}', got '{actual.id}'")
        
        # Compare prompts
        self._assert_prompts_match(expected.prompt, actual.prompt, exchange_idx)
        
        # Compare responses
        self._assert_responses_match(expected.response, actual.response, exchange_idx)

    def _assert_prompts_match(self, expected, actual, exchange_idx):
        """Compare two prompts."""
        if expected.prompt_text != actual.prompt_text:
            self.fail(f"Exchange {exchange_idx + 1} prompt text mismatch:\n"
                     f"Expected: '{expected.prompt_text}'\n"
                     f"Actual:   '{actual.prompt_text}'")
        
        if expected.new_text != actual.new_text:
            self.fail(f"Exchange {exchange_idx + 1} prompt new_text mismatch:\n"
                     f"Expected: '{expected.new_text}'\n"
                     f"Actual:   '{actual.new_text}'")
        
        # Compare metadata
        if expected.metadata.temperature != actual.metadata.temperature:
            self.fail(f"Exchange {exchange_idx + 1} prompt temperature mismatch: "
                     f"expected {expected.metadata.temperature}, got {actual.metadata.temperature}")
        
        if expected.metadata.max_tokens != actual.metadata.max_tokens:
            self.fail(f"Exchange {exchange_idx + 1} prompt max_tokens mismatch: "
                     f"expected {expected.metadata.max_tokens}, got {actual.metadata.max_tokens}")
        
        if expected.metadata.model != actual.metadata.model:
            self.fail(f"Exchange {exchange_idx + 1} prompt model mismatch: "
                     f"expected '{expected.metadata.model}', got '{actual.metadata.model}'")
        
        # Compare prompt tool calls
        self._assert_tool_calls_match(expected.tool_calls, actual.tool_calls, exchange_idx, "prompt")

    def _assert_responses_match(self, expected, actual, exchange_idx):
        """Compare two responses."""
        if expected.response_text != actual.response_text:
            self.fail(f"Exchange {exchange_idx + 1} response text mismatch:\n"
                     f"Expected: '{expected.response_text}'\n"
                     f"Actual:   '{actual.response_text}'")
        
        # Compare response tool calls
        self._assert_tool_calls_match(expected.tool_calls, actual.tool_calls, exchange_idx, "response")

    def _assert_tool_calls_match(self, expected_calls, actual_calls, exchange_idx, context):
        """Compare lists of tool calls."""
        if len(expected_calls) != len(actual_calls):
            self.fail(f"Exchange {exchange_idx + 1} {context} tool call count mismatch: "
                     f"expected {len(expected_calls)}, got {len(actual_calls)}")
        
        for i, (expected_call, actual_call) in enumerate(zip(expected_calls, actual_calls)):
            if expected_call.tool_name != actual_call.tool_name:
                self.fail(f"Exchange {exchange_idx + 1} {context} tool call {i + 1} name mismatch: "
                         f"expected '{expected_call.tool_name}', got '{actual_call.tool_name}'")
            
            if expected_call.parameters != actual_call.parameters:
                self.fail(f"Exchange {exchange_idx + 1} {context} tool call {i + 1} parameters mismatch:\n"
                         f"Expected: {expected_call.parameters}\n"
                         f"Actual:   {actual_call.parameters}")
            
            if expected_call.result != actual_call.result:
                self.fail(f"Exchange {exchange_idx + 1} {context} tool call {i + 1} result mismatch:\n"
                         f"Expected: {expected_call.result}\n"
                         f"Actual:   {actual_call.result}")

    def _print_conversation_diff(self, field_name, expected, actual):
        """Print a clear diff for conversation-level fields."""
        print(f"\n{'='*60}")
        print(f"CONVERSATION FIELD MISMATCH: {field_name}")
        print(f"{'='*60}")
        print(f"Expected: {expected}")
        print(f"Actual:   {actual}")
        print(f"{'='*60}")

    def _print_exchange_diff(self, expected, actual, exchange_idx):
        """Print a detailed diff for an exchange mismatch."""
        print(f"\n{'='*60}")
        print(f"EXCHANGE {exchange_idx + 1} MISMATCH")
        print(f"{'='*60}")
        print(f"Expected Exchange ID: {expected.id}")
        print(f"Actual Exchange ID:   {actual.id}")
        print(f"\nExpected Prompt:")
        print(f"  Text: '{expected.prompt.prompt_text}'")
        print(f"  New Text: '{expected.prompt.new_text}'")
        print(f"  Temperature: {expected.prompt.metadata.temperature}")
        print(f"  Max Tokens: {expected.prompt.metadata.max_tokens}")
        print(f"  Model: '{expected.prompt.metadata.model}'")
        print(f"  Tool Calls: {len(expected.prompt.tool_calls)} calls")
        
        print(f"\nActual Prompt:")
        print(f"  Text: '{actual.prompt.prompt_text}'")
        print(f"  New Text: '{actual.prompt.new_text}'")
        print(f"  Temperature: {actual.prompt.metadata.temperature}")
        print(f"  Max Tokens: {actual.prompt.metadata.max_tokens}")
        print(f"  Model: '{actual.prompt.metadata.model}'")
        print(f"  Tool Calls: {len(actual.prompt.tool_calls)} calls")
        
        print(f"\nExpected Response:")
        print(f"  Text: '{expected.response.response_text}'")
        print(f"  Tool Calls: {len(expected.response.tool_calls)} calls")
        
        print(f"\nActual Response:")
        print(f"  Text: '{actual.response.response_text}'")
        print(f"  Tool Calls: {len(actual.response.tool_calls)} calls")
        print(f"{'='*60}")

    def _print_trace_url_if_available(self, conversation):
        """Print the Honeycomb trace URL if available in conversation metadata."""
        trace_url = conversation.metadata.get('honeycomb_trace_url')
        if trace_url:
            print(f"\n{'='*60}")
            print(f"TRACE URL FOR DEBUGGING:")
            print(f"{'='*60}")
            print(f"{trace_url}")
            print(f"{'='*60}")
        else:
            print(f"\n{'='*60}")
            print(f"NO TRACE URL AVAILABLE")
            print(f"{'='*60}")


if __name__ == '__main__':
    unittest.main()