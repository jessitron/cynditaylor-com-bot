#!/usr/bin/env python3
"""Print a Honeycomb UI URL for a per-session SUM(cost.usd) query.

The query embeds `cost.usd` as a calculated_field so you can run it before
the derived column exists in the schema, then "Save as derived column"
from the query page.
"""

import json
import urllib.parse

EXPR = (
    "ADD("
    "MUL(COALESCE($cost.ses.send.qty, 0), COALESCE($cost.ses.send.price, 0)),"
    "MUL(COALESCE($cost.bedrock.input.qty, 0), COALESCE($cost.bedrock.input.price, 0)),"
    "MUL(COALESCE($cost.bedrock.output.qty, 0), COALESCE($cost.bedrock.output.price, 0)),"
    "MUL(COALESCE($cost.bedrock.cache_read.qty, 0), COALESCE($cost.bedrock.cache_read.price, 0)),"
    "MUL(COALESCE($cost.bedrock.cache_write.qty, 0), COALESCE($cost.bedrock.cache_write.price, 0)),"
    "DIV(MUL(COALESCE($cost.agentcore.cpu.seconds, 0), COALESCE($cost.agentcore.cpu.usd_per_hour, 0)), 3600),"
    "DIV(MUL(MUL(COALESCE($cost.agentcore.memory.peak_rss_bytes, 0), COALESCE($cost.agentcore.memory.usd_per_gb_hour, 0)), $duration_ms), 3600000000000)"
    ")"
)

QUERY = {
    "calculations": [{"op": "SUM", "column": "cost.usd"}],
    "calculated_fields": [{"name": "cost.usd", "expression": EXPR}],
    "breakdowns": ["session.id"],
    "orders": [{"op": "SUM", "column": "cost.usd", "order": "descending"}],
    "time_range": 604800,
}

URL = (
    "https://ui.honeycomb.io/modernity/environments/cynditaylor-com-bot"
    "/datasets/cynditaylor-com-bot?query="
    + urllib.parse.quote(json.dumps(QUERY))
)

print(URL)
