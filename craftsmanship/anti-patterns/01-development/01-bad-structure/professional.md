# Bad Structure Anti-Patterns — Professional

> Structural quality is a product constraint. Balance readability, runtime cost, delivery speed, and operational risk with evidence.

## Goal

Establish measurable standards for structural health, while allowing contained exceptions for proven hot paths.

## Measure before changing a hot path

| Question | Evidence |
|---|---|
| Where is time spent? | Production tracing or a representative CPU profile. |
| What allocates? | Allocation profile and heap growth. |
| Did the change help? | Repeated benchmark and production comparison. |
| Is the code still safe? | Contract tests, error rate, and rollback criteria. |

```python
from timeit import repeat

def benchmark(fn, data):
    return min(repeat(lambda: fn(data), number=100, repeat=5))
```

Treat a benchmark as a decision input, not a permission slip to make all code clever.

## Structural trade-offs

- A wide or direct implementation may be correct in a measured hot path.
- Put that exception behind a clear interface, document its invariant, and test it directly.
- Do not generalize a fast path until real callers require variation.
- Do not claim a layer is expensive or free without measurement; runtime behavior depends on workload and implementation.

## Operating model

1. Set a small set of fitness signals: cycle time, change failure rate, hotspot churn, test duration, and relevant latency or allocation budgets.
2. Review trends by service or boundary, not a single universal complexity score.
3. Fund the highest-risk structural work with an owner, expected outcome, and stop condition.
4. Keep an exception register for deliberate complexity; revisit it when assumptions change.

## Decision record template

- **Problem:** Which change is expensive or risky today?
- **Evidence:** What traces, tests, or incident data support that claim?
- **Constraint:** Which compatibility, latency, or delivery limit matters?
- **Decision:** What boundary or contained exception will we use?
- **Exit:** What signal tells us to simplify, replace, or remove it?

## Check your understanding

1. What measurement would disprove your performance claim?
2. How will a deliberately ugly fast path stay contained?
3. Which structural metric would change a funding decision?
