# Testing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you build a golden-set regression suite for a prompt or agent behavior that catches a real regression on deploy — checking output *properties* rather than exact matches — and keep that suite from silently going stale?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — From Mocked Units to Real Behavior

The junior-level unit test mocks the model out entirely — it proves the deterministic code around the model call is correct, but it proves nothing about whether the *model's actual behavior* on realistic input is still correct. That's a different, harder question, and it needs a different kind of test: one that runs a fixed set of representative inputs through a real (or near-real) model and checks the output against defined properties.

This is a **golden set**: a fixed collection of representative inputs, each paired with a definition of what a correct-enough output looks like — not the exact text, but checkable properties of it. A golden-set suite is a regression suite in the ordinary sense — it exists to answer "did a change break something that used to work" — adapted for the fact that "used to work" can't mean "produced this exact string."

## Core Concept 2 — Choosing Golden-Set Inputs

An input set that doesn't represent real usage gives you false confidence: everything passes in CI, and the first regression a user hits is one your set never covered. Build the set from two sources:

- **A representative sample of real traffic.** Pull actual (anonymized, if needed) requests across the categories your feature actually handles, weighted roughly the way real traffic is weighted — if 60% of billing tickets are refund requests, refund requests should be roughly that share of your billing golden-set cases, not an even split across every category you can imagine.
- **Every input that has caused a real bug before.** When a prompt change or model update breaks something in production, the input that exposed it becomes a permanent golden-set case, with a property check that encodes exactly what went wrong. This is the single highest-value source of cases — it directly prevents the regression from recurring, and it's the difference between a golden set that only prevents *hypothetical* regressions and one that has already saved you at least once.

A workable starting size for one prompt or one agent behavior is 30–100 cases: enough to cover the input space's real categories and edge cases, small enough that a run finishes in a few minutes rather than an hour. Fewer than that and rare-but-real categories go uncovered; far more than that and the suite becomes too slow to run on every relevant PR, pushing it toward nightly-only (see `senior.md` for how that trade-off gets made deliberately rather than by accident).

## Core Concept 3 — Defining Pass/Fail as Property Checks

Exact-match string comparison fails here for the same reason it failed at junior level, at a larger scale: two runs of the same prompt against the same model can differ in wording while both being correct. Replace exact match with property checks:

| Property-check type | What it verifies | Example |
|---|---|---|
| Required field / pattern present | Output contains something it must contain | Response includes a case reference number matching `\bCASE-\d{6}\b` |
| Banned pattern absent | Output doesn't contain something it must never contain | Response contains no PII pattern, no competitor name, no unqualified financial guarantee |
| Structural validity | Output parses as the shape the caller expects | Output is valid JSON with required keys `{summary, severity, next_step}` |
| Similarity / rubric threshold | Output is "close enough" to a reference by some measured distance | Embedding similarity to a reference answer ≥ 0.80; LLM-as-judge rubric score ≥ 3 of 5 on faithfulness |
| Tool-call schema validity | If the model calls a tool, the call matches the declared schema | `issue_refund` called with a numeric `amount` and non-empty `reason` |

Most golden-set cases combine two or three of these rather than relying on one. A refund-request case might check: the tool called was `issue_refund` (structural), the `amount` argument is a positive number matching the amount mentioned in the ticket (required-field), and the response text contains no promise of a specific refund timeline the business hasn't committed to (banned pattern).

## Core Concept 4 — Running It: Real Model, Cheap Model, or Both

Running the full golden set against the most expensive, most capable model on every PR is accurate but slow and costly at scale. The workable pattern most teams land on:

- **On every PR that touches the prompt or agent logic**, run the golden set against a **cheaper or faster model** that's a reasonable stand-in for the production model. This catches most structural and required-field regressions quickly.
- **Nightly or before release**, run the same golden set against the **actual production model**, to catch anything the cheap stand-in couldn't reproduce (see `senior.md` for the full layered design).

