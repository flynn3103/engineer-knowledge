# Time Management — Mistake

The Pressure Commitment Loop is useful when time is scarce, but only if the commitment stays honest and visible.

## When this approach helps — and when it does not

- **Use it for work with a real deadline or competing priorities.** It exposes the choice between scope, time, and help before the choice becomes an emergency.
- **Keep it light for tiny, reversible requests.** A five-minute correction does not need a formal estimate; confirm the impact and do it.
- **Do not use it to hide a quality problem.** Cutting scheduled export from Maya's demo scope is sensible; shipping a CSV that leaks another customer's invoices is not. Variable scope means choosing what to build, not dropping necessary safety or correctness.

## Common mistakes

- **Saying yes before looking at existing work.** Maya accepts the Friday export, then discovers the invoice bug already consumes the time.
  - Why it hurts: the team hears a promise, while Maya is silently making two incompatible ones.
  - Fix: list current commitments and ask which one loses priority before accepting the new work.

- **Estimating a title instead of a deliverable.** "CSV export: one day" hides filter behavior, empty data, encoding, tests, review, and release.
  - Why it hurts: hidden work becomes "unexpected" work late in the week.
  - Fix: name a small first version, split it into visible parts, use similar completed work, and state assumptions. Keep the result a range, not a magic number.

- **Treating all requests as must-have.** Maya tries to include custom columns, scheduled emails, and filter reuse because they appeared in one conversation.
  - Why it hurts: scope grows while the date stays fixed, so testing and communication are squeezed out.
  - Fix: label must-haves, nice-to-haves, and out-of-scope work. Basecamp recommends asking whether the work can ship without an item and who is affected before keeping it in a fixed time box ([Decide When to Stop](https://basecamp.com/shapeup/3.5-chapter-14)).

- **Giving a soft no.** "I will try" or "maybe Friday" sounds polite but leaves the requester planning on a yes.
  - Why it hurts: nobody makes the needed trade-off, and disappointment arrives at the deadline.
  - Fix: state the constraint and one or two real alternatives: smaller scope, later date, different owner, or a priority swap.

- **Escalating only when the work is already late.** Maya waits until Friday to mention that filter reuse is hard.
  - Why it hurts: the person who can change scope has no time left to choose.
  - Fix: set a checkpoint around the biggest unknown. Report what is done, what remains, what changed, and the decision needed.

- **Using pressure as a reason to skip thinking.** "It is urgent" becomes a reason to omit tests, review, or a rollback plan.
  - Why it hurts: a rushed release can create more work than the request saved.
  - Fix: shrink optional product scope first. Keep the quality checks that make the committed slice safe to release.

- **Turning every update into a long task list.** Maya reports 19 tickets instead of saying whether the demo's download is on track.
  - Why it hurts: stakeholders cannot see the outcome or make a decision.
  - Fix: update by scope: finished outcome, next outcome, risk, and decision needed. Scope-sized updates make status clearer than a pile of task detail ([Basecamp's scope map](https://basecamp.com/shapeup/3.3-chapter-12)).

Continue to [Best Practise](best-practise.md).
