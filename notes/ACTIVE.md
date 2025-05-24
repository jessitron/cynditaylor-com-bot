# Create some real tests

We are going to work in small increments.
The end goal here is: property-based tests that express how the agent works, that print great summaries of what is happening when they fail.

## Make the agent more testable.

[] The agent should accept an LLM provider in the constructor
[] Implement an in-memory version of the conversation logger
[] Implement an in-memory version of the conversation reader, which accepts a conversation as an a constructor argument
[] use these in a test with a hard-coded conversation, checking that the logged conversation matches the one passed in.

### Detailed plan:

#### Step 1: Agent Constructor Refactoring 
- [x] Agent already accepts LLMProvider in constructor (line 32 in agent.py)
- No changes needed for this requirement

#### Step 2: In-Memory Conversation Logger
- Create `InMemoryConversationLogger` class that implements same interface as `ConversationLogger`
- Store exchanges in memory list instead of writing to file
- Keep same `log_exchange(prompt, response)` method signature
- Return conversation data when requested instead of file path

#### Step 3: In-Memory Conversation Reader  
- Create `InMemoryConversationReader` class that implements same interface as `ConversationReader`
- Accept a `Conversation` object in constructor instead of file path
- `load_conversation()` method returns the conversation passed to constructor
- Enables testing with pre-defined conversation data

#### Step 4: Single Test Implementation ← do this first!
- Create test that:
  1. Instantiates agent with mock LLM provider
  2. Uses `InMemoryConversationLogger` to capture exchanges
  3. Uses `InMemoryConversationReader` with hard-coded conversation
  4. Verifies logged conversation matches expected conversation structure
  5. Prints detailed summaries on test failures showing differences

#### Step 5: Test Infrastructure
- Use existing Frank LLM provider to replay responses from hard-coded conversations
- Set up test fixtures with sample conversations for Frank to replay
- Add assertion helpers that compare conversation structures with readable error messages