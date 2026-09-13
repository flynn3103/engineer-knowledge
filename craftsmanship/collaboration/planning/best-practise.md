# Planning - Best Practise

## Pattern: the Annual-to-Weekly Planning Loop

- **Set the annual direction.** Name the few outcomes worth sustained investment, the evidence they should change, and the trade-offs they require. Do not turn this layer into a ticket list.
- **Translate it into a quarterly OKR.** Write 1–3 qualitative objectives. Give each objective 3–5 measurable, verifiable key results with a current value, target value, and owner.
- **Run initial team planning.** Agree on the intended outcome, in-scope and out-of-scope work, capacity, roles, dependencies, risks, and the first milestone. Keep the plan rough where evidence is weak.
- **Create a WBS.** Break the chosen scope into deliverables or phases, then into work packages. Every package needs an owner, a clear result, a dependency check, and a way to know it is complete.
- **Set the cadence.** Use a weekly delivery check for milestones, risks, and blockers; a monthly OKR check for metric progress; and a quarterly review to learn, reset priorities, and make the next plan.
- **Change deliberately.** When evidence says the plan is off track, record the decision: continue, re-scope, add capacity, change approach, or stop. Update the plan so people do not follow an obsolete promise.

## Start with this template

```text
Yearly direction: [The durable user or business outcome]
Not this year: [Explicit trade-offs]

Quarterly objective: [Qualitative change we want]
Key results:
- [Metric] from [current] to [target] — owner: [...]
- [Metric] from [current] to [target] — owner: [...]

Initial team plan:
- In scope / out of scope: [...]
- Capacity and people needed: [...]
- Risks, assumptions, and dependencies: [...]
- First milestone and proof: [...]

Work breakdown:
- Deliverable or phase: [result]
  - Work package: [owner | dependency | proof of done]

Cadence:
- Weekly: [milestone, blocker, decision]
- Monthly: [KR value, trend, forecast, adjustment]
- Quarterly: [learn, score, stop/start/continue]
```

## Use it for first-time reporting

- **Yearly direction:** Make new customers successful sooner; do not pursue a fully custom report builder this year.
- **Quarterly OKR:** Improve first-time reporting. Track time to first saved report, 14-day successful-report rate, and report-creation failure rate.
- **Initial plan:** One default report template and a guided path are in scope. New data-source integrations are out. Product, analytics, design, support, and platform are needed. The first milestone is a working internal prototype with event tracking.
- **WBS:** Journey research → default template definition → guided experience → event instrumentation → error handling → cohort release → support guide and review. Each work package gets one owner and any dependency.
- **Cadence:** Each week, inspect prototype/release milestones, blocked dependencies, and failure signals. Each month, compare the three key results with their expected milestones. At quarter end, decide whether to expand, fix the main drop-off, or stop the approach.

## Make it a habit

- At the start of annual planning, ask: “What would make us say this year mattered?” Keep only the answers that need sustained investment.
- Before accepting a key result, ask: “Could this be complete while the user is no better off?” If yes, it is probably an output, not a key result.
- In every kickoff, write one non-goal. It protects capacity when a reasonable but unrelated request arrives.
- Review the WBS with the people who build, operate, support, secure, and measure the change. Missing work is easiest to add before the first commitment.
- Give each key result a simple monthly milestone. It makes “off track” visible early enough to change something.
- End every tracking session with one of four outcomes: continue, adjust, escalate, or stop. A status meeting without a decision should be shorter or asynchronous.
- After the quarter, compare the plan, evidence, and result. Keep the lessons that improve the next estimate, breakdown, and cadence.

## Self-check

- [ ] Does the yearly direction state an outcome, not a collection of projects?
- [ ] Does every key result measure a verifiable change rather than feature delivery?
- [ ] Does the team know what is in scope, out of scope, and uncertain?
- [ ] Does every work package have an owner, dependency check, and proof of done?
- [ ] Are operation, support, measurement, and rollout work visible in the breakdown?
- [ ] Does the tracking cadence look at both delivery evidence and key-result progress?
- [ ] Can the team change or stop the plan when evidence warrants it?

## Sources

- [Atlassian: Objectives and Key Results](https://www.atlassian.com/team-playbook/plays/okrs)
- [Atlassian: Agile quarterly planning](https://www.atlassian.com/agile/agile-at-scale/long-term-agile-planning)
- [Atlassian: Quarterly planning](https://www.atlassian.com/work-management/strategic-planning/quarterly-planning)
- [Asana: Work Breakdown Structure](https://asana.com/resources/work-breakdown-structure)
