# Active work for the agent right now

I want to make it easier to test the exchanges. Right now, the system prompt gets crammed into the prompt text, so any test has to hard-code the expectation of it.

Let's break out the system prompt from the exchanges, and make it a property of the conversation instead.

## Plan:

### Current Problem
- System prompts are embedded in `prompt_text` field of each exchange
- Test files like `/workspaces/cynditaylor-com-bot/test_conversations/test_conversation.json` show long system prompts mixed with user instructions 
- Tests must hard-code expectations including the full system prompt text
- This makes tests brittle and hard to maintain

### Solution: Separate System Prompt from Exchange Data

1. **Add `system_prompt` field to Conversation class**
   - Add `system_prompt: Optional[str] = None` to Conversation dataclass
   - Update `to_dict()` and `from_dict()` methods to handle system_prompt

2. **Modify Prompt class to store user content only**
   - Keep `prompt_text` for actual user instructions/content
   - Remove system prompt content from prompt_text

3. **Update conversation partners to use system_prompt**
   - Modify agent.py to set system_prompt on conversation
   - Update LLM providers to combine system_prompt + prompt_text when making calls
   - Ensure Frank LLM provider handles system_prompt separately

4. **Update test files and test structure**
   - Extract system prompts from existing test_conversation.json files
   - Put system prompt in conversation-level field
   - Simplify prompt_text to contain only user instructions
   - Update test assertions to check system_prompt separately

5. **Update logging and serialization**
   - Ensure ConversationLogger handles system_prompt field
   - Update visualization tools to display system_prompt separately

### Files to modify:
- `/workspaces/cynditaylor-com-bot/src/conversation/types.py` - Add system_prompt to Conversation
- `/workspaces/cynditaylor-com-bot/src/agent/agent.py` - Set system_prompt when creating conversation
- `/workspaces/cynditaylor-com-bot/src/llm/frank_llm/frank.py` - Handle system_prompt
- `/workspaces/cynditaylor-com-bot/test_conversations/test_conversation.json` - Restructure test data
- Test files in `/workspaces/cynditaylor-com-bot/tests/` - Update assertions

