# Computational Thinking — Professional

At professional level, decomposition shapes the organization’s ability to learn and deliver.

## Architecture and ownership are one design

Conway’s law means communication paths influence system boundaries. Use domain ownership, operational responsibility, and decision latency together. A technically elegant boundary without an accountable owner becomes a queue.

## Manage cognitive load

Teams should own coherent capabilities with clear interfaces and production responsibility. Platform teams reduce repeated cognitive load through paved roads—deployment, telemetry, identity, and data access—while preserving escape hatches for justified exceptions.

## Design evolutionary seams

Good seams support staged replacement, compatibility testing, traffic shaping, telemetry comparison, and rollback. Branch-by-abstraction, strangler migrations, consumer-driven contracts, and schema expansion/contraction are tools; each needs measurable exit criteria.

## Operability questions

- Which team owns the invariant when two components disagree?
- What metric reveals boundary latency, retries, or coordination cost?
- Can one team deploy and recover its capability independently?
- What fails first at 10× load or during dependency degradation?
- How will temporary dual paths be removed?

## Staff-level checklist

1. Frame the problem and non-negotiable invariants.
2. Map domain, data, failure, and ownership boundaries.
3. Compare modular and distributed options, including coordination cost.
4. Deliver a reversible vertical slice.
5. Instrument correctness and operational outcomes.
6. Expand only after evidence; remove obsolete paths.

```text
PROBLEM -> OUTCOMES -> CAPABILITIES -> SEAMS -> SLICES -> EVIDENCE -> EVOLUTION
            preserve invariants | assign ownership | keep reversal possible
```

## Test yourself

1. A proposed microservice has no independent data or owner. How do you evaluate it?
2. How would you measure cognitive load and boundary quality?
3. Design a staged extraction that can be stopped after any stage.
4. Which platform capabilities reduce repeated decomposition work without centralizing product decisions?

## Further reading

- David Parnas, “On the Criteria To Be Used in Decomposing Systems into Modules.”
- Eric Evans, *Domain-Driven Design*.
- Team Topologies by Skelton and Pais.
- Martin Fowler on branch by abstraction and the strangler fig pattern.
