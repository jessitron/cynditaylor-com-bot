# Create some real tests

We are going to work in small increments.
The end goal here is: property-based tests that express how the agent works, that print great summaries of what is happening when they fail.

## Make the agent more testable.

We are not implementing property-based tests yet. We are implementing only one test.

[x] The agent should accept an LLM provider in the constructor
[] Implement an in-memory version of the conversation logger
[] Implement an in-memory version of the conversation reader, which accepts a conversation as an a constructor argument
[] implement a fully-in-memory frank provider
[] use these in a test with a hard-coded conversation, checking that the logged conversation matches the one passed in.

### Detailed plan:

#### Step 1: Single Test Implementation ← do this first!
- Create test that:
  1. Instantiates agent with mock LLM provider
  - Use existing Frank LLM provider to replay responses from hard-coded conversations
  2. Uses `InMemoryConversationLogger` to capture exchanges (it doesn't exist yet)
  3. Uses `InMemoryConversationReader` with hard-coded conversation (it doesn't exist yet)
  4. Verifies logged conversation matches expected conversation structure

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

#### Step 3.5: In-Memory Frank Provider ← implement this now!
- Create `InMemoryFrankProvider` class that implements LLMProvider interface
- Accept a `Conversation` object in constructor instead of reading from file
- Use `InMemoryConversationReader` internally
- Enables fully in-memory testing without file dependencies

#### Step 4: Test Infrastructure
- Set up test fixtures with sample conversations for Frank to replay
- Add assertion helpers that compare conversation structures with readable error messages

### Instructions

Please implement only Step 1. I want to look at the test before we go any farther. It's OK that the test won't run yet!
I especially want to see whether you create the LLMProvider in a way that I think will work.

### Summary of what was accomplished:

#### Completed:
- [x] Created test structure in `tests/test_agent_conversation_logging.py` showing how Frank LLM provider will be used
- [x] Implemented `InMemoryConversationReader` class that accepts Conversation object in constructor  
- [x] Implemented `InMemoryFrankProvider` class that uses in-memory conversation instead of reading from file
- [x] Added Step 3.5 to plan for in-memory Frank provider
- [x] Implemented `InMemoryConversationLogger` class that stores exchanges in memory
- [x] Modified `LoggingConversationPartner` to accept external conversation logger
- [x] Updated `InMemoryFrankProvider` to accept and use conversation logger
- [x] Updated test to use all in-memory components and verify conversation matching

#### Implementation details:
- `InMemoryConversationReader`: Simple class that returns the conversation passed to constructor
- `InMemoryConversationLogger`: Stores exchanges in memory with same interface as file-based logger
- `InMemoryFrankProvider`: Accepts Conversation and logger in constructor, passes logger to LoggingConversationPartner
- `LoggingConversationPartner`: Modified to accept external logger via `conversation_logger` parameter
- Test creates in-memory logger, passes it to Frank provider, runs agent, and compares logged vs expected conversation
- Fully in-memory testing setup with no file dependencies