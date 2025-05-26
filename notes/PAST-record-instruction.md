# Make the conversation record more informative

see src/agent/agent.py
line 94:

   llm = self.llm_provider.start_conversation()

Right after this, I want to pass the instruction to the llm, so that it can record it as metadata on the conversation, like this:

llm.record_metadata("instruction", instruction)

That instruction should wind up in the conversation history's metadata section

## Plan:

Based on analysis of the codebase:

1. **Understanding**: The conversation system has:
   - `Conversation` type with `metadata: Dict[str, Any]` field (src/conversation/types.py:57)
   - `ConversationLogger.add_metadata()` method to update conversation metadata (src/conversation/logger.py:38)
   - `LoggingConversationPartner` wraps conversation partners and handles logging (src/llm/logging_conversation_partner.py)

2. **Implementation Steps**:
   a. Add `record_metadata(key: str, value: Any)` method to base `ConversationPartner` class (src/llm/conversation_partner.py)
   b. Implement the method in `LoggingConversationPartner` to delegate to `conversation_logger.add_metadata()`
   c. Add the call `llm.record_metadata("instruction", instruction)` in `agent.py` after line 94

3. **Expected Result**: 
   - The instruction will be stored in the conversation history's metadata section
   - Conversations will be more informative with context about what task was being performed

## Implementation Status:
- [x] Add `record_metadata` method to `ConversationPartner` class
- [x] Implement `record_metadata` in `LoggingConversationPartner`
- [x] Add call to `record_metadata` in `agent.py`
- [x] Run the application and verify the instruction is logged correctly

## Summary:
Successfully implemented instruction recording in conversation metadata. The instruction now appears in the conversation history's metadata section as requested. Verified through test output showing: `{'instruction': "Update the hero section...", ...}` in the logged conversation metadata.