# RFC — Mistake

Use an RFC for a decision with shared, lasting, or hard-to-reverse effects. Do not turn every local refactor into a committee document: a small, reversible change with one clear owner normally needs a ticket and normal code review instead.

LLVM reserves its process for **substantive** changes, which is a useful test: match the depth of the RFC to the cost of being wrong.

## Common mistakes

- **Starting with a preferred tool instead of a problem.** “Use a queue for CSV import” makes the review a debate about queues, while the real need—large imports without duplicate invitations—stays vague.
  - **Why it hurts:** reviewers cannot tell whether the proposal solves the right thing, or whether a simpler option would work.
  - **Fix:** open with the user/system pain, evidence, affected people, and what happens if the team does nothing.

- **Leaving goals and non-goals unstated.** A reviewer adds “also support Excel files” and another adds “make this a general import platform.”
  - **Why it hurts:** a one-feature proposal quietly becomes an open-ended program.
  - **Fix:** list the promised outcomes and the nearby work that is explicitly out of scope. The Kubernetes KEP template separates both for this reason.

- **Presenting only one option.** The RFC is really a request to approve work that has already been decided.
  - **Why it hurts:** feedback turns into taste or resistance, because nobody can compare cost, risk, and fit.
  - **Fix:** show the recommended option and at least one credible alternative, including “do nothing or defer” when it is genuinely possible. State why each loses or wins against the stated goals.

- **Making the design either too thin or too coded.** “Use an async worker” says too little; a 20-page class-by-class implementation plan says too much.
  - **Why it hurts:** the first hides interactions and failure cases; the second spends review time on code details that belong in pull requests.
  - **Fix:** explain data flow, interfaces, state changes, failure behavior, and affected systems—enough for a teammate to challenge the design, not enough to pre-write every function.

- **Asking “Any thoughts?” instead of asking for a review decision.** Important people skim the RFC but do not know what expertise to apply.
  - **Why it hurts:** silence looks like agreement, while privacy, operations, or product assumptions go unchecked.
  - **Fix:** name reviewers and put concrete questions beside their concerns: retention for security, queue thresholds for SRE, retry semantics for API consumers, and user promise for product.

- **Treating silence as approval.** No one comments because the proposal was missed, unclear, or has no obvious owner.
  - **Why it hurts:** implementation starts without a shared decision, then objections arrive after the cost has grown.
  - **Fix:** set a review window, ask the decision owner to state the outcome, and follow up with needed reviewers. LLVM treats low engagement as lack of consensus, not automatic acceptance.

- **Editing away feedback without a visible trail.** A reviewer cannot tell whether their concern changed the design or was simply ignored.
  - **Why it hurts:** the next discussion repeats the same question and people stop trusting the document.
  - **Fix:** keep a small decision log: concern, response, change made, and date. Update the main proposal so newcomers see the current shape, as LLVM recommends.

- **Skipping tests, monitoring, and recovery.** The async import works in a demo, but a stuck worker or bad rollout leaves an account unable to invite anyone.
  - **Why it hurts:** operational risk stays invisible until production is the test environment.
  - **Fix:** name the failure signals, test cases, rollout steps, rollback trigger, and owner before approval. Kubernetes includes these checks in its proposal template.

- **Writing an RFC after the decision is already fixed.** The team has built most of the import pipeline; the RFC is only asked to justify it.
  - **Why it hurts:** reviewers can only argue about sunk cost, not help shape the decision.
  - **Fix:** publish a rough draft once the problem and options are clear, before an irreversible implementation choice is made.

- **Keeping the RFC “accepted” after a material change.** The team later adds cross-region replication or changes from polling to externally delivered webhooks.
  - **Why it hurts:** the actual risk and affected people no longer match what reviewers approved.
  - **Fix:** amend minor details in the decision log; reopen discussion for a change that alters scope, safety, costs, or the chosen approach. LLVM likewise calls for a new RFC when a proposal changes materially.

## Sources

- [LLVM: Request For Comment process](https://llvm.org/docs/RFCProcess.html)
- [Rust: RFC template](https://github.com/rust-lang/rfcs/blob/master/0000-template.md)
- [Kubernetes: KEP template](https://github.com/kubernetes/enhancements/blob/master/keps/NNNN-kep-template/README.md)

Continue to [Best Practise](best-practise.md).
