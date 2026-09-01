# Mixing Async and Blocking - Senior

> Offloading prevents loop stalls; isolation and admission control prevent
> offload pools from becoming the next outage.

A CDC service may use blocking calls for schema registry, DNS, and a warehouse
driver. One shared pool lets a warehouse outage consume every worker and starve
schema refreshes. Separate pools when workloads have different latency and
criticality, then bound each queue.

| Failure | Signal | Safer design |
|---|---|---|
| Pool starvation | active=max, queue delay rises | isolate pools, reject early |
| Timeout but work continues | abandoned work count | client-side deadline/cancel API |
| Nested pool deadlock | workers waiting on same pool | prohibit nested sync waits |
| CPU steals loop time | loop lag tracks CPU | process/compute executor |

Retries multiply occupancy. If 32 blocked calls each retry three times while the
downstream remains unavailable, the pool becomes a retry reservoir. Apply one
end-to-end deadline, exponential backoff with jitter, and a retry budget.

Shutdown must stop admissions before closing executors. Decide whether accepted
uploads drain or cancel, cap the drain interval, and expose unfinished work so
operators know whether replay is required.

## Test yourself

1. When should two blocking dependencies use separate pools?
2. How can retries turn a bounded worker pool into prolonged overload?
3. What evidence would reveal a nested pool deadlock?

Continue to [`professional.md`](professional.md).
