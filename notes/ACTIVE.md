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

[] make the agent output the conversation history in this format.

Put your plan for this here:

