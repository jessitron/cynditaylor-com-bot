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

Now let's have some fun.

[x] make a script that reads the conversation history and prints it to the terminal like in cowsay,

[x] implement Frank LLM to read conversation history and replay responses

Let's see whether you can make it better...

[x] Frank has ONLY replay mode, there is no other mode. All it does is replay one conversation, based on the default instruction.
[x] do not create method docstrings. Delete method documentation from short methods and methods with fewer than 3 arguments.
[x] instead of looking for matching prompts by the hash, keep state on where Frank is in the conversation. Either it gets exactly the prompt it was expecting, or else error.
[x] remove the prompt hashing stuff completely.

// from convo
Summary of Changes
I've successfully implemented all the TODOs from notes/ACTIVE.md:

Made Frank LLM only have replay mode
Removed the normal mode and fallback functionality
Simplified the FrankProvider class to only use the conversation reader
Made it raise errors when prompts don't match or when initialization fails
Removed method docstrings from short methods
Removed docstrings from methods with fewer than 3 arguments
Removed docstrings from short methods across the codebase
Updated conversation state tracking
Modified ConversationReader to track the current position in the conversation
Updated the prompt matching logic to expect the exact next prompt in sequence
Added better error handling for when prompts don't match
Removed prompt hashing completely
Removed the hash_util.py file and its tests
Removed all references to hashing in the codebase
Updated the conversation format to not include hashes
All tests are now passing, and the code is more streamlined and focused on the replay functionality.