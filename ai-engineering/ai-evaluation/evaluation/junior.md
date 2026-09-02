# Evaluation — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a fixed set of model outputs and a concrete rubric, can you score them by hand, compute a pass rate, and explain why that's a different question from "does this pass a test"?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

Part of [Evaluation](README.md).

---

## Core Concept 1 — Evaluation Is Not Testing

If you've just come from [Testing](../testing/README.md), the words "test" and "evaluate" will want to blur together. Keep them apart — they answer different questions, and confusing them produces the wrong kind of check.

| | Testing | Evaluation |
|---|---|---|
| Question asked | Did this specific known case break? | How good is this, on what dimensions, compared to what? |
| Answer shape | Pass / fail against a fixed expectation | A graded score, often on more than one axis |
| Ground truth | An exact or tightly-bounded expected output | A rubric or human judgment — "good" is graded, not binary |
| Typical use | Regression check before merging a change | Quality measurement before and after shipping a change |
| Example | "Given this exact input, the tool-call arguments must match this JSON" | "Across 30 support answers, how many are factually grounded in the retrieved article?" |

A regression test on a golden set tells you a known case didn't silently break. It cannot tell you whether the system is *good* — a model can pass every regression test in your suite and still produce mediocre, ungrounded, or unhelpful answers on the inputs nobody wrote a test for. That broader, graded, comparative question is what evaluation exists to answer. See [Testing — Middle](../testing/middle.md) for how a golden-set regression suite is built; the two use similar-looking example sets for genuinely different purposes.

## Core Concept 2 — Vocabulary: Eval Set, Rubric, Score, Baseline

- **Eval set** — a fixed collection of representative inputs (and sometimes reference outputs) you run the system against repeatedly. Not the same as a golden set: a golden set exists to catch known regressions; an eval set exists to measure overall quality right now.
- **Rubric** — an explicit, written definition of what "good" means for this task, broken into criteria a scorer (human or automated) can check independently.
- **Score** — the result of applying the rubric to one output. Can be binary (pass/fail per criterion) or a small scale (1–3, 1–5) with each point defined.
- **Baseline** — the thing you're comparing against: a previous prompt version, a different model, or a minimum acceptable bar. A score with no stated baseline ("87% helpful") is not yet useful — 87% compared to what?

## Core Concept 3 — A Bad Rubric vs. a Good Rubric

The single most common junior mistake in evaluation is writing a rubric like this:

> **Quality: rate 1–5.**

This fails for three concrete reasons: it's one dimension pretending to cover everything (accuracy, tone, and completeness all get collapsed into one number), it never defines what separates a 3 from a 4, and two people scoring the same output will disagree because they're each silently inventing their own definition of "quality" as they go.

A good rubric replaces one vague dimension with several narrow, independently checkable ones. For a RAG-backed customer support bot answering questions from a knowledge base, a usable rubric looks like this:

| Criterion | Definition | Scale |
|---|---|---|
| **Groundedness** | Every factual claim in the answer is supported by the retrieved knowledge-base article shown alongside it | Pass / Fail |
| **On-topic** | The answer addresses the question actually asked, not a related but different one | Pass / Fail |
| **Safety** | No promise (refund amount, ship date, policy exception) is stated unless it appears in the retrieved article | Pass / Fail |
| **Completeness** | 1 = missing information the user needs to act; 2 = partially complete; 3 = fully actionable | 1–3 |

Each row is checkable on its own, by reading the output and the retrieved article side by side, without needing to hold the other three criteria in your head at the same time. That independence is what makes the rubric usable by more than one person consistently.

## Core Concept 4 — Worked Example: Scoring Five Responses by Hand

Five customer-support responses, each generated from the same retrieved article ("Refunds are issued within 5–7 business days to the original payment method for items returned within 30 days"), scored against the rubric above:

| # | Response (summary) | Grounded | On-topic | Safety | Complete | Overall |
|---|---|---|---|---|---|---|
| 1 | States 5–7 business day refund timeline, original payment method | Pass | Pass | Pass | 3 | **PASS** |
| 2 | States refund is "usually instant" and offers a $10 goodwill credit | Fail (neither claim is in the article) | Pass | Fail | 2 | **FAIL** |
| 3 | Explains the return-shipping label process instead of refund timing | Pass | Fail (answers a different question) | Pass | 1 | **FAIL** |
| 4 | States the 5–7 day window but omits the 30-day return-eligibility condition | Pass | Pass | Pass | 2 | **PASS** |
| 5 | States timeline, payment method, and the 30-day condition fully | Pass | Pass | Pass | 3 | **PASS** |

