# Active work for Augment Agent right now

We are working on some refactoring.

Frank now accepts a list of exchanges and replays them. If the prompt doesn't match, it is only a warning.
It always returns the next response in the list.

✅ Completed refactoring to add proper types:

[x] Make a type for the exchanges.
[x] Make a type for the conversation.
[x] Make the ConversationLogger use that type
[x] Make the ConversationReader return a Conversation type
[x] Make the Frank LLM use the Exchange type
[x] Make Frank return a response string
[x] Change the test to provide a proper list of Exchanges

All tasks have been completed and tests are passing. The code now has proper type definitions for Exchange and Conversation objects, making it more maintainable and type-safe.

## Next

I want to change how tool call results are recorded.

In a Conversation, the first exchange should have this structure:

```json
{
    "id": "exchange-1",
    "prompt": {
        "text": "The exact prompt text sent to the LLM",
        "metadata": {
            ... whatever...
        }
    },
    "response": {
        "text": "The full response from the LLM to replay",
        "tool_calls": [
            {
                "tool_name": "example_tool",
                "parameters": {"param1": "value1"},
                // never a result here
            }
        ]
    }
}
```

Then subsequent exchanges, after tool calls, should have this structure:

```json 
{
    "id": "exchange-2",
    "prompt": {
        "tool_calls": [
            {
                "tool_name": "example_tool",
                "parameters": {"param1": "value1"},
                "result": "Tool execution result"
            }
        ],
        "new_portion": "only the text that was not in the previous prompt",
        "text": "the whole prompt to send this time",
        "metadata": {
            ... whatever...
        }
    },
    "response": {
        "text": "Follow-up response from the LLM... maybe it doesn't have tool calls this time"
    }
}
```

[] change the structure of the Conversation types
[] make the agent send a prompt in this structure
[] make the test conversation follow this structure
[] make Frank return a response object including tool calls, as in the replay
[] the Agent no longer tries to log tool call results; instead it includes them in the Prompt structure
[] that way the ConversationLogger can just log the tool call results with the prompt, instead of trying to cram them into the previous exchange.
