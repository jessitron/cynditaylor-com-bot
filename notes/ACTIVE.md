# Active work for Augment Agent right now

In this file, we will formulate a plan together. Separately, you will implement it.

Our goal now is better abstract the LLM provider from the agent flow.

Let me try to be very clear about this.

[] frank_provider never calls tools. Only agent.py can call tools.

[] frank_provider does not loop. It makes 1 call to the LLM.

also note: avoid adding `with tracer.start_as_current_span("span-name")` -- you're making too many spans.