Tools like [promptfoo](https://www.promptfoo.dev/) and [DeepEval](https://github.com/confident-ai/deepeval) exist specifically to run this pattern — define a set of test cases and assertions once, run them against whichever model backend is configured for that CI stage, and get a pass/fail plus a report per case rather than hand-rolling the harness.

## Core Concept 5 — A Regression the Suite Actually Caught

A concrete shape this takes in practice: a prompt template for a billing assistant includes a line requiring the response to state the refund policy's 14-day processing window whenever a refund is mentioned. An engineer editing the template for tone cleans up the wording and, in the process, deletes that line — a change that reads as harmless in the diff, because nothing else in the prompt looks wrong.

A golden-set case built from a past incident — "response mentions a refund" → property check: "response contains a processing-window disclaimer matching a known pattern" — fails on this change, because the rewritten prompt no longer instructs the model to include that line and the model, unprompted, doesn't include it either. The suite doesn't need to know *why* the disclaimer disappeared; it only needs the property check that was written when this exact failure happened the first time. Without that case, this ships, and the next signal is a support escalation instead of a failed CI run.

## Core Concept 6 — How a Golden Set Goes Stale

A golden set is a piece of code with its own maintenance burden, and it decays in two distinct ways that need two distinct fixes:

1. **Inputs stop representing real traffic.** The product adds a new ticket category, or user behavior shifts, and the golden set — frozen at whenever it was built — never picks up the new pattern. Nothing in CI ever fails, because nothing in the set exercises the new behavior; the first sign of trouble is a production complaint about a case type CI never tested. **Fix:** resample from real traffic on a schedule (quarterly is a reasonable default for a moderately active feature), not only when someone remembers to.
2. **Expected properties never get updated after an intentional behavior change.** The team decides to shorten refund-processing language, updates the prompt on purpose, and now several golden-set cases fail — correctly, because the old property check encoded the old required behavior. If the fix is "just update the assertion to match whatever the new output is" without asking whether the new output is actually still correct, the suite stops meaning anything: it now only confirms that the code matches itself, not that it matches an intended behavior. **Fix:** require a PR that intentionally changes output behavior to update the corresponding golden-set assertions *in the same PR*, with the property change reviewed as a real product decision, not a green-CI checkbox.

Both failure modes look identical from the outside — "the golden set didn't catch a problem" or "the golden set is flaky." Only one of them means the suite has a hole to patch by adding cases; the other means someone bypassed the review the suite exists to force.

## Real-World Examples

- **A frozen golden set misses a whole new failure category.** A support-triage golden set built at launch has no cases for a "subscription cancellation" category the product added six months later. A prompt change that breaks cancellation handling passes every CI run cleanly; the first failure anyone sees is a spike in escalations. Quarterly resampling from real traffic would have added cancellation cases before the change shipped.
- **An assertion update erases the point of the test.** A golden-set case fails after a prompt edit; under deadline pressure, the failing assertion is updated to match the new (subtly wrong) output rather than investigated. Three weeks later the same underlying bug — a missing eligibility check before offering a refund — reaches production, because the case that would have caught it was quietly rewritten to expect the broken behavior.

## Common Mistakes

- **Exact-match assertions on model output.** Breaks on harmless rewording exactly as at junior level, just now against real model calls instead of a mock, which makes it look like a "flaky model" problem when it's actually a test-design problem.
- **A golden set that never grows past its initial build.** No mechanism ties production incidents or new traffic categories back into the set, so it answers "does this match what we knew six months ago" instead of "does this match real usage."
- **Treating every failing assertion as the assertion's fault.** Updating an assertion to match new output without asking whether the new output is actually correct turns the suite into a mirror instead of a check.
- **Running the golden set only locally, never in CI.** A suite that exists but doesn't gate merges catches nothing that a rushed or distracted engineer doesn't remember to run by hand.
- **One property check per case instead of the two or three that actually matter.** A case that only checks "output is valid JSON" and nothing about its content will pass a response that's syntactically fine and substantively wrong.

---

## Apply it

1. Pull or write 20–30 representative inputs for one prompt or agent behavior you own, including at least three drawn from a real past bug or incident (or a plausible one, if none exists yet).
2. For each input, write one to three property checks — required field, banned pattern, structural validity, or threshold — that define "correct enough" without depending on exact wording.
3. Wire the suite to run against a real or cheap-model stand-in on every PR that touches the relevant prompt or agent code.
4. Deliberately introduce a regression (delete a required line from the prompt, as in Core Concept 5) and confirm the suite fails on the case built to catch exactly that.
5. Write down, in a sentence or two, your policy for when updating a failing golden-set assertion is legitimate versus when it's covering up a regression.

## Verify your work

- The suite fails when you deliberately reintroduce a known past regression, and passes once it's reverted.
- Every case's property check is traceable to a reason it exists — a real traffic pattern or a specific past incident, not a guess.
- The suite runs as part of CI on relevant PRs, not only as something a person remembers to run locally.
- At least one case in the set exists specifically because of a past production bug.
- You can state, without hedging, what would make updating a failing assertion legitimate versus what would make it a cover-up.

## Review questions

- Why does exact string matching fail as a pass/fail criterion for real model output, even when the model's behavior hasn't actually regressed?
- What are the two distinct ways a golden set goes stale, and why does each need a different fix?
- What made the disclaimer-dropping example in Core Concept 5 something CI caught instead of something a user reported first?
- How is a golden-set regression test different from an [evaluation](../evaluation/README.md) of output quality, given that both might use the same set of inputs? See [evaluation — middle](../evaluation/middle.md) for the quality-measurement side of this.
- Why is running a golden set only against a cheap stand-in model, never against the real production model, an incomplete strategy on its own?

---

*Part of [Testing](README.md) → [AI Evaluation](../README.md). Continue to [senior.md](senior.md).*
