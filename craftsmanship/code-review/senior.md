# Code Review — Senior

Senior review protects system evolution: compatibility, data migration, rollout, rollback, observability, capacity, and ownership.

For risky changes, review the operational plan alongside code. Require invariants, failure modes, staged exposure, metrics, and stop conditions. Preserve dissent in an architecture decision when the trade-off cannot be settled inside the diff.

Prevent review bottlenecks by distributing expertise, documenting ownership, pairing on unfamiliar areas, and escalating only high-blast-radius decisions. Approval should mean the evidence is sufficient, not that the reviewer would write identical code.

## Test yourself

1. What must accompany a schema-changing PR?
2. When should review move to a design forum?
3. How do you reduce single-reviewer dependency?
4. Which rollout metric should block expansion?

Continue to [`professional.md`](professional.md).
