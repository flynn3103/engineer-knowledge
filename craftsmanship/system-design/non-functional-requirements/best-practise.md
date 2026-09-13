# Non-Functional Requirements — Best Practise

## The Quality-Risk Loop

- **1. Flag the change at refinement.** Run the loop when a ticket changes a user-facing wait, traffic or payload shape, data flow, permission, dependency, retention rule, background job, release risk, or on-call responsibility.
- **2. Write one critical flow in plain language.** “An authorised account owner requests and receives their organisation's 90-day order export.” Keep it user-centred; an API or database is a dependency, not the outcome.
- **3. Run a short five-lens risk scan.** Ask the performance, reliability, security, privacy, and operability questions in [Problem](problem.md). Record unknowns with the person who can answer them instead of inventing a target.
- **4. Add a sizing card when volume, payload, storage, retention, copies, or cost could change the requirement.** Use the smallest credible numbers and name their source. The goal is to expose a decision or a test target, not to predict an exact server count.
- **5. Turn the important risks into quality cards.** Start with the smallest set that protects the critical flow. Google SRE recommends a small number of indicators for the functionality most important to customers, not a dashboard for everything ([source](https://sre.google/workbook/implementing-slos/)).
- **6. Attach evidence before coding.** Put each card in the ticket, design note, or acceptance criteria with its test, monitoring source, and owner. The requirement is incomplete if no one can show that it holds.
- **7. Verify in the delivery path.** Exercise the happy path and a relevant bad path: slow or overloaded work, dependency failure, unauthorised access, retention expiry, or an operator recovery step. Run the sizing scenario as a representative load test when the risk is material.
- **8. Observe and revisit.** Review the actual signal after release. Re-run the scan when the flow, data, policy, dependency, demand shape, or incident history changes.

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

## Sizing-card template

```text
Critical flow and boundary:
Evidence source and date:
Busy-window demand: [events] in [minutes/seconds] = [peak RPS/QPS]
Operations: [create / read / poll / write / download], each with its own rate
Payload: [average or large expected bytes] in and out
In-flight work: [rate] × [average seconds]
Stored data: [items/day] × [size] × [retention] × [stored copies]
Capacity / quota to check:
Rough cost: [usage] × [current rate], region and calculator date included
Assumptions, uncertainty, and decision owner:
Evidence before release: [load test / production metric / quota check]
Review trigger:
```

Use the same unit within one line (`MiB` with `MiB/s`, or `GB` with `GB/s`) and round aggressively. A clear `600 exports in one minute` is more useful than false precision such as `10.000 RPS`.

## Filled sizing card for the export feature

- **Critical flow and demand:** at month end, 600 account owners request an export within one minute, based on the named analytics query and support history. `600 ÷ 60 = 10 RPS` at the create-export endpoint.
- **Operations, not one total:** while up to 600 jobs run, a five-second polling interval can cause `600 ÷ 5 = 120 QPS` to the status endpoint. Estimate source reads, file writes, and downloads separately because they have different quotas and payloads.
- **Payload and bandwidth:** one large expected export is `100,000 rows × 0.5 KiB`, or roughly 50 MiB. To make 600 such files ready within ten minutes, the rough output target is `600 × 50 MiB ÷ 600 seconds = 50 MiB/s`; if all are downloaded in five minutes, outgoing data could reach 100 MiB/s.
- **Stored data and copies:** 1,200 exports a day, seven-day retention, and two stored copies means `1,200 × 50 MiB × 7 × 2 = 840,000 MiB`, about 820 GiB. Record an archival backup or a separate replica on its own line because it may have a different retention and price.
- **Cost and test:** use the current provider calculator for roughly 820 GiB of storage plus requests, worker time, transfer, backups, region, and copy count. Put the calculator date in the ticket. Verify the 600-export burst with representative data, then replace the assumptions with observed p95 file size, peak rate, and completion time.

[Google SRE's workbook uses this kind of arithmetic to sanity-check bandwidth and concurrent work, but says a load test is still necessary](https://sre.google/static/pdf/nalsd-workbook-letter.pdf). A sizing card is therefore a conversation record and a test plan—not a promise that rounded math has proved the system safe.

## Filled cards for the export feature

- **Performance card:** For an authorised owner requesting a 90-day export at the agreed peak, the request is acknowledged within 2 seconds and the file is ready within 10 minutes. Measure the request and completion timestamps; verify with the representative 600-export burst and a large file; review after the first peak period.
- **Reliability card:** For eligible export jobs, at least 99.5% produce one complete file within 10 minutes in a rolling 30-day window. Measure successful completions against eligible requests; verify failure and retry behavior; the feature owner reviews breaches.
- **Security card:** A requester or downloader must be authorised for the organisation whose file they access. Verify with cross-organisation and expired-access tests; record denied access attempts according to the security policy; involve the security owner for the threat level and controls.
- **Privacy card:** The export contains only approved fields and is removed after the agreed retention period. Verify the schema and deletion behavior; link the data classification and policy decision; ask the privacy or legal owner when the product, jurisdiction, or data use requires it.
- **Operability card:** The team can see job state, completion delay, and failures by organisation, and a sustained failure signal has a named recipient and first recovery action. Verify the dashboard, alert route, and runbook in a safe environment.

The values are deliberately examples. The useful habit is the card shape: outcome first, then measurable threshold, evidence, and ownership. [Microsoft recommends deriving targets with business stakeholders and refining them with monitoring and testing](https://learn.microsoft.com/en-us/azure/well-architected/reliability/metrics); the number should therefore reflect the user and business cost, not a default copied from another service.

## Put the loop into daily work

- **Ticket refinement:** add the critical flow, five-lens scan, sizing card when needed, open questions, and accountable partners before sizing the implementation work.
- **Design and PR review:** link each quality and sizing card to the chosen control and evidence. Ask, “Which promise or assumption does this code, test, dashboard, quota check, or runbook prove?”
- **Release review:** check the agreed signals, access and data checks, traffic and storage assumptions, rollback or recovery route, alert owner, and support handoff in proportion to the risk.
- **Incident and support review:** turn the new fact into a changed card, test, monitor, or ownership rule. Do not only patch the symptom.
- **Privacy and security review:** trace requirement → control → verification evidence. NIST describes this kind of traceability between privacy requirements and controls, while OWASP recommends using verifiable security requirements and abuse cases across delivery ([NIST](https://www.nist.gov/privacy-framework/using-privacy-framework-11), [OWASP](https://top10.owasp.org/2025/0x03_2025-Establishing_a_Modern_Application_Security_Program/)).

## Self-check before calling the requirement ready

- [ ] Did we name the user flow and the people affected if it fails?
- [ ] Did we examine changed data, permissions, dependencies, and operating work?
- [ ] Did we ask all five lenses, and record what is deliberately out of scope?
- [ ] If volume or data can change the outcome, did we calculate each meaningful operation's peak rate, payload bandwidth, retained storage, copies, and rough cost separately?
- [ ] Does each sizing number name its evidence source, busiest window, unit, assumption, and review trigger?
- [ ] Is each important promise measurable with a threshold, a window, and a source?
- [ ] Did the right product, security, privacy, support, and operations owners answer their parts?
- [ ] Does each promise have evidence before release and an owner after release?
- [ ] Did we test one realistic failure or misuse path, and the material sizing scenario, not only the happy path?
- [ ] Is the requirement still true after the latest policy, dependency, or incident change?

## Sources behind the pattern

- [Google SRE, “Implementing SLOs”](https://sre.google/workbook/implementing-slos/) — user-centred indicators, measurable SLOs, and feedback from real signals.
- [Microsoft Well-Architected, “Defining reliability targets”](https://learn.microsoft.com/en-us/azure/well-architected/reliability/metrics) — business-flow targets, recovery measures, monitoring, and testing.
- [OWASP, “Establishing a Modern Application Security Program”](https://top10.owasp.org/2025/0x03_2025-Establishing_a_Modern_Application_Security_Program/) — security requirements, data flows, abuse cases, and operational security work.
- [NIST, “Using Privacy Framework 1.1”](https://www.nist.gov/privacy-framework/using-privacy-framework-11) — turning privacy risks and requirements into work across the delivery lifecycle.
- [Google SRE, “Non-Abstract Large Scale Design Workbook”](https://sre.google/static/pdf/nalsd-workbook-letter.pdf) — back-of-the-envelope checks for bandwidth, concurrent work, bottlenecks, and why load testing still matters.
- [Google SRE, “SLO Implementation: Evernote and Home Depot”](https://sre.google/workbook/slo-engineering-case-studies/) — choosing between average, peak, and total traffic volume, and sizing for expected peaks.
- [Google Cloud Storage, “Best practices for media workloads”](https://docs.cloud.google.com/storage/docs/best-practices-media-workload?hl=en) — calculating origin QPS after cache hits and checking the rate at the real boundary.
- [Microsoft Learn, “Understanding Your Bill — Azure Cosmos DB”](https://learn.microsoft.com/en-us/azure/cosmos-db/understand-your-bill) — an example of separating storage and throughput cost, with replicated capacity multiplied by region.
