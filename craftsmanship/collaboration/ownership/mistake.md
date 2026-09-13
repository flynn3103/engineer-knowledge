# Ownership - Mistake

## When to use it

- **Use a named outcome owner when work crosses teams, needs a decision, has risky handoffs, or affects customers.** It makes the gaps visible before the outcome is lost between people.
- **Use a lighter version for a small, independent task.** If one engineer can safely finish and verify it alone, a full role map is extra ceremony; name the task and its result instead.
- **The benefit is clarity.** People know what they own, who makes the call, and when they will hear an update.
- **The cost is coordination.** Writing updates and asking for decisions takes time, so keep the record short and match it to the size and risk of the work.

## Common mistakes

- **Doing every task yourself because you own the outcome.** This turns the owner into a bottleneck and leaves specialists out of work they can do better. Fix: own coordination and the result; give investigation, testing, communication, and follow-up to the people best placed to do them.
- **Calling a task the outcome.** "Fix checkout" lets each person imagine a different finish line. Fix: state the user or system result, the boundary, and the proof of safety before assigning work.
- **Having several final decision makers.** People wait, debate the same choice again, or act on different answers. Fix: name one Approver for each meaningful decision; a Driver gathers input but does not need to have the final authority.
- **Using roles as labels with no next action.** A DACI table does not repair an incident or ship a feature. Fix: attach each role to a decision, an action, or a communication need, then remove the ceremony when the work is small.
- **Leaving actions in chat or in someone's memory.** Handoffs become invisible and the work that prevents a repeat often disappears. Fix: record every next action with an owner, due date, priority, and clear proof that it is finished.
- **Giving updates that only say "still working on it."** People cannot tell whether the plan changed, what risk grew, or what help is needed. Fix: share the current result, new evidence, next decision or action, risk, and next update time.
- **Treating a mistake as one person's failure.** People become defensive or hide facts that would prevent a repeat. Fix: use factual, blameless language and look for the system, tool, guardrail, or handoff that made the failure possible, as recommended by [Google SRE](https://sre.google/workbook/postmortem-culture/).
- **Closing the incident when the immediate fix lands.** The same failure can return because the underlying gap has no owner. Fix: verify the immediate result, communicate it, and track each prevention action to a measurable end state.
- **Keeping ownership after the work or authority has moved.** The old owner cannot make progress and the new team assumes someone else is handling it. Fix: make the handoff explicit: name the new owner, transfer the facts and open actions, and announce the new update path.

Continue to [Best Practise](best-practise.md).
