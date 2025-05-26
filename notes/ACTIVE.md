# Factoring out test utilities

Currently, there are two test files. They have a lot of duplicated code around comparing expected/actual and printing the difference.
(It also doesn't work, it needs to be about the new structure)

Pull that code into a shared place. After that, make it work.

## Plan

1. **Create shared test utilities module** (`tests/conversation_test_utils.py`)
   - Extract the identical methods from both test files:
     - `assert_conversations_match()` - Main comparison with detailed error messages
     - `_assert_exchanges_match()` - Exchange-level comparison
     - `_assert_prompts_match()` - Prompt comparison including metadata and tool calls
     - `_assert_responses_match()` - Response comparison including tool calls  
     - `_assert_tool_calls_match()` - Tool call list comparison
     - `_print_conversation_diff()` - Conversation-level diff printing
     - `_print_exchange_diff()` - Detailed exchange diff printing
     - `_print_trace_url_if_available()` - Debug trace URL printing

2. **Create ConversationTestCase base class**
   - Inherit from `unittest.TestCase`
   - Include all the extracted comparison methods
   - Make it easy for test classes to inherit these utilities

3. **Refactor existing test files** 
   - Make both test classes inherit from `ConversationTestCase`
   - Remove the duplicated methods (lines 52-209 in both files)
   - Import the new utilities module

4. **Fix/update the utilities for new conversation structure**
   - Ensure all comparison methods work correctly with current conversation types
   - Test that the refactored tests still pass