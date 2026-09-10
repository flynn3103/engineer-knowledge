# Datasets and Graders — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you tell a real improvement from noise, and decide exactly which subset of your eval suite is allowed to block a deploy?

---

## Variance across repeats

- At non-zero temperature, the same case can pass on one run and fail on the next. A single-run pass rate comparison between two prompt versions can show a "difference" that's pure noise.
- Run each case N times (commonly 3–10, depending on cost tolerance) per version being compared, and report a pass rate with a confidence interval, not a single number.

## Confidence intervals and minimum detectable effect

- A pass-rate difference of 2 percentage points on a 30-case set with wide confidence intervals may not be statistically distinguishable from zero — compute the interval before claiming "the new version is better."
- **Minimum detectable effect**: given your sample size and repeat count, there's a smallest true difference your setup can reliably detect. If your set is too small, a real 5-point improvement may be indistinguishable from noise — the fix is more cases or more repeats, not a lower bar for claiming success.

## Paired A/B on prompts

- Compare two prompt versions on the *same* cases (paired), not on separately-sampled sets — paired comparison controls for case-to-case difficulty variance and needs a smaller sample to detect a real difference than an unpaired comparison would.

## Regression suites and release gates

- The subset of the golden set that blocks a deploy should be: fast enough to run on every merge candidate, deterministic or low-variance enough that a flake doesn't block a good change, and covering the responsibilities where a regression is unambiguous and costly (see [Evaluation Fundamentals — Senior](../../evaluation-fundamentals/senior.md) for gate vs. observe).
- **Flake budget**: allow a small, explicit tolerance for a case that legitimately varies across runs (e.g., "must pass 4 of 5 repeats," not "must pass every single time") — an all-or-nothing gate on a noisy case blocks good changes for the wrong reason.
- **Suite runtime and cost**: a CI gate suite using an LLM judge on every case can become slow and expensive at high commit frequency — keep the gating subset small and deterministic-first, reserving judge-graded cases for a slower pre-release suite.
- **Mocked tool layers**: for deterministic CI runs, mock external tool calls (order lookup, payment API) with fixed responses so the gate suite doesn't depend on live external systems being up, and doesn't produce different results run to run due to real data changing underneath it.

## Online eval: shadow runs, A/B, implicit signals

- **Shadow runs**: run the new version alongside the old one on real traffic without acting on its output, comparing results — catches issues an offline set didn't anticipate, with zero customer-facing risk.
- **A/B**: split real traffic between versions and act on both, comparing outcomes — needed when the true measure of quality only shows up in downstream behavior (e.g., did the customer re-contact support).
- **Implicit signals**: escalation rate (agent handed off to a human), human edit distance on a drafted reply (how much a human had to change before sending) — these are proxies for quality that don't require an explicit label and can be tracked on 100% of prod traffic.

## Common Mistakes

- **Comparing single-run pass rates between two versions.** Reports noise as if it were a real difference, especially at non-zero temperature.
- **An all-or-nothing gate on a case with known run-to-run variance.** Blocks legitimately good changes on a flake, training the team to route around or ignore the gate.
- **Gating CI on the full judge-graded suite.** Slows every commit and racks up judge-call cost that doesn't need to be paid at that frequency.
- **No mocked tool layer for CI.** Gate results become flaky or wrong whenever an external dependency is slow, down, or its underlying data has changed.

## Apply It

1. For your two most recently compared prompt versions, recompute the pass-rate difference with repeats and a confidence interval — check whether the claimed improvement holds up.
2. Define your CI gate subset explicitly: which cases, what flake tolerance, and confirm it uses mocked tool responses.
3. Set up one online signal (shadow run, A/B, or an implicit signal like escalation rate) for your highest-risk agent.

## Verify Your Work

- Prompt-version comparisons use paired repeats with a reported confidence interval, not a single-run pass rate.
- The CI gate suite has an explicit flake tolerance and uses mocked tool responses.
- At least one online signal exists that doesn't depend on the offline golden set.

## Review Questions

- Why can a single-run pass-rate comparison between two prompt versions be misleading?
- What is a flake budget, and why is an all-or-nothing gate on a noisy case counterproductive?
- Why does a shadow run catch issues an offline golden set might miss?
