# Decomposition - Professional

At this level, align architecture, team ownership, and delivery slices so teams can ship and operate value with minimal coordination.

## Align systems and teams

Systems tend to mirror the communication structures that build them. Use that deliberately:

1. Identify the domain capabilities you want.
2. Give one team end-to-end ownership of each capability.
3. Define contracts between teams and remove shared writes.
4. Give teams authority over code, data, deployment, observability, and on-call.
5. Measure how often delivery still requires cross-team coordination.

## Size boundaries to cognitive load

Keep a capability together when it shares business changes, atomic invariants, traffic patterns, failure tolerance, expertise, or compliance controls. Consider separation only when several signals support independent ownership and operation.

Prefer modules before services. A network boundary adds latency, partial failures, versioning, observability, and operational ownership.

> Modularize early. Distribute only when independent operation is worth its permanent integration cost.

## Measure recomposition costs

Treat frequent coordination as architecture data. Track:

- Changes that need multiple teams.
- Handoff wait time and synchronized releases.
- Contracts changed per feature.
- Cross-team incident escalation.
- Shared database writes.

## Decompose initiatives into vertical slices

Deliver a small end-to-end flow rather than separate database, backend, and UI milestones.

Each slice should:

- Deliver user value or decisive learning.
- Work end to end and be observable.
- Be reversible or safe to stop.
- Reduce uncertainty for the next slice.

Order slices by high-impact uncertainty, not ease. Test value, technical, migration, operational, and organizational risks early.

## Migrate safely

For a capability extraction:

1. Define and test internal contracts.
2. Shadow requests without customer impact.
3. Route a low-risk live flow.
4. Ramp traffic with automatic rollback.
5. Migrate remaining flows with measured exit criteria.
6. Remove the old path only after traffic and dependencies are gone.

The owning team must own orchestration, idempotency, recovery, observability, and on-call; dependencies must provide stable contracts.

## Initiative record

```markdown
## Outcome and measures
What changes for users or the business, and how will we measure it?

## Capability and ownership
What code, data, invariants, operations, and accountable team belong together?

## Coordination and risks
Which contracts and teams are involved? Rank assumptions by impact and uncertainty.

## Vertical slices
For each: value, scope, evidence, rollback, and exit criteria.

## Migration and retirement
How will traffic and data move, and when can the old path be removed?
```

## Checklist

- [ ] Architecture and ownership reinforce each other.
- [ ] One team owns every capability end to end.
- [ ] Service boundaries have several evidence-based justifications.
- [ ] Critical data and invariants have a clear owner.
- [ ] Coordination is measured and reduced.
- [ ] Slices provide value or learning and have rollback criteria.
- [ ] High-impact uncertainty is tested early.

> Professional decomposition aligns software, teams, and delivery so each piece can create value, operate safely, and evolve with minimal coordination.

Return to [junior](junior.md), [middle](middle.md), or [senior](senior.md).

## Check your understanding

1. How does Conway's law affect decomposition?
2. What evidence supports a service boundary?
3. What makes an initiative slice valuable and safe?
