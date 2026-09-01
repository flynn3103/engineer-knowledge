# Over-Engineering Anti-Patterns — Professional

> Complexity should earn its carrying cost. Evaluate it with workload evidence, operational constraints, and a clear exit path.

## Goal

Set portfolio-level rules that prevent speculative complexity while protecting justified reliability, security, and performance investments.

## Evidence before investment

| Proposed investment | Evidence required |
|---|---|
| Performance optimization | Representative profile, benchmark, and target budget. |
| New service or queue | Independent scaling, ownership, failure-isolation, or deployment need. |
| Platform or framework | Multiple supported consumers and funded long-term ownership. |
| Configurable policy | Validated owner workflow, audit trail, and rollback model. |

```python
from timeit import repeat

def compare(candidate, baseline, data):
    candidate_time = min(repeat(lambda: candidate(data), number=100, repeat=5))
    baseline_time = min(repeat(lambda: baseline(data), number=100, repeat=5))
    return candidate_time, baseline_time
```

Benchmark representative workloads, then check memory, failure behavior, and operational complexity. A faster microbenchmark can still be the worse system decision.

## Controls that preserve simplicity

- Maintain architecture decision records with problem, alternatives, owner, metrics, and expiry or review date.
- Set service and dependency budgets appropriate to the organization; exceptions need evidence and an owner.
- Review platforms as products with adoption, support, and retirement measures.
- Track cost of complexity: deploy duration, incident recovery, onboarding time, change failure rate, and operational toil.
- Prefer a reversible experiment over a permanent framework when uncertainty is high.

## Deliberate exceptions

Some complexity is essential: a security boundary, regulated audit trail, data isolation, or proven load requirement. Isolate it, document the invariant it protects, test it, and revisit its assumptions rather than treating “simple” as the only virtue.

## Check your understanding

1. What would falsify the claim that a new platform is needed?
2. Which operational metric captures complexity better than source-line count?
3. How will you know a deliberate exception can be retired?
