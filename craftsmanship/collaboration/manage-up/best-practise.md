# Manage Up - Best Practise

## Pattern: the Promotion Evidence Loop

- **Read the bar.** Get the current and next-level expectations. Write the two or three observable behaviors or outcomes you need to demonstrate; ask your manager to correct your reading.
- **Choose one meaningful problem.** Find work that matters to customers, the business, or the engineering organization and has enough scope to show the target behavior. For Mai, this is failed-payment recovery, not “write a retry service.”
- **Make a before snapshot.** Record the problem, baseline, people affected, constraints, and decision you are accountable for. Mai records the 18% support-ticket rate and the missing retry visibility.
- **Keep an evidence log.** After key moments, add a few lines: context, your role, decision or action, result, collaborators, and a link to proof. Include kind feedback and a lesson from work that did not go as planned.
- **Write one impact story.** Use **Context → Action → Result → Learning → Next ask**. Mai explains the renewal problem, her cross-team leadership and technical decisions, the ticket-rate change, what the rollout taught her, and the question she needs answered about staff readiness.
- **Share on a calm cadence.** Use a brief weekly or biweekly update for important work and reserve part of a regular one-on-one for growth. Bring decisions, risks, results, and one clear ask—not a diary of tasks.
- **Get feedback and change course.** Ask the manager and close partners what the story proves and what is still missing. Turn one gap into a next experiment, then repeat the loop.

## Start with this template

```text
Target level and expected behavior: [...]
Problem and baseline: [...]
Why it matters: [...]

My role:
- I owned: [...]
- I influenced or enabled: [...]
- Partners and their contributions: [...]

Action and decision: [...]
Result: [metric, customer/team result, or risk reduced]
Evidence: [dashboard, design note, feedback, release note]
Learning: [...]
Next ask: [specific feedback, decision, or opportunity]
```

## Use it for failed-payment recovery

- **Read the bar:** Mai and her manager agree that she needs to demonstrate cross-team technical leadership and a durable result, not just deliver more backend code.
- **Make the snapshot:** Renewal-failure tickets are 18%; support has no retry-state view; payment retries must not double-charge customers.
- **Keep the evidence:** Mai stores the decision record, rollout plan, baseline and post-release dashboard, support feedback, and notes showing how Linh and Arjun took ownership of parts of the system.
- **Tell the story:** “I led recovery across payments and support; we cut ticket rate to 7%; support can explain each state; I set up ownership beyond myself.”
- **Make the next ask:** “What specific staff-level behavior is still unproven, and what upcoming problem is a good place to show it?”

## Make it a habit

- Keep one short, private evidence note per meaningful project; update it after a decision, release, incident, or partner feedback.
- Before a one-on-one, choose one of four asks: clarify expectations, remove a blocker, review an impact story, or choose a growth opportunity.
- Send a project update only when it changes a decision, risk, result, or needed support. Put the outcome before implementation detail.
- Credit people by name when their work changed the result. This makes your leadership and judgment more believable.
- Ask for feedback close to the event: after a design review, release, facilitation, or cross-team decision. Specific examples are more useful than a year-end memory.
- Once per quarter, compare your evidence with the target-level expectations. Keep the strongest examples, name the gap, and agree on the next smallest chance to close it.
- If results are weak, record the learning instead of hiding the project. Good judgment includes noticing that a plan did not work and changing it.

## Self-check

- [ ] Do I know the written expectations for my next level, not just its title?
- [ ] Can I explain the customer, business, or engineering problem before I describe the feature?
- [ ] Does my evidence show my role, partners' roles, and an observable result?
- [ ] Have I asked for one specific piece of feedback or support recently?
- [ ] Could my manager accurately repeat my impact story in a review discussion?
- [ ] Am I showing useful work and decisions rather than broadcasting every task?
- [ ] Do I have a concrete next opportunity to close the most important gap?

## Sources

- [Staff Engineer: Being visible](https://staffeng.com/guides/being-visible/)
- [Staff Engineer: Find your sponsor](https://staffeng.com/guides/find-your-sponsor/)
- [Atlassian: 7 tips for better 1-on-1 meetings](https://www.atlassian.com/blog/teamwork/1-on-1-meeting-tips)
- [Atlassian: Career development plan](https://www.atlassian.com/software/confluence/templates/career-development-plan)
