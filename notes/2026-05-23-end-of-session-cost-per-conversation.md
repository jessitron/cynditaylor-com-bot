# 2026-05-23 — Cost per cyndibot conversation

Spot-checked Bedrock token cost in Honeycomb (env `cynditaylor-com-bot`, last 7d).

## Findings

3 conversations total, all from 2026-05-22. Cost at Sonnet 4.5 pricing ($3/M
input, $15/M output, no cache discount applied):

| Conversation | Cost |
| --- | --- |
| `thread-b351739…` | $7.94 |
| `thread-05a3a70…` | $3.92 |
| `thread-97eb919…` | $1.32 |
| **Total** | **$13.17** |

The $7.94 conversation had 53 chat-span LLM calls and ~2.4M input tokens.
Conversation history is being resent on every turn.

## Followups

- **No cache-token attributes on these spans.** `gen_ai.usage.cache_read_input_tokens`
  / `cache_write_input_tokens` are not populated, so we can't tell whether
  Bedrock prompt caching is helping. If Strands isn't passing
  `cachePoint` blocks to Bedrock Converse, we're paying full input rate
  for the resent history every turn. Worth instrumenting + checking Strands docs.
- This cost shape will not survive scaling beyond mom — each email round-trip
  is a few dollars right now.

## Honeycomb gotcha (worth knowing)

`run_query` scoped to `dataset_slug: "cynditaylor-com-bot"` errored with
"Query references columns not found in cached schema" for `gen_ai.usage.*`
columns, even though `get_span_details` clearly showed them on the `chat`
span. Workaround: `environment_wide_query: true` worked fine. Schema cache
was apparently stale for the dataset-scoped path. (Separately, the user is
chasing a Honeycomb bug on `list_aiconversations` — query URL `tCWWiXbFk3g`
reproduced today as `6Qn6BD6Fzhb`.)

## Query that worked

`run_query` with `environment_wide_query: true`:
- breakdowns: `gen_ai.conversation.id`
- calcs: `SUM(gen_ai.usage.input_tokens)` as `input_tokens`,
  `SUM(gen_ai.usage.output_tokens)` as `output_tokens`, `COUNT` as `llm_calls`
- formula: `cost_usd = ($input_tokens * 3 + $output_tokens * 15) / 1000000`
- filters: `gen_ai.usage.input_tokens` exists, `gen_ai.conversation.id` exists

Today's URL: <https://ui.honeycomb.io/modernity/environments/cynditaylor-com-bot/result/9fTHn5Kf9Fr>
