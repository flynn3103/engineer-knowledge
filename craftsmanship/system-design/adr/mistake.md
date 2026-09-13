# Architecture Decision Records (ADR) — Mistake

- **What an ADR gives you:** a shared, durable explanation for an important choice, so code review, incidents, and future work do not restart the same debate.
- **What it does not replace:** discovery, an RFC, a detailed design, a task plan, or a code review. An ADR records the decision that came out of those activities.
- **A useful rule:** write enough that a future teammate can judge whether the choice still fits, but not so much that the record turns into a design document nobody reads. Nygard recommends small, easy-to-digest records; Microsoft likewise advises keeping each one short, factual, and separate from design guidance ([Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions), [Microsoft Learn](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)).

## Common mistakes

- **Recording every minor code choice.** Why it hurts: the decision log fills with noise, so people stop looking for the few records that set real boundaries or quality commitments. Fix: create an ADR when a choice affects structure, a key quality, a shared dependency or contract, more than one team, or is hard to undo.

- **Putting several decisions into one ADR.** Why it hurts: “use an outbox, switch broker, and rewrite refunds” has mixed drivers and may change in separate phases. Fix: make one record about one choice; create linked ADRs when a later choice depends on it. Microsoft recommends splitting decisions that have separate phases ([Microsoft Learn](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)).

- **Writing only the winning option.** Why it hurts: “use a transactional outbox” does not tell a future reader why a direct publish or synchronous call was rejected. Fix: state the decision drivers and the real alternatives, then show why the chosen option fits them better.

- **Calling a draft accepted before the right people agree.** Why it hurts: downstream teams may build against a direction that was only one engineer’s proposal. Fix: use `Proposed` while feedback is open; mark `Accepted`, `Rejected`, or `Superseded` only when the agreed status is known. AWS describes this lifecycle explicitly ([AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)).

- **Hiding the downside.** Why it hurts: the cancellation-event ADR would look perfect if it omitted duplicate delivery, relay operations, and eventual delivery. Those costs later arrive as “surprises.” Fix: list good, bad, and neutral effects, plus the work each cost creates.

- **Turning the ADR into an implementation manual.** Why it hurts: a ten-page explanation of tables and handlers is slow to review and goes stale while the decision gets buried. Fix: state the choice, why, and consequences; link to the RFC or detailed design for implementation notes. The record must still stand on its own as a decision.

- **Quietly rewriting an accepted record.** Why it hurts: history disappears, and no one can tell when or why the system changed direction. Fix: keep accepted ADRs append-only; write a new ADR that supersedes the old one and link both. This preserves the decision history as context changes ([AWS Prescriptive Guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)).

- **Leaving out the evidence and the deciders.** Why it hurts: a reader cannot tell whether the outbox decision came from a measured failure mode, a product promise, a security rule, or one person’s preference. Fix: link the ticket, test, spike, RFC, or incident that informed it and name the decision makers or owner.

- **Giving no way to check the decision.** Why it hurts: “reliable” becomes an aspiration; nobody knows whether the outbox relay is meeting the reason it was chosen. Fix: add a confirmation method and a revisit trigger, such as an integration test, pending-event alert, delivery-delay target, or incident threshold. MADR includes confirmation for exactly this purpose ([MADR template](https://adr.github.io/madr/)).

- **Keeping the record where the delivery team cannot find it.** Why it hurts: a decision in a private meeting note or an unlinked wiki page is easily forgotten and later contradicted. Fix: keep a visible decision log with the workload documentation or repository, and link it from the ticket and pull request that use it.

## Quick judgment check

- **Write an ADR** when a cancellation feature requires a lasting rule for messaging, storage, security, deployment, data ownership, or a cross-team contract.
- **Use a ticket note or pull-request description instead** when the choice is local, obvious, cheap to reverse, and does not set a direction others need to follow.
- **Use an RFC or discovery document first** when the team has not yet selected an option. Create the ADR when the final direction is clear.

## Sources

- [Michael Nygard — Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [AWS Prescriptive Guidance — Architectural decision record process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
- [MADR — Markdown Architectural Decision Records](https://adr.github.io/madr/)
- [Microsoft Learn — Maintain an architecture decision record](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)

Continue to [Best Practise](best-practise.md).
