# Active work for Augment Agent right now

We are working on some refactoring.

Frank now accepts a list of exchanges and replays them. If the prompt doesn't match, it is only a warning.
It always returns the next response in the list.

I'm having trouble with types being wrong. The exchanges are currently just whatever we read in from the file. They need a type.

[] Make a type for the exchanges.
[] Make a type for the conversation.
[] Make the ConversationLogger use that type
[] Make the ConversationReader return a Conversation type
[] Make the Frank LLM use the Exchange type
[] Make Frank return a response string
[] Change the test to provide a proper list of Exchanges