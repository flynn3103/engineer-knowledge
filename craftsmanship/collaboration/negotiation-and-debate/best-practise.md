# Negotiation and Debate - Best Practise

## Pattern: the Position-to-Decision Loop

- **Frame the choice.** Write the decision, deadline, decision owner, and cost of waiting.
- **List positions and interests separately.** A position is "ship Friday"; an interest is "give the customer credible proof before the renewal meeting."
- **Agree on criteria before defending options.** Use measures that can prove or disprove an option, such as a load-test result, rollback time, customer date, or support impact.
- **Write options before judging them.** Include an option that changes scope, exposure, timing, or sequencing rather than only arguing for the two opening demands.
- **Get focused challenge.** Ask people to comment on evidence, missing risks, and the criteria. Use silent writing first when hierarchy or strong personalities could shape the room.
- **Record the decision.** State the option, why it won, the people who own the next steps, and the evidence that would reopen it.
- **Commit after the call.** Challenge a decision respectfully before it is made. Afterward, support the work unless new material evidence appears.

## Start with this template

```text
Decision: [The exact choice]
Decision owner and deadline: [Who decides and when]
Cost of waiting: [What happens if we do not decide]

Positions: [What each side says it wants]
Interests: [Need, risk, or constraint behind each position]
Criteria: [Facts or measures the option must meet]
Options: [At least two distinct paths]

Decision: [Chosen option and why]
Actions: [Action | owner | due time | proof of done]
Review trigger: [New evidence that would reopen the choice]
```

## Use it in the export-launch example

- **Frame:** Decide what customers can safely see by Friday, with the product lead as decision owner.
- **Interests:** Product needs proof for the renewal meeting; engineering needs a proven stop-and-recover path; support needs a clear customer promise.
- **Criteria:** Load test passes, rollback completes within 15 minutes, and the customer sees the real workflow.
- **Options:** Full release, staging demo, or one-customer feature-flag pilot.
- **Decision:** Pilot only if both safety checks pass by Thursday; otherwise use the demo and move the pilot to next week.
- **Commit:** Product prepares the customer message, engineering owns the checks and flag, support owns the pilot contact, and the group reviews the evidence Thursday.

## Make it a habit

- Before a difficult meeting, write the decision in one sentence and ask the decision owner to confirm it.
- When someone states a demand, ask: "What problem does that solve for you?" Then repeat the answer until they agree you understood it.
- Bring one piece of evidence that could change your own mind, not only evidence that supports your preferred option.
- Before speaking in a high-stakes debate, write the strongest version of the other side's argument. If they would not recognize it, ask more questions.
- End every decision meeting with the choice, owner, actions, and review trigger in the shared record.
- Run a short retrospective after a hard decision: did the criteria predict the result, did people raise concerns early, and did the group follow through?

## Self-check

- [ ] Is the decision clear, with one owner and a deadline?
- [ ] Did we separate stated positions from underlying interests?
- [ ] Did we agree on evidence and limits before choosing?
- [ ] Did we create more than one meaningful option?
- [ ] Did people have a safe way to raise a concern?
- [ ] Is the decision, reasoning, action ownership, and review trigger written down?
- [ ] Are we committing to the chosen option unless new material evidence appears?

## Sources

- [Getting to Yes and principled negotiation](https://en.wikipedia.org/wiki/Getting_to_Yes)
- [Atlassian: Sparring](https://www.atlassian.com/team-playbook/plays/sparring)
- [Amazon: Have Backbone; Disagree and Commit](https://www.amazon.jobs/content/en/our-workplace/leadership-principles)
- [Google SRE: Postmortem Culture](https://sre.google/workbook/postmortem-culture/)
