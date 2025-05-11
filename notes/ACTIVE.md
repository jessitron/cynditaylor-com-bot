# Active work for Augment Agent right now

Next it's time to add an OpenTelemetryConversationPartnerDecorator, that wraps each exchange in a span.

## Plan:

1. Create a new file `src/llm/opentelemetry_conversation_partner.py` that will contain the decorator class
2. Implement the `OpenTelemetryConversationPartnerDecorator` class that:
   - Follows the decorator pattern similar to `LoggingConversationPartner`
   - Wraps each exchange (get_response_for_prompt call) in an OpenTelemetry span
   - Adds relevant attributes to the span (prompt details, response details)
   - Properly delegates to the wrapped conversation partner
3. Update the necessary imports and ensure the decorator can be used in the codebase

## Implementation Status:
- [x] Create plan
- [x] Create new file for the decorator
- [x] Implement the decorator class

## Continuing
[x] Define the link_to_current_span method.
Find information about Honeycomb and OpenTelemetry in `notes/Clues-about-OpenTelemetry.md`

## Next

[] Make LoggingConversationPartner, in finish_conversation, accept a response from the downstream conversation partner, containing a dict of whatever fields. Include those fields in the conversation log.
[] Make OpenTelemetryConversationPartnerDecorator, in finish_conversation, return a link to the trace in Honeycomb as metadata for the LoggingConversationPartner to record.
[] Make OpenTelemetryConversationPartnerDecorator retain the start time of the trace, and set the trace_start_ts and trace_end_ts in the link correctly.