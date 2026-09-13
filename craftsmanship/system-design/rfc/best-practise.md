# RFC — Best Practise

Use the **PROPOSE loop** as a small, repeatable practice: **Pin** the problem, **Ring-fence** scope, **Offer** options, **Propose** one, **Outline** safety, **Seek** comments, and **End** with a decision.

## Start with the decision, not the document

- **Write one sentence:** “We need to decide whether to move CSV invitations from a synchronous request to an asynchronous import job.”
- **Name why now:** a product deadline, repeated support issue, public API change, operational risk, or a cost that will otherwise grow.
- **Check the threshold:** use the RFC when the choice crosses team or system boundaries, changes a lasting contract, or will be hard to reverse. Use a short ticket and code review for a local, reversible change.
- **Find the decision owner:** they do not have to author the RFC, but they must be clear about who closes the decision.
- **Find the affected reviewers:** product, security, operations, API owners, and the team that will maintain the new path.

## Use this short RFC template

Copy this shape before adding detail. It follows the useful parts of the LLVM, Rust, and Kubernetes proposal templates without requiring their full process.

```md
# <Decision, not a technology name>

Status: Draft | Accepted | Declined | Superseded
Owner: <person or team>
Decision needed by: <date>

## Summary
<One-sentence recommendation and expected outcome.>

## Problem and evidence
<Who is affected, what happens now, and why it matters.>

## Goals / non-goals / constraints
- Goal:
- Non-goal:
- Constraint:

## Options considered
| Option | Benefits | Costs and risks | Why choose or reject |

## Recommendation and design
<Data flow, interfaces, state changes, failure behavior, affected systems.>

## Safety plan
- Tests:
- Measures and alerts:
- Rollout:
- Rollback:

## Open questions and requested comments
- <Reviewer or role>: <specific question>

## Decision log
| Date | Decision or feedback | Response / change |
```

## Run the review deliberately

- **Draft early and keep it incomplete on purpose.** Publish when the problem, constraints, and viable options are clear; questions in the document invite useful help before the direction hardens.
- **Send it to people by role, not only title.** The service owner sees integration risks; support sees the user failure path; security sees data handling; SRE sees operation and rollback; product checks the user promise.
- **Ask a decision-shaped question.** “Should a partial CSV import invite valid rows?” gets better feedback than “Please review.”
- **Give reviewers time and a deadline.** State when a decision is needed, then follow up rather than reading no response as agreement.
- **Update the top of the RFC as discussion changes it.** Keep a small decision log so a new reviewer can see what changed and why without reading every comment. This mirrors LLVM's advice to incorporate relevant feedback visibly.
- **Make the decision explicit.** Record accepted, declined, or needs-revision; identify the owner and next action. An RFC left as “draft” after a meeting is an unresolved decision.

## Prove the proposal can live in production

- **List the unhappy paths.** For the import job: invalid rows, a worker retry, duplicate rows, object-storage denial, a user who leaves the page, a queue backlog, and a cancellation request.
- **Name proof before implementation.** Unit tests for parsing/idempotency, integration tests for the worker and email provider, and end-to-end tests for the administrator's status screen.
- **Choose signals with thresholds.** Track queue delay, completion rate, failed-row rate, worker error rate, and duplicate-email count. Say which signal pauses rollout or triggers rollback.
- **Roll out in steps.** Start with internal accounts, then a small opt-in group, then the wider audience. Use a feature flag if the path can be disabled safely.
- **Describe recovery in user terms.** If a job fails, the admin sees why, can retry safely, and support can find the import record. Do not write only “rollback available.”

## Keep the scope useful

- **One RFC, one main decision.** The CSV import RFC can decide sync versus async processing; a new cross-region storage design deserves its own proposal.
- **Put future ideas in non-goals or a follow-up.** They stay visible without blocking the decision in front of the team.
- **Keep implementation incremental.** Split accepted work into reviewable pull requests: import record and storage, worker processing, status UI, then staged rollout. This follows LLVM's recommendation to implement finalized RFCs in incremental changes.
- **Reopen only for a material change.** A renamed endpoint can go in the decision log; a new external webhook, data-retention policy, or operating-cost profile needs renewed review.

## Self-check before asking for approval

- [ ] Can a reviewer name the problem without hearing me explain it live?
- [ ] Are goals, non-goals, constraints, and affected systems visible?
- [ ] Did I show real alternatives and why the recommendation wins?
- [ ] Is the design detailed enough to test its interactions and failure cases?
- [ ] Did I ask each needed reviewer a concrete question?
- [ ] Are tests, signals, rollout, rollback, and ownership stated?
- [ ] Is the decision owner and decision date clear?
- [ ] Can someone see which feedback changed the proposal?
- [ ] If the chosen design changes materially later, is there a clear path to reopen it?

## Sources

- [LLVM: Request For Comment process](https://llvm.org/docs/RFCProcess.html)
- [Rust: RFC template](https://github.com/rust-lang/rfcs/blob/master/0000-template.md)
- [Kubernetes: KEP template](https://github.com/kubernetes/enhancements/blob/master/keps/NNNN-kep-template/README.md)
