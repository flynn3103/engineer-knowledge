# Functional Requirements — Mistake

- **What this gives you:** a shared target for code, tests, and release decisions when product behavior is unclear or changing.
- **What it does not replace:** a quality target, technical design, user research, or a business decision that nobody has made yet.
- **A useful check:** Atlassian’s **Card, Conversation, Confirmation** means the short written story starts the work, conversation fills in the meaning, and acceptance criteria confirm when it is complete ([Atlassian](https://www.atlassian.com/agile/project-management/user-stories)). Most requirement mistakes happen when a team keeps only one of those three.

## Common mistakes

- **Treating the raw ticket as the requirement.** “Let customers cancel an order” has no clear eligibility, outcome, or boundary, so each person fills in gaps differently.
  - Why it hurts: engineering may build a button that policy, fulfillment, or support cannot safely honor.
  - Fix: retain the raw request as evidence, then rewrite it as an actor, goal, rules, paths, and acceptance criteria.

- **Starting with a screen or implementation choice.** “Add a cancel endpoint and a modal” decides the shape before the user problem is clear.
  - Why it hurts: a polished solution can fail to handle orders that already shipped, refunds that are pending, or a customer who repeats the action.
  - Fix: ask “who needs what, in which state, and what must they observe afterward?” before discussing UI or code.

- **Writing only the happy path.** The customer cancels a processing order and everything succeeds; the requirement says nothing about a shipped order, a duplicate click, or a refund that cannot be completed yet.
  - Why it hurts: the omitted case becomes an accidental product rule discovered by users or support.
  - Fix: walk the primary path plus every point where the actor, state, permission, or external result changes the outcome.

- **Hiding rules inside vague words.** “Allow recent orders to be cancelled” leaves “recent” and “allowed” open to interpretation.
  - Why it hurts: tests cannot tell which interpretation is right, and support cannot explain the behavior.
  - Fix: name the state, condition, owner, and result: for example, “paid orders in `processing` are eligible; orders handed to a carrier use the return path.”

- **Mixing what with how.** “Use a queue to cancel the order” is an implementation decision, not a functional requirement.
  - Why it hurts: it locks a solution before the team has agreed on the customer-visible result, and it makes later design changes look like requirement changes.
  - Fix: state the outcome first: “the cancellation stops fulfillment and records a refund request.” Put technical choices in design work.

- **Smuggling a quality target into functional scope.** “Cancellation must return in 200 ms” is important, but it says how well the service operates rather than what it does.
  - Why it hurts: the team cannot see which discussion is about product behavior and which is about performance, reliability, security, or cost.
  - Fix: link a separate non-functional requirement to the same story when needed; keep the cancellation behavior and its quality target distinct.

- **Leaving scope edges unsaid.** Full-order cancellation, partial item cancellation, cash-on-delivery orders, and post-shipping returns are treated as one request.
  - Why it hurts: estimates hide work, a sprint grows while it is underway, and users receive an inconsistent first release.
  - Fix: write “in scope,” “out of scope,” and “next decision” in the ticket. A smaller honest slice is safer than an implied promise.

- **Recording an answer without its source or decision owner.** Someone says, “we always refund immediately,” and the claim becomes code.
  - Why it hurts: nobody can tell whether the rule came from policy, a product choice, an old workaround, or one person’s guess.
  - Fix: link the support case, policy, design, or meeting note; mark who confirms the rule and when it changed.

- **Waiting until after coding to confirm meaning.** The developer shows a completed feature and asks whether it is correct.
  - Why it hurts: disagreement arrives at the most expensive point, when UI, tests, and dependent systems already reflect an assumption.
  - Fix: circulate the short behavior list before implementation. IIBA’s confirmation step specifically checks captured information for accuracy, consistency, gaps, and shared understanding ([IIBA Core Standard](https://www.iiba.org/globalassets/standards-and-resources/core-standard/iiba-core-standard.pdf)).

- **Making a long document the only way to participate.** A large specification full of internal language asks busy product, support, or operations partners to decode it.
  - Why it hurts: the people with the best evidence do not confirm it, and the team mistakes silence for agreement.
  - Fix: adapt the artifact to the reader: a short ticket, order-state sketch, examples, and a focused question often get a better answer than a long technical document.

- **Treating acceptance criteria as a final paperwork step.** Criteria are copied from the happy path after development is nearly done.
  - Why it hurts: “done” becomes a feeling, not a result the product owner and tester can check.
  - Fix: agree on observable conditions before coding. Microsoft recommends defining conditions for done before implementation so expectations align and acceptance testing has a basis ([Microsoft Learn](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/scrum-process-workflow?view=azure-devops)).

## Quick judgment check

- **Use this practice heavily** when a request changes user behavior, business rules, permissions, state transitions, or an external integration.
- **Use a lighter version** when fixing a clear defect with known expected behavior; still state the reproducible behavior and expected result.
- **Bring in another practice** when the unanswered question is about quality, architecture, legal policy, pricing, or user research rather than product behavior alone.

## Sources

- [Atlassian — User stories and the 3 C’s](https://www.atlassian.com/agile/project-management/user-stories)
- [IIBA Core Standard — Confirm Elicitation Results](https://www.iiba.org/globalassets/standards-and-resources/core-standard/iiba-core-standard.pdf)
- [Microsoft Learn — Scrum work items and acceptance criteria](https://learn.microsoft.com/en-us/azure/devops/boards/work-items/guidance/scrum-process-workflow?view=azure-devops)

Continue to [Best Practise](best-practise.md).
