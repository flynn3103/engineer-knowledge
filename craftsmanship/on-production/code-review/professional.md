# Code Review — Professional

Professional review systems balance defect prevention, learning, ownership, and delivery tempo.

Google’s reviewer guidance emphasizes readability ownership and small changes. Gerrit and GitHub encode different workflow assumptions around patch sets and branch integration. Merge queues serialize tested heads because independently green pull requests can fail when combined.

Measure review wait time, time to first meaningful response, rework, escaped defects, ownership concentration, and merge-queue failure. Do not rank individuals by comments or approvals; those metrics are easily gamed.

## Design and operations checklist

1. Define which risks require which reviewers.
2. Automate objective checks before human attention.
3. Keep changes reviewable and mechanically separable.
4. Make ownership discoverable but transferable.
5. Provide escalation for security and architecture decisions.
6. Audit review outcomes and bottlenecks, not activity volume.

```text
CONTEXT -> RISK -> HUMAN JUDGMENT -> AUTOMATED EVIDENCE -> MERGE -> OUTCOME
              quality + learning + flow + accountable ownership
```

## Test yourself

1. Design review policy for a security-critical monorepo.
2. How do merge queues change correctness assumptions?
3. Which metric reveals overloaded expert reviewers?
4. How would you evaluate whether review prevents meaningful defects?

## Further reading

- Google Engineering Practices, Code Review Developer Guide.
- Michaela Greiler, *The Art of Code Review*.
- SmartBear, *Best Kept Secrets of Peer Code Review*.
