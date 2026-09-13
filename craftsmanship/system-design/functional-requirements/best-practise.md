# Functional Requirements — Best Practise

- **Run this routine before a request becomes code:** the **Need-to-Behavior Loop**.
- **Aim for shared current understanding, not a perfect specification:** “What should this product do for this person in this situation?”

## The loop, ready to use

- **1. Capture the need.** Record the request in a ticket and link its evidence: support case, design, product decision, customer quote, metric, or policy.
  - Write: “Customers need self-service cancellation because support receives requests after mistaken orders.”
  - Do not write a design or estimate as if this sentence were already complete.

- **2. Name the actor and goal.** State who acts, what they want to accomplish, and why.
  - Write: “As a customer with a paid, unshipped order, I want to cancel it myself so that I can correct a mistake without waiting for support.”
  - Check: if you cannot say why the actor needs it, go back to the source. GOV.UK notes that the goal helps decide whether a user need has been met ([GOV.UK](https://www.gov.uk/service-manual/agile-delivery/writing-user-stories)).

- **3. Walk the workflow.** Ask someone close to the work to show the current path, then write the path in simple steps.
  - Start state: the order is paid and in `processing`.
  - Action: the customer chooses **Cancel order**, gives a reason, and confirms.
  - Result: the order is cancelled, fulfillment stops, and the customer sees the refund state.
  - Alternate state: an order handed to a carrier has no cancellation action and points to the supported return/contact path.
  - Repeated action: a second request shows the first result and does not create a second refund request.

- **4. Turn uncertainty into decisions.** List every rule you cannot safely infer, its owner, and its deadline.
  - “Can a customer cancel only one item?” — Product owner decides; not in this slice.
  - “What if refund creation fails?” — Payments and support decide the visible status and follow-up route.
  - “When is an order handed to a carrier?” — Fulfillment owner confirms the state transition.

- **5. Write observable confirmation.** Put the result into acceptance criteria before implementation begins.
  - It is done when an eligible customer can cancel their own order.
  - It is done when cancellation records the reason, stops fulfillment, and shows the cancellation/refund state.
  - It is done when an ineligible order directs the customer to the correct next step.
  - It is done when repeat submission leaves one cancellation and one refund request.

- **6. Confirm, build, and update.** Ask the product owner, designer, tester, and affected team to review only the behavior they own. Link tests and pull-request notes to those criteria. If a rule changes, update the ticket and explain why.

## A ticket template that stays useful

```md
## Need
Source and evidence:
Actor:
Goal:

## Behavior
Start state:
Action:
Expected result:
Alternate or failure paths:

## Rules and scope
Business rules:
In scope:
Out of scope:
Open questions, owner, and decision date:

## Confirmation
Acceptance criteria:
Links to design, policy, support evidence, and tests:
```

Keep it short. A backlog item can begin as only a title and gather detail as the team refines it; Microsoft explicitly describes adding details later and refining requirements over time ([Microsoft Learn](https://learn.microsoft.com/en-us/azure/devops/cross-service/manage-requirements?tabs=agile-process&view=azure-devops)).

## Questions that uncover the right behavior

- **Need:** What problem happens today? Who reported it? What evidence do we have?
- **Actor:** Who performs the action, who else is affected, and who is not allowed to do it?
- **Trigger:** What must be true before the action is available?
- **Normal path:** What does the actor do, and what do they see or receive afterward?
- **State changes:** Which records, permissions, inventory, notifications, or external services must change from the user’s point of view?
- **Alternates:** What happens when the action is too late, repeated, invalid, denied, or only partly completed?
- **Rules:** Which business or policy rule chooses between those outcomes? Who can confirm it?
- **Boundary:** What are we not solving in this slice, and where does that need go next?
- **Proof:** What could a tester, product owner, or customer observe to say this is done?

## Put the loop into daily work

- **New ticket:** spend five minutes capturing source, actor, goal, and one open question before it disappears into the backlog.
- **Refinement:** share a short workflow and ask each affected person to correct it. Let product answer value and policy, design answer interaction, QA answer observable cases, and dependent teams answer their state changes.
- **Estimation:** refuse false precision. If an unknown rule could change the path, record it and get the answer before committing a date.
- **Implementation:** treat a newly discovered rule as a requirement question, not a private code decision. Post the proposed behavior and get confirmation.
- **Pull request:** include the story and changed acceptance criteria in the description; reviewers can then check product behavior as well as code quality.
- **Release and support:** compare real tickets and behavior against the agreed criteria. Add a new scenario when reality exposes a missing path.

## Ready-to-start checklist

- [ ] The ticket links to the request or evidence that created it.
- [ ] The actor, action, and goal are understandable without meeting the author.
- [ ] The normal path has a visible start and end.
- [ ] Alternate paths cover every important state, permission, or external result that changes behavior.
- [ ] Every business rule has a source or a named decision owner.
- [ ] In-scope and out-of-scope work are explicit.
- [ ] Functional outcomes are separate from performance, reliability, security, privacy, and other quality targets.
- [ ] Acceptance criteria describe what a person can observe, not how the code is built.
- [ ] The people who own the decision have confirmed the behavior.
- [ ] Tests, release notes, and support guidance can link back to the same current record.

## Signs the habit is working

- You ask for a workflow or example before proposing code.
- Product and engineering disagree early in a ticket, then agree before implementation instead of during acceptance testing.
- A tester can create acceptance tests without guessing what words like “allowed,” “recent,” or “complete” mean.
- Scope changes appear as explicit decisions, not surprise tasks late in a sprint.
- Support can explain why a user sees a result because the rule was documented and confirmed.

## Sources

- [GOV.UK — Writing user stories](https://www.gov.uk/service-manual/agile-delivery/writing-user-stories)
- [Microsoft Learn — Requirements Management for Agile Teams](https://learn.microsoft.com/en-us/azure/devops/cross-service/manage-requirements?tabs=agile-process&view=azure-devops)
- [Atlassian — User stories and the 3 C’s](https://www.atlassian.com/agile/project-management/user-stories)
