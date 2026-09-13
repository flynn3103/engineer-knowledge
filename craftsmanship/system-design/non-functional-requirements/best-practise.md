# Non-Functional Requirements — Best Practise

## The Quality-Risk Loop

- **1. Flag the change at refinement.** Run the loop when a ticket changes a user-facing wait, data flow, permission, dependency, retention rule, background job, release risk, or on-call responsibility.
- **2. Write one critical flow in plain language.** “An authorised account owner requests and receives their organisation's 90-day order export.” Keep it user-centred; an API or database is a dependency, not the outcome.
- **3. Run a short five-lens risk scan.** Ask the performance, reliability, security, privacy, and operability questions in [Problem](problem.md). Record unknowns with the person who can answer them instead of inventing a target.
- **4. Turn the important risks into quality cards.** Start with the smallest set that protects the critical flow. Google SRE recommends a small number of indicators for the functionality most important to customers, not a dashboard for everything ([source](https://sre.google/workbook/implementing-slos/)).
- **5. Attach evidence before coding.** Put each card in the ticket, design note, or acceptance criteria with its test, monitoring source, and owner. The requirement is incomplete if no one can show that it holds.
- **6. Verify in the delivery path.** Exercise the happy path and a relevant bad path: slow or overloaded work, dependency failure, unauthorised access, retention expiry, or an operator recovery step.
- **7. Observe and revisit.** Review the actual signal after release. Re-run the scan when the flow, data, policy, dependency, or incident history changes.

## Quality-card template

```text
Critical flow:
Risk and user impact:
Promise: For [actor and condition], [outcome] is true within [threshold/window].
Measure and source:
Evidence before release:
Owner and alert/runbook, if needed:
Decision date and review trigger:
```

## Filled cards for the export feature

- **Performance card:** For an authorised owner requesting a 90-day export at the agreed peak, the request is acknowledged within 2 seconds and the file is ready within 10 minutes. Measure the request and completion timestamps; verify with a representative large export; review after the first peak period.
- **Reliability card:** For eligible export jobs, at least 99.5% produce one complete file within 10 minutes in a rolling 30-day window. Measure successful completions against eligible requests; verify failure and retry behavior; the feature owner reviews breaches.
- **Security card:** A requester or downloader must be authorised for the organisation whose file they access. Verify with cross-organisation and expired-access tests; record denied access attempts according to the security policy; involve the security owner for the threat level and controls.
- **Privacy card:** The export contains only approved fields and is removed after the agreed retention period. Verify the schema and deletion behavior; link the data classification and policy decision; ask the privacy or legal owner when the product, jurisdiction, or data use requires it.
- **Operability card:** The team can see job state, completion delay, and failures by organisation, and a sustained failure signal has a named recipient and first recovery action. Verify the dashboard, alert route, and runbook in a safe environment.

The values are deliberately examples. The useful habit is the card shape: outcome first, then measurable threshold, evidence, and ownership. [Microsoft recommends deriving targets with business stakeholders and refining them with monitoring and testing](https://learn.microsoft.com/en-us/azure/well-architected/reliability/metrics); the number should therefore reflect the user and business cost, not a default copied from another service.

## Put the loop into daily work

- **Ticket refinement:** add the critical flow, five-lens scan, open questions, and accountable partners before sizing the work.
- **Design and PR review:** link each quality card to the chosen control and evidence. Ask, “Which promise does this code, test, dashboard, or runbook prove?”
- **Release review:** check the agreed signals, access and data checks, rollback or recovery route, alert owner, and support handoff in proportion to the risk.
- **Incident and support review:** turn the new fact into a changed card, test, monitor, or ownership rule. Do not only patch the symptom.
- **Privacy and security review:** trace requirement → control → verification evidence. NIST describes this kind of traceability between privacy requirements and controls, while OWASP recommends using verifiable security requirements and abuse cases across delivery ([NIST](https://www.nist.gov/privacy-framework/using-privacy-framework-11), [OWASP](https://top10.owasp.org/2025/0x03_2025-Establishing_a_Modern_Application_Security_Program/)).

## Self-check before calling the requirement ready

- [ ] Did we name the user flow and the people affected if it fails?
- [ ] Did we examine changed data, permissions, dependencies, and operating work?
- [ ] Did we ask all five lenses, and record what is deliberately out of scope?
- [ ] Is each important promise measurable with a threshold, a window, and a source?
- [ ] Did the right product, security, privacy, support, and operations owners answer their parts?
- [ ] Does each promise have evidence before release and an owner after release?
- [ ] Did we test one realistic failure or misuse path, not only the happy path?
- [ ] Is the requirement still true after the latest policy, dependency, or incident change?

## Sources behind the pattern

- [Google SRE, “Implementing SLOs”](https://sre.google/workbook/implementing-slos/) — user-centred indicators, measurable SLOs, and feedback from real signals.
- [Microsoft Well-Architected, “Defining reliability targets”](https://learn.microsoft.com/en-us/azure/well-architected/reliability/metrics) — business-flow targets, recovery measures, monitoring, and testing.
- [OWASP, “Establishing a Modern Application Security Program”](https://top10.owasp.org/2025/0x03_2025-Establishing_a_Modern_Application_Security_Program/) — security requirements, data flows, abuse cases, and operational security work.
- [NIST, “Using Privacy Framework 1.1”](https://www.nist.gov/privacy-framework/using-privacy-framework-11) — turning privacy risks and requirements into work across the delivery lifecycle.