An output only passes overall if every Pass/Fail criterion passes and Completeness scores 2 or higher — a single failed criterion fails the whole response, regardless of how good the rest of it reads.

Aggregate results:

- **Overall pass rate: 3/5 = 60%**
- Groundedness: 4/5 = 80%
- On-topic: 4/5 = 80%
- Safety: 4/5 = 80%
- Mean completeness: (3+2+1+2+3)/5 = **2.2 / 3**

Response 2 is the instructive failure: it reads fluently and confidently, and a vague "rate 1–5 for quality" rubric might well have scored it a 4. The groundedness criterion catches it specifically because it isolates *one* checkable fact — is this claim in the source article — from the response's overall polish.

## Core Concept 5 — The Repeatable Method

1. **Assemble an eval set.** 15–30 examples that represent real, typical inputs plus a few known-hard edge cases (ambiguous questions, missing context, policy exceptions). Fewer than ~15 makes the pass rate noisy; a single unlucky example swings it by several points.
2. **Write the rubric before you look at outputs.** 2–4 concrete criteria, each independently checkable, each with its scale defined in writing (what does a 1 mean versus a 2?).
3. **Score every output against every criterion**, one criterion at a time across the whole batch rather than one output fully scored before moving to the next — this keeps a single criterion's standard consistent instead of drifting as you get tired or distracted.
4. **Compute the aggregate per criterion, not just an overall number.** An 80% overall pass rate hides whether the failures cluster on one criterion (fixable with a prompt tweak) or are scattered across all of them (a deeper problem).
5. **Record the specific failing criterion for every failure**, not just "bad output" — "failed groundedness, invented a $10 credit" is something you can act on; "bad" is not.

## Common Mistakes

- **Scoring holistically instead of per-criterion.** Reading an output once and assigning a single vibe-based number lets a confident tone paper over a factual error — this is exactly what sank Response 2 above if scored holistically.
- **A rubric with one vague dimension.** "Quality: 1–5" cannot be applied consistently by two different people, and even by the same person on two different days.
- **An eval set too small or too easy.** Five friendly, unambiguous questions will pass almost anything; the eval set needs the messy, ambiguous, or edge-case inputs the system actually receives.
- **Not defining the scale.** A 1–3 "completeness" criterion with no written definition of what 1, 2, and 3 mean isn't a rubric, it's a guess with extra steps.
- **Averaging away a safety failure.** A 90% overall score that includes one unsafe promise to a customer is not a 90% system — some criteria (safety, groundedness) deserve reporting as a hard floor, not just folded into an average.

## Apply it

1. Take 20 real or representative outputs from a system you have access to (support responses, summaries, generated descriptions — anything with a clear "what should this contain" answer).
2. Write a rubric with 2–4 concrete criteria. For each, write the pass/fail definition or the 1–3 scale definition *before* you read any of the 20 outputs.
3. Score all 20 outputs against each criterion, one criterion at a time (all 20 for criterion 1, then all 20 for criterion 2, and so on).
4. Compute the overall pass rate and the per-criterion pass rate. Identify which single criterion accounts for the most failures.
5. Pick the three worst-scoring outputs and write, in one sentence each, the specific criterion and reason they failed.

## Verify your work

- Every criterion in your rubric has a written definition of what separates a pass from a fail, or what separates each point on its scale.
- You can point to the specific criterion that failed for every failing output — not a vague "this one wasn't great."
- Your per-criterion pass rates are reported separately, not folded into one overall number that could hide a concentrated failure.
- A second person reading your rubric (without you explaining it out loud) could score at least a few of the same outputs and land close to your scores.
- You can state, in one sentence, what makes your eval set different from a regression test's golden set.

## Review questions

- What question does testing answer that evaluation does not, and what question does evaluation answer that testing does not?
- Why does a rubric like "quality: rate 1–5" fail to produce consistent scores between two different people?
- Why does scoring one criterion at a time across a whole batch produce more consistent results than scoring one output fully before moving to the next?
- Why can an output with a fluent, confident tone still fail a groundedness criterion?
- What is missing from a reported score of "87% helpful" with no further context?
