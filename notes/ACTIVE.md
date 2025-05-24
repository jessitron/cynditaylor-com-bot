# Create some real tests

We are going to work in small increments.
The end goal here is: property-based tests that express how the agent works, that print great summaries of what is happening when they fail.

## Make the agent more testable.

[] The agent should accept an LLM provider in the constructor
[] Implement an in-memory version of the conversation logger
[] Implement an in-memory version of the conversation reader, which accepts a conversation as an a constructor argument
[] use these in a test with a hard-coded conversation, checking that the logged conversation matches the one passed in.

### Detailed plan: