# Log Aggregation — Junior

<!-- level-focus -->
At junior level, send structured logs from one service to a searchable central store.

## Method

Emit JSON with timestamp, level, service, event, and trace ID. A collector reads stdout, adds deployment metadata, and forwards it. Search one failed request by trace ID; never log secrets or raw credentials.

## Apply it

1. Emit a success and error event.
2. Configure one collector input.
3. Search both events by trace ID.

## Verify your work

- Fields are queryable rather than embedded prose.
- Sensitive values are absent.

## Review questions

- Why is structured logging easier to aggregate?
- Which field connects logs to traces?
