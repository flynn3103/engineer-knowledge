# Elicitation - Best Practise

## Pattern: the Need-to-Rule Loop

- **Frame the outcome.** Write the person affected, their goal, current pain, and the proof that the change helped. Do this before discussing components or screens.
- **Map the evidence.** Name the people, documents, data, systems, and real cases that can answer the next question. Use an interview, observation, document review, prototype, or experiment that fits the uncertainty.
- **Walk one real case.** Follow the current path from trigger to result. Ask what the person does, sees, decides, and hands to someone else.
- **Name the rules.** Write allowed cases, blocked cases, actors, data needed, timing, and effects on other people or systems.
- **Show back the model.** Turn the findings into a short scenario, table, flow, or acceptance examples. Ask the people closest to the work to correct it.
- **Record open assumptions.** For each unknown, state who will answer it, how, and by when. Do not hide uncertainty inside a confident requirement.
- **Learn again.** Recheck the model when a prototype, build, test, or launch exposes a new detail.

## Start with this template

```text
Outcome: [Who needs what result, and why?]
Current path: [What happens today in one real case?]
Evidence: [People, policy, data, system, or observation to consult]

Rules:
- Allowed when: [...]
- Blocked when: [...]
- Actor and permission: [...]
- Data and timing: [...]
- Effect on other people or systems: [...]

Proof of success: [What a user or team can observe]
Open assumptions: [Unknown | owner | how to check | by when]
Confirmation: [Who reviewed the summary and what changed]
```

## Use it for order cancellation

- **Frame:** Customers need to correct a mistaken order without a support ticket; support needs a clear, safe answer.
- **Map:** Ask a support specialist about recent cancellations, inspect warehouse status changes, read the refund policy, and check payment-provider behavior.
- **Walk:** Follow one paid order from checkout through fulfilment. Mark where a customer can act and where the warehouse has taken over.
- **Name:** Allow self-service cancellation only before picking; reject later requests with the reason and the support route; start the applicable refund workflow and log the action.
- **Show back:** Give product, support, warehouse, and payments a short table of status, allowed action, customer message, and system effect.
- **Learn:** If the payment provider cannot instantly reverse a method, add the real refund state and customer expectation before release.

## Make it a habit

- Before estimating a request, ask someone to state the user outcome and show one real example.
- Replace “should” and “usually” in a requirement with the condition that makes the statement true.
- End each discovery conversation with: “What did I miss, and who else would see this differently?”
- Keep a small list of assumptions in the ticket or design note. Delete an assumption only when evidence confirms it.
- Turn every important rule into at least one allowed example and one blocked example. These examples become useful review questions and test cases.
- When a bug or support ticket appears, ask whether it revealed a missing rule, a missing stakeholder, or an untested real-world path; feed the answer into the next elicitation loop.

## Self-check

- [ ] Can we state the user or business outcome without naming a feature?
- [ ] Did we use evidence beyond one person's opinion?
- [ ] Did we walk at least one real current case?
- [ ] Are allowed and blocked cases clear enough for a teammate to test?
- [ ] Did people closest to the work confirm or correct the summary?
- [ ] Are open assumptions visible, owned, and time-bound?
- [ ] Do we have a plan to learn from the first build, test, or release?

## Sources

- [IIBA: Elicitation and Collaboration](https://www.iiba.org/globalassets/standards-and-resources/core-standard/iiba-core-standard.pdf)
- [IIBA: Prepare for Elicitation](https://www.iiba.org/globalassets/business-analysis-resources/the-business-analysis-standard/files/the-business-analysis-standard.pdf)
- [IIBA: Requirements and Designs](https://www.iiba.org/knowledgehub/the-business-analysis-standard/4-implementing-business-analysis/4-4-understanding-requirements-and-designs/)
- [IIBA: When Stakeholders Can't Define Requirements](https://www.iiba.org/business-analysis-blogs/how-to-elicit-requirements-when-stakeholders-cant-define-what-they-want/)
