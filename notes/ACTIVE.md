# Create some real tests

We are going to work in small increments.
The end goal here is: property-based tests that express how the agent works, that print great summaries of what is happening when they fail.

## Make the agent more testable.

We are not implementing property-based tests yet. We are implementing only one test.

[x] The agent should accept an LLM provider in the constructor
[x] Implement an in-memory version of the conversation logger
[x] Implement an in-memory version of the conversation reader, which accepts a conversation as an a constructor argument
[x] implement a fully-in-memory frank provider
[x] use these in a test with a hard-coded conversation, checking that the logged conversation matches the one passed in.
[] make a helper to compare conversations and print a nice diff when they don't match.

### Next step: make the test print a very clear result when it fails.
