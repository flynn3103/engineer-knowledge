# Evaluation Fundamentals — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you pick metrics that map to what the agent is actually supposed to do, instead of defaulting to one generic accuracy score?

---

## Metric families

- **Outcome correctness**: did the final result match ground truth (refund amount, answer to a factual question).
- **Trajectory correctness**: did the agent take a reasonable path — right tools, right order, no redundant steps. Matters most when a wrong-but-lucky path is a real risk (e.g., skipping an eligibility check but guessing the right refund amount anyway).
- **Constraint adherence**: did the output obey a hard rule — a JSON schema, a policy ("never promise a refund date"), a tone requirement. Usually checked deterministically, not by judgment.
- **Safety**: did the agent avoid a harmful, disallowed, or out-of-scope action, independent of whether the "helpful" answer was also correct.
- **Process metrics**: step count, latency, cost per run — not quality signals by themselves, but they catch a agent that got the right answer by looping 40 times.

## Why a single composite score hides problems

- A single 0–100 "quality score" that blends correctness, tone, and safety can stay flat while one component silently regresses — e.g., correctness improves 5 points while a new safety violation appears in 2% of cases, netting no visible change in the composite.
- Report the components separately. Combine into one number only for a dashboard headline, never as the only thing a team looks at when deciding whether a change is safe to ship.

## Choosing metrics for a specific agent

1. List what the agent is for, in one sentence (e.g., "resolve order status and refund questions without human intervention").
2. For each responsibility, name the metric that would catch it failing: refund amount → outcome correctness (exact-match); "checked eligibility first" → trajectory correctness; "never leaks another customer's order" → safety, checked deterministically.
3. Drop any metric you can't act on. A metric nobody will look at or that doesn't change a decision is noise, not signal.

## Variance from temperature

- Non-zero temperature means the same case can legitimately produce different (still-correct) outputs across runs. A single run's pass/fail is noisy.
- Run each case multiple times (e.g., 3–5 repeats) when temperature is non-zero, and report the pass rate across repeats, not a single binary result — see [Datasets and Graders — Senior](../../datasets-and-graders/senior.md) for the statistics.

## Common Mistakes

- **One composite score covering correctness, safety, and tone.** Masks a real regression in one dimension behind noise or improvement in another.
- **Copying a generic eval framework's default metrics without checking they map to this agent's job.** A metric that doesn't correspond to a real failure mode of your agent wastes review time and gives false confidence.
- **Treating process metrics (latency, step count) as quality metrics.** A fast, cheap wrong answer is still wrong — track these alongside correctness, not instead of it.

## Apply It

1. Write one sentence describing your agent's job, then list its 3–5 real responsibilities.
2. For each responsibility, name the specific metric (and grading method — exact-match, rubric, deterministic rule) that would catch it failing.
3. Identify which of your current metrics don't map to any of these responsibilities, and drop them.

## Verify Your Work

- Every reported metric traces back to a named responsibility of the agent.
- Correctness, trajectory, constraint, and safety metrics are reported separately, not blended into one score.
- Process metrics (cost, latency, steps) are tracked but never substitute for a correctness signal.

## Review Questions

- Why can a single composite score stay flat while a real regression happens in one component?
- What's an example where trajectory correctness matters even though the outcome was right?
- Why do you need multiple repeats per case when temperature is non-zero?
