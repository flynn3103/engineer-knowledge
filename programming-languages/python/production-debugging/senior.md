# Python Production Debugging — Senior

Debug production as a system:

```mermaid
flowchart LR
    Symptom[alert or user report] --> Evidence[logs, metrics, traces]
    Evidence --> Hypothesis[one testable cause]
    Hypothesis --> Mitigation[reduce impact]
    Mitigation --> Fix[verified change]
    Fix --> Learning[runbook or guardrail]
```

Prioritize mitigation and blast-radius control. Use profiles, thread/task dumps, and database evidence only when the symptom points there. Record the invariant that the fix restores.
