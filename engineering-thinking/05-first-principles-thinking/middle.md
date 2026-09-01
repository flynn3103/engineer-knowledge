# First-Principles Thinking — Middle

Derive design options from invariants. If orders must never be charged twice, idempotency is fundamental; a particular queue or database is not.

Use constraint mapping:

- correctness invariants;
- workload and latency evidence;
- regulatory and security obligations;
- team and operational capacity;
- budget and migration limits.

Generate at least three mechanisms satisfying the constraints, including a simpler option. Prototype the most uncertain mechanism, not the easiest demo.

## Test yourself

1. Which checkout requirement is an invariant?
2. How do measured constraints differ from forecasts?
3. Why include a simpler option?
4. Which uncertainty should a prototype target?

Continue to [`senior.md`](senior.md).
