import unittest
from src.conversation.types import TextPrompt, FinalResponse, ToolUseRequests, ToolUseResults


class ConversationTestCase(unittest.TestCase):
    """Base test case class with utilities for comparing conversations."""

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
        # Check prompt types match
        if type(expected) != type(actual):
            self.fail(f"Exchange {exchange_idx + 1} prompt type mismatch: "
                     f"expected {type(expected).__name__}, got {type(actual).__name__}")
        
        if isinstance(expected, TextPrompt):
            if expected.text != actual.text:
                self.fail(f"Exchange {exchange_idx + 1} prompt text mismatch:\n"
                         f"Expected: '{expected.text}'\n"
                         f"Actual:   '{actual.text}'")
        elif isinstance(expected, ToolUseResults):
            if len(expected.results) != len(actual.results):
                self.fail(f"Exchange {exchange_idx + 1} prompt tool results count mismatch: "
                         f"expected {len(expected.results)}, got {len(actual.results)}")
            
            for i, (expected_result, actual_result) in enumerate(zip(expected.results, actual.results)):
                if expected_result.id != actual_result.id:
                    self.fail(f"Exchange {exchange_idx + 1} prompt tool result {i + 1} ID mismatch: "
                             f"expected '{expected_result.id}', got '{actual_result.id}'")
                if expected_result.result != actual_result.result:
                    self.fail(f"Exchange {exchange_idx + 1} prompt tool result {i + 1} result mismatch:\n"
                             f"Expected: {expected_result.result}\n"
                             f"Actual:   {actual_result.result}")

    def _assert_responses_match(self, expected, actual, exchange_idx):
        """Compare two responses."""
        # Check response types match
        if type(expected) != type(actual):
            self.fail(f"Exchange {exchange_idx + 1} response type mismatch: "
                     f"expected {type(expected).__name__}, got {type(actual).__name__}")
        
        if isinstance(expected, FinalResponse):
            if expected.text != actual.text:
                self.fail(f"Exchange {exchange_idx + 1} response text mismatch:\n"
                         f"Expected: '{expected.text}'\n"
                         f"Actual:   '{actual.text}'")
        elif isinstance(expected, ToolUseRequests):
            # Compare optional text
            if expected.text != actual.text:
                self.fail(f"Exchange {exchange_idx + 1} response text mismatch:\n"
                         f"Expected: '{expected.text}'\n"
                         f"Actual:   '{actual.text}'")
            
            # Compare tool requests
            if len(expected.requests) != len(actual.requests):
                self.fail(f"Exchange {exchange_idx + 1} response tool requests count mismatch: "
                         f"expected {len(expected.requests)}, got {len(actual.requests)}")
            
            for i, (expected_request, actual_request) in enumerate(zip(expected.requests, actual.requests)):
                if expected_request.tool_name != actual_request.tool_name:
                    self.fail(f"Exchange {exchange_idx + 1} response tool request {i + 1} name mismatch: "
                             f"expected '{expected_request.tool_name}', got '{actual_request.tool_name}'")
                if expected_request.id != actual_request.id:
                    self.fail(f"Exchange {exchange_idx + 1} response tool request {i + 1} ID mismatch: "
                             f"expected '{expected_request.id}', got '{actual_request.id}'")
                if expected_request.parameters != actual_request.parameters:
                    self.fail(f"Exchange {exchange_idx + 1} response tool request {i + 1} parameters mismatch:\n"
                             f"Expected: {expected_request.parameters}\n"
                             f"Actual:   {actual_request.parameters}")

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
        print(f"  Type: {type(expected.prompt).__name__}")
        if isinstance(expected.prompt, TextPrompt):
            print(f"  Text: '{expected.prompt.text}'")
        elif isinstance(expected.prompt, ToolUseResults):
            print(f"  Tool Results: {len(expected.prompt.results)} results")
        
        print(f"\nActual Prompt:")
        print(f"  Type: {type(actual.prompt).__name__}")
        if isinstance(actual.prompt, TextPrompt):
            print(f"  Text: '{actual.prompt.text}'")
        elif isinstance(actual.prompt, ToolUseResults):
            print(f"  Tool Results: {len(actual.prompt.results)} results")
        
        print(f"\nExpected Response:")
        print(f"  Type: {type(expected.response).__name__}")
        if isinstance(expected.response, FinalResponse):
            print(f"  Text: '{expected.response.text}'")
        elif isinstance(expected.response, ToolUseRequests):
            print(f"  Text: '{expected.response.text}'")
            print(f"  Tool Requests: {len(expected.response.requests)} requests")
        
        print(f"\nActual Response:")
        print(f"  Type: {type(actual.response).__name__}")
        if isinstance(actual.response, FinalResponse):
            print(f"  Text: '{actual.response.text}'")
        elif isinstance(actual.response, ToolUseRequests):
            print(f"  Text: '{actual.response.text}'")
            print(f"  Tool Requests: {len(actual.response.requests)} requests")
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