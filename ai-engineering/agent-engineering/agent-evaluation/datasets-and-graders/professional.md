# Datasets and Graders — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you run your eval datasets as a governed asset — versioned, owned, and defended against becoming a target that's gamed instead of a measure that's trusted?

---

## Dataset ownership and versioning

- Assign a named owner to each golden set — someone accountable for its quality, not just whoever created it first.
- Version the dataset with a changelog: every added, removed, or modified case is recorded with a reason (e.g., "added case #47 — regression from incident INC-2044; removed case #12 — no longer reflects current policy"). Without this, a pass-rate change over time is unexplainable — you can't tell if the agent got better/worse or if the test itself changed underneath it.

## Labeling operations and annotator quality

- If human labels feed the golden set or calibrate the judge, treat labeling as an operational process with its own quality control: inter-annotator agreement checks, a documented labeling guideline, and periodic re-review of a sample of past labels for drift.
- Cost of labeling scales with set size and case complexity — budget for it explicitly rather than treating it as free because "someone will just label a few cases."

## Cross-team benchmark misuse

- A benchmark built for one agent's specific job can be misapplied to justify a claim about a different agent or model in a different context ("model X scored higher on our support-ticket benchmark, so it's better for the coding-assistant use case too") — a benchmark's validity doesn't transfer outside the task it measures.
- Guard against this by documenting explicitly what a benchmark does and doesn't measure, and pushing back when a score is cited outside its scope.

## Controls against Goodhart's law

- Once a benchmark becomes the target teams are compensated or evaluated on, it invites gaming — a team optimizing directly for judge-approval patterns rather than genuine quality.
- Concrete controls: rotate or periodically refresh the benchmark so a static gaming strategy stops working; keep a portion of cases private/held-out even from the team being measured; pair the automated score with a recurring independent human spot-check (see [Evaluation Fundamentals — Professional](../../evaluation-fundamentals/professional.md)) that would catch a growing gap between the metric and real quality.

## Common Mistakes

- **No changelog on dataset changes.** Makes a pass-rate trend uninterpretable — you can't separate "the agent improved" from "the test got easier."
- **Treating labeling as free, ad-hoc work.** Produces inconsistent labels with no quality control, undermining every downstream calibration built on them.
- **Citing a benchmark score outside the task it was built to measure.** Misapplies a specific, narrow validity claim to a broader one it doesn't support.
- **A fully static, fully public benchmark used as a compensation target.** Eventually gets gamed as teams learn its specific patterns rather than improving general quality.

## Apply It

1. Assign a named owner and start a changelog for each golden set currently in use.
2. Document the labeling process for any human-labeled data: guideline, inter-annotator agreement check, and re-review cadence.
3. Write down, for your most-cited benchmark, exactly what task and scope it's valid for — and where it's currently being cited outside that scope.
4. Add at least one Goodhart countermeasure (rotating cases, held-out private subset, or a recurring human spot-check) to your most heavily-optimized benchmark.

## Verify Your Work

- Every golden set in active use has a named owner and a changelog of changes with reasons.
- The labeling process has a documented guideline and a measured inter-annotator agreement.
- At least one Goodhart countermeasure is in place for any benchmark tied to a team's evaluation or compensation.

## Review Questions

- Why does a dataset changelog matter for interpreting a pass-rate trend over time?
- What's the risk of citing a benchmark score outside the task it was built to measure?
- Name one concrete countermeasure against a benchmark being gamed once it becomes a target.
