# Non-Functional Requirements — Mistake

## When the Quality-Risk Loop earns its cost

- **Use the full loop when a change touches a critical user journey, sensitive data, permissions, an external dependency, background work, or on-call ownership.** These are the places where a short ticket can hide a costly failure mode.
- **Use a lighter scan for a small, reversible change with no changed risk.** Write the reason it is low risk; “the feature is small” is not evidence that its data or access impact is small.
- **Do not treat the loop as legal, privacy, or security approval.** It exposes questions early; the accountable specialist or policy owner still makes the decision that needs their authority.

## Common mistakes

- **Writing “fast,” “secure,” or “highly available” as if they were requirements.** Nobody can tell if the promise was met, and each person silently supplies a different meaning. **Fix:** state the flow, condition, measure, threshold, time window, and owner—for example, “90% of eligible exports complete within 10 minutes over 30 days.”
- **Starting with a favourite solution.** “Add a queue” or “turn on encryption” can hide the user impact, make alternatives invisible, and create work the feature does not need. **Fix:** name the risk and desired outcome first; choose a control only after the requirement is clear.
- **Asking only the product manager.** Product may know the goal but not the data classification, support history, dependency limits, or on-call burden. **Fix:** bring in the people who own those facts early, with concrete questions about the changed flow.
- **Measuring an average for every customer and calling it a user promise.** A healthy average can hide the slow, failed, or high-value flow that users actually notice. **Fix:** measure the critical flow and choose a threshold that represents the affected user experience; Google SRE explicitly uses separate latency thresholds to expose the long tail in user wait time ([source](https://sre.google/workbook/implementing-slos/)).
- **Copying a cloud provider's SLA as the product requirement.** A provider agreement covers a defined slice of a service, not your code, configuration, dependencies, or user journey. **Fix:** treat vendor commitments as an input and define an end-to-end target that the team can measure; Microsoft cautions against using an SLA without understanding its coverage ([source](https://learn.microsoft.com/en-us/azure/well-architected/reliability/metrics)).
- **Treating security as a last-minute scan.** Access rules, data flows, and abuse cases become much harder to change after the feature shape is fixed. **Fix:** include protection needs, data-flow review, and at least one abuse case while the ticket is being clarified; OWASP recommends these activities throughout the development lifecycle ([source](https://top10.owasp.org/2025/0x03_2025-Establishing_a_Modern_Application_Security_Program/)).
- **Calling privacy “security with a different name.”** A feature can have strong access control and still collect too much data, retain it too long, or use it beyond the agreed purpose. **Fix:** trace the data life cycle, policy, legal requirements, and acceptable risk separately; NIST maps those privacy outcomes into planning, design, deployment, and operation ([source](https://www.nist.gov/privacy-framework/using-privacy-framework-11)).
- **Creating an alert without a useful action.** A noisy alert trains people to ignore it; an alert with no owner or runbook turns an incident into improvisation. **Fix:** name the symptom, threshold, recipient, urgency, and first safe action. Keep the human-facing signal simple and tied to a real failure.
- **Adding every control because the feature feels risky.** An enormous checklist delays delivery and makes the important risks harder to see. **Fix:** rank risks by affected flow, impact, likelihood, and policy; use a standard such as ASVS as a guide, not as an excuse to apply every control unchanged.
- **Leaving the requirement in the ticket after release.** Usage, policies, dependencies, and support evidence change. **Fix:** review the promises after rollout, an incident, a material dependency change, or a new data use; update the requirement and its evidence together.

Continue to [Best Practise](best-practise.md).
