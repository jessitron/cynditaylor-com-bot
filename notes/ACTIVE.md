# Active work for Augment Agent right now

In this file, we will formulate a plan together. Separately, you will implement it.

Our goal now is better abstract the LLM provider from the agent flow.

[x] The LLM provider knows about tools in order to tell the LLM about them.

[x] The LLM provider does not have the ability to execute tools.

[x] The agent has the ability to execute tools.

[x] Each tool should have its own class. Each conforms to a Tool interface.

[x] Each tool execution creates an OpenTelemetry span.





