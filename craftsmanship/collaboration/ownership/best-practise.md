# Ownership - Best Practise

## Pattern: the Outcome Owner Loop

- **Frame.** Write one sentence for the outcome, boundary, and proof of success. Start with the user or system result, not the first task someone suggested.
- **Map.** Name the Driver, one Approver for each decision, the Contributors, and the Informed people. Use the [DACI roles](https://www.atlassian.com/team-playbook/plays/daci) only where a real decision or handoff needs clarity.
- **Run.** Keep one short record of facts, risks, decisions, actions, owners, and the next update time. Each action needs a clear finish line.
- **Close.** Verify the outcome with evidence, tell affected people, and keep prevention work visible until it is done.

## Start with this template

```text
Outcome: [The user or system result we need]
Boundary: [What is not part of this work]
Proof: [The signal that shows the outcome is safe]

Driver: [Keeps the work moving]
Approver: [Makes the next decision]
Contributors: [Bring needed knowledge or do a task]
Informed: [Need the result]

Current facts: [What we know]
Decision needed: [Question, owner, and deadline]
Actions: [Action | owner | due time | proof of done]
Risk and next update: [What could change and when people will hear again]
```

## Use it in the duplicate-charge example

- **Frame:** "Stop new duplicate charges today; identify affected customers; re-enable checkout only after the safe-path test passes."
- **Map:** You drive the response; the incident lead approves rollback; payments, QA, and support contribute; product and support leads are informed.
- **Run:** Keep the rollback decision, customer list, test result, and idempotency-key action in one place with named owners.
- **Close:** Confirm alert volume is normal, customer remediation has started, and the prevention item has a trackable end state.

## Make it a habit

- Before accepting cross-team work, ask: "What result am I helping own, and how will we know it is done?"
- Before a meeting, write the decision needed and name the person who can make it. Do not invite people just because they are nearby.
- After each material update, replace stale facts and record what changed. A current short record is more useful than a perfect long one.
- At handoff, ask the new owner to repeat the outcome, open actions, risks, and next update time. Do not call the handoff done until they accept it.
- After an incident or launch, review the actions for clear owners, priorities, and proof of completion. Google SRE notes that a postmortem without follow-through is indistinguishable to users from no postmortem at all.

## Self-check

- [ ] Is the outcome clear enough that a teammate can repeat it?
- [ ] Is there one Driver and one Approver for each decision?
- [ ] Are contributors asked for knowledge or work they can actually provide?
- [ ] Does every action have one owner, a due time, and proof of done?
- [ ] Are affected people informed without needing to search for updates?
- [ ] Did we verify the immediate result and assign any prevention work?
- [ ] If the work moved, did the new owner explicitly accept it?

## Sources

- [Atlassian: DACI decision-making framework](https://www.atlassian.com/team-playbook/plays/daci)
- [Atlassian: Roles and Responsibilities](https://www.atlassian.com/team-playbook/plays/roles-and-responsibilities)
- [Google SRE: Postmortem Culture](https://sre.google/workbook/postmortem-culture/)
