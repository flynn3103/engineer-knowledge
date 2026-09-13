# Architecture Decision Records (ADR) — Best Practise

- **Use this repeatable practice:** the **CODE Record** — **C**ontext, **O**ptions, **D**ecision, **E**ffects.
- **Aim for a decision a future teammate can use:** they should learn what was chosen, why it fit at the time, what it costs, and how to tell when it no longer fits.

## Start only when the choice deserves a record

- **Ask whether the choice changes a shared direction.** Does it affect system structure, a quality target, a dependency, a contract, a delivery practice, multiple teams, or something costly to reverse?
- **Start a `Proposed` ADR when discussion needs a focal point.** Do not wait until the context disappears into chat history.
- **Mark it `Accepted` only after the agreed reviewers decide.** Mark it `Rejected` when the team deliberately declines it.
- **Create a new record when the choice changes.** Mark the old accepted ADR `Superseded` and link to the replacement rather than rewriting history. This is the append-only model recommended by AWS and Microsoft ([AWS](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html), [Microsoft Learn](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)).

## The CODE Record, ready to copy

```md
# ADR-017: Use a transactional outbox for order-cancellation events

Status: Proposed | Accepted | Rejected | Superseded
Date:
Deciders:
Links: ticket, RFC or spike, design, pull request, incident

## Context and decision drivers
- What changed or what problem needs a decision?
- Which facts, constraints, quality targets, or contracts matter?

## Considered options
- Option A — why it could work; its important cost.
- Option B — why it could work; its important cost.
- Option C — why it could work; its important cost.

## Decision
We will use {chosen option} because {it best meets the named drivers}.

## Effects and confirmation
- Good:
- Cost or risk:
- Follow-up work and owner:
- How we will confirm the decision:
- Revisit trigger:
```

This template follows the common ADR elements of context, options, outcome, consequences, and confirmation in [MADR](https://adr.github.io/madr/). Keep it small enough that the people who must review it can read it in one sitting; Nygard’s original format targets one or two pages ([Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)).

## Fill it in with the cancellation-event example

- **Context:** say that order cancellation must persist before fulfillment acts, that a publish failure must not lose the event, and that duplicate handling must be safe.
- **Options:** compare synchronous downstream calls, direct publish after a database update, and a transactional outbox. Do not add a fake option just to make the list longer.
- **Decision:** write “We will use a transactional outbox because a committed cancellation and the intent to notify must not split during failure.”
- **Effects:** name the benefit (recoverable delivery), the cost (relay operations and duplicate-safe consumers), the owner, and the proof (transaction test plus pending-event alert).
- **Status:** leave it `Proposed` during review. Change it to `Accepted` when the order, fulfillment, and payments owners agree.

## Put the record into normal delivery work

- **Backlog refinement:** when a functional or non-functional requirement exposes a lasting technical choice, create the ADR stub and add the open question to the ticket.
- **Discovery or RFC review:** link experiments, traffic estimates, incident evidence, and stakeholder input. The RFC can explore; the ADR records the final result.
- **Before implementation:** resolve the critical options and consequences before a code path makes the decision by accident.
- **Pull request:** link the accepted ADR from the PR. Reviewers can check whether the code follows the agreed direction, not only whether it compiles.
- **Release and operations:** add the confirmation check to tests, dashboards, runbooks, or alerts. An ADR without a way to observe its promise is only a memory aid.
- **Incident or changed requirement:** read the relevant ADR first. If the premise changed, write a successor record that explains why the old direction no longer fits.
- **Onboarding:** point a new teammate to the decision log before they redesign a boundary or remove an apparently unnecessary component.

## Ready-to-accept checklist

- [ ] The title names one clear choice, not a project or meeting.
- [ ] The context gives facts, requirements, and constraints without quietly choosing an option first.
- [ ] The record names the viable options and their meaningful trade-offs.
- [ ] The decision says what the team will do and why, in one clear sentence.
- [ ] The status, decision date, owner, and deciders are visible.
- [ ] Positive, negative, and neutral consequences are all recorded.
- [ ] Follow-up work has an owner, and confirmation has a concrete test, review, metric, or alert.
- [ ] A future event that would trigger reconsideration is named.
- [ ] Links point to the ticket, evidence, RFC or design, and implementation without making the ADR unreadable by itself.
- [ ] A change in direction will create a new linked ADR, not erase the accepted one.

## Build the habit

- **Make “does this need an ADR?” a refinement question.** Ask it whenever the team chooses a dependency, data boundary, API rule, reliability technique, or security control.
- **Give each ADR a short review window.** People can comment on a one-page decision more reliably than on a large design document; resolve feedback before changing its status.
- **Use ADR links in code review.** A reviewer who asks “why this outbox?” should receive the record, not a search through old messages.
- **Review the decision log after a material incident or before a large change.** Check which assumptions are now false, then supersede only the decisions that need to change.
- **Keep the format consistent.** A predictable title, status, context, options, decision, effects, and check makes records easy to scan as the log grows.

## Sources

- [Michael Nygard — Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [AWS Prescriptive Guidance — Architectural decision record process](https://docs.aws.amazon.com/prescriptive-guidance/latest/architectural-decision-records/adr-process.html)
- [MADR — Markdown Architectural Decision Records](https://adr.github.io/madr/)
- [Microsoft Learn — Maintain an architecture decision record](https://learn.microsoft.com/en-us/azure/well-architected/architect-role/architecture-decision-record)
