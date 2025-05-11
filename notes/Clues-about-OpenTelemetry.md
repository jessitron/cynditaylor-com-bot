# Hey Augment, look here to find out how to do things in OpenTelemetry and Honeycomb

See also: Honeycomb MCP has some answers.

## Honeycomb API
Documentation lives here: https://api-docs.honeycomb.io/api

Assume the API key is available in $HONEYCOMB_API_KEY
The Honeycomb dataset we put data in is $OTEL_SERVICE_NAME

### Auth API example

Call: `curl -i -X GET https://api.honeycomb.io/1/auth -H 'X-Honeycomb-Team: YOUR_API_KEY_HERE'`

Response:
```
{
  "id": "FL_xMM5LapLC",
  "type": "configuration",
  "api_key_access": {
    "events": true,
    "markers": true,
    "triggers": false,
    "boards": false,
    "queries": false,
    "columns": false,
    "createDatasets": true,
    "slos": false,
    "recipients": false,
    "privateBoards": false
  },
  "environment": {
    "name": "Production",
    "slug": "production"
  },
  "team": {
    "name": "Honeycomb Docs",
    "slug": "honeycomb-docs"
  }
}
```

### How to get a URL to show a trace in Honeycomb:

Example:

```
https://ui.honeycomb.io/<team>/environments/<environment>/datasets/<dataset>/trace?trace_id=<traceId>
  &span=<spanId>
  &trace_start_ts=<ts>
  &trace_end_ts=<ts>
```

trace_start_ts and trace_end_ts are specified as UNIX/Epoch-style integer timestamps. Make trace_start_ts about 5m before the start of the trace, and trace_end_ts about 5m after the end of the trace.

Full documentation: https://docs.honeycomb.io/investigate/collaborate/share-trace/
