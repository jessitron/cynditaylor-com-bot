# Active work for Augment Agent right now

In this file, we will formulate a plan together. Separately, you will implement it.

Our goal is to re-implement how Frank responds so it can read a conversation history
and replay the LLM part in it, failing if the prompt it gets doesn't match the one the conversation expects.

[x] describe a format of conversation history file that will work for that.

Put your format description here:

## Proposed Conversation History Format

I propose a JSON-based format for the conversation history file that Frank can use to replay LLM responses:

```json
{
  "version": "1.0",
  "conversation_id": "unique-conversation-id",
  "timestamp": "2023-06-15T14:30:00Z",
  "exchanges": [
    {
      "id": "exchange-1",
      "prompt": {
        "text": "The exact prompt text sent to the LLM",
        "hash": "sha256-hash-of-prompt-for-verification",
        "metadata": {
          "temperature": 0.7,
          "max_tokens": 1000,
          "other_params": "as_needed"
        }
      },
      "response": {
        "text": "The full response from the LLM to replay",
        "tool_calls": [
          {
            "tool_name": "example_tool",
            "parameters": {"param1": "value1"},
            "result": "Tool execution result"
          }
        ]
      }
    },
    {
      "id": "exchange-2",
      "prompt": {
        "text": "Follow-up prompt including previous context",
        "new_portion": "only the text that was not in the previous prompt",
        "hash": "sha256-hash-of-prompt-for-verification",
        "metadata": {
          "temperature": 0.7,
          "max_tokens": 1000
        }
      },
      "response": {
        "text": "Follow-up response from the LLM"
      }
    }
  ]
}
```

[x] make the agent output the conversation history in this format.

Put your plan for this here:

## Plan for Implementing Conversation History Output

To make the agent output conversation history in the proposed format, we'll need to:

1. **Create a Conversation Logger Module**:
   - Implement a `ConversationLogger` class that will track and record all exchanges between the agent and the LLM
   - Add methods to calculate and store hashes of prompts
   - Include functionality to detect and record only the new portions of follow-up prompts

2. **Modify the LLM Interface**:
   - Update the existing LLM abstraction layer to pass all prompts through the logger
   - Ensure all metadata (temperature, max_tokens, etc.) is captured
   - Intercept and record all responses and tool calls

3. **Implement Hash Calculation**:
   - Add a utility function to generate consistent SHA-256 hashes of prompts
   - Ensure the hashing method is deterministic and can be reproduced when verifying prompts

4. **Add Conversation History File I/O**:
   - Create functions to save the conversation history to JSON files
   - Implement loading functionality for Frank to read these files
   - Add proper error handling for file operations

5. **Integrate with Frank LLM**:
   - Modify Frank to check incoming prompts against the conversation history
   - Implement the matching logic using the hash verification
   - Add appropriate error responses when prompts don't match

6. **Add Command-Line Options**:
   - Create flags to enable/disable conversation recording
   - Add options to specify the output file path
   - Include a debug mode that shows more details about prompt matching

7. **Testing Strategy**:
   - Create unit tests for the hash calculation and matching logic
   - Develop integration tests that verify the full conversation recording and replay
   - Include edge cases like very long prompts and complex tool interactions

8. **Documentation**:
   - Document the format thoroughly for future reference
   - Create examples showing how to use the conversation history files
   - Add comments explaining the implementation details

This implementation will allow us to accurately record all agent-LLM interactions and replay them through Frank, ensuring that responses match exactly when the same prompts are provided.

[] implement the conversation logger module

