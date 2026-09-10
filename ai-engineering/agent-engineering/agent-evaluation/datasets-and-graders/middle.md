# Datasets and Graders — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you grade open-ended text with an LLM-as-judge, calibrate it against human judgment, and know its common failure modes well enough not to trust it blindly?

---

## Rubric-based LLM-as-judge

- Write a rubric with explicit criteria (e.g., "does the reply acknowledge the customer's issue; does it state a concrete next step; is the tone professional") rather than asking the judge for a vague "rate the quality 1–10."
- A specific rubric produces more consistent, more explainable scores than an open-ended quality request, and lets you see *which* criterion failed, not just an aggregate number.

## Pairwise vs. absolute scoring

- **Absolute scoring**: judge rates one output against the rubric independently (e.g., 1–5 per criterion). Simpler, but LLM judges tend to cluster scores in a narrow range, making small real differences hard to detect.
- **Pairwise scoring**: judge is shown two outputs (e.g., old prompt vs. new prompt, same case) and picks which is better. More sensitive to small improvements, and is the right tool for "did this change make things better" questions specifically.
- **Reference-based vs. reference-free**: reference-based judging compares the output to a known-good example; reference-free judges quality directly against the rubric with no example to compare to. Reference-based is more reliable when a good reference genuinely exists (e.g., a human-written ideal reply for this exact case).

## Calibrating the judge against humans

1. Have a human grade a sample of cases (30–50) using the same rubric.
2. Run the LLM judge on the same cases.
3. Compute agreement (e.g., Cohen's kappa, or simple percent-agreement) between judge and human.
4. If agreement is low, revise the rubric wording (usually the issue — ambiguous criteria) and recalibrate before trusting the judge on cases with no human label.

## Known judge biases

- **Position bias**: in pairwise scoring, the judge favors whichever output is shown first (or second) regardless of quality — mitigate by randomizing or swapping order and averaging.
- **Length bias**: judges tend to rate longer answers as more thorough even when the extra length adds no value — mitigate by including a rubric criterion that explicitly penalizes unnecessary length.
- **Self-preference bias**: a judge model tends to rate outputs from its own model family higher — mitigate by using a different model family as judge than the one being evaluated, where feasible.

## Dataset hygiene

- **Dedupe**: near-duplicate cases inflate the appearance of coverage without adding real signal — check for and remove them.
- **Difficulty stratification**: tag cases as easy/ambiguous/adversarial so you can report pass rate per difficulty tier, not just in aggregate (an easy-case-heavy set overstates real-world performance).
- **Growing from prod failures**: every confirmed production failure becomes a new golden-set case (see [Debugging Agent Failures](../../debugging-agent-failures/)) — this is how the set stays representative of real failure modes instead of only the failure modes you imagined up front.
- **Freezing a held-out slice**: keep a portion of the set untouched during iteration, scored only at decision points — see [Evaluation Fundamentals — Senior](../../evaluation-fundamentals/senior.md).

## Common Mistakes

- **An open-ended "rate 1–10" prompt instead of a specific rubric.** Produces inconsistent, unexplainable scores that don't tell you which dimension actually failed.
- **Never calibrating the judge against a human baseline.** You have no idea whether the judge's scores mean anything until you check agreement.
- **Ignoring position and length bias in pairwise comparisons.** Silently favors whichever output happens to be verbose or shown first, independent of actual quality.

## Apply It

1. Write a rubric with 3–5 explicit criteria for one agent's open-ended output.
2. Grade 30–50 cases with both a human and the LLM judge using the same rubric; compute agreement.
3. If agreement is low, identify the ambiguous criterion, rewrite it, and recalibrate.
4. Check your pairwise setup (if used) for position bias by swapping output order and comparing results.

## Verify Your Work

- The rubric has explicit, checkable criteria — not a single vague quality request.
- Judge-human agreement has been measured on a real sample, with the number recorded.
- Pairwise comparisons are checked for position bias by swapping order.

## Review Questions

- Why does a specific rubric produce more useful scores than an open-ended "rate the quality" prompt?
- What does judge-human agreement tell you, and what do you do if it's low?
- Name one judge bias and its mitigation.
