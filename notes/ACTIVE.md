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