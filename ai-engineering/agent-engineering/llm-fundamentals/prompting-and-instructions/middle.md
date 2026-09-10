# Prompting and Instructions — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you use few-shot examples, delimiters, and structured output to make behavior consistent — and iterate against real inputs instead of guessing?

---

## Few-shot examples — the strongest steering tool

- Put 2–5 worked examples in the prompt: input → desired output, exactly in your production format. The model patterns-matches from them more reliably than from any instruction.
- **Match your production format exactly** — if production output is JSON, the examples are JSON; if it's a one-paragraph reply, examples are one-paragraph replies.
- Choose examples that cover the *hard* cases — ambiguous input, missing fields, boundary conditions — not just the happy path. The model generalizes from what it sees.
- Quality beats quantity: 3 precise, consistent examples outperform 10 sloppy ones (a sloppy example is a lesson in sloppiness).

## Delimiters — separating instruction from data

- Wrap user-provided content in explicit delimiters: triple backticks, XML tags (`<ticket>...</ticket>`), or clear section markers.
- Purpose: the model must know which text is *instruction* (to obey) and which is *material* (to operate on). Unmarked mixing invites confusion — and injection, where user text reads as new instructions.
- Delimiters also make prompts diffable and template-able — the engineering benefit stacks on the model one.

## Structured output — contract, not suggestion

- Specify the exact schema in the prompt (field names, types, what to do on missing data), and validate the result in code — treat the model like an unreliable microservice behind a schema check.
- Use the provider's native structured-output/JSON mode when available — constrained decoding beats politely-requested JSON.
- Define failure behavior: retry with the validation error fed back, fall back, or escalate — never let malformed output flow into downstream code unchecked (the retry logic lives in [Reliability and Recovery](../../agent-workflow/reliability-and-recovery/)).

## The iteration loop

1. Pull 5–10 **real** inputs — production samples, including ones that failed before.
2. Run the current prompt; grade outputs against written expectations (sealed first — see [Evaluation Fundamentals](../../agent-evaluation/evaluation-fundamentals/junior.md)).
3. Change **one thing** per iteration — an added constraint, a clarified example. Multi-change edits can't attribute improvement.
4. Re-run the same set; keep the change only if the grade improves.
5. Version prompts like code: named, dated, with the eval score recorded — "v14, 92% on ticket set, 2026-09-06."

## Common Mistakes

- **Examples in a different format than production.** The model copies the examples' shape, not your intentions — mismatch teaches mismatch.
- **Happy-path-only examples.** The model stays competent exactly where it already was and stays lost where you needed it.
- **Fixing three things per iteration.** When the score moves you won't know why; attribution is the entire value of the loop.
- **Prompt edits without a eval set.** "Feels better on my one test case" is how regressions ship.
- **Trusting unvalidated structured output.** One malformed response into a downstream parser costs more than every schema check combined.

## Apply It

1. Add 3–5 few-shot examples to one production prompt — covering happy path plus your two hardest real cases, in production format.
2. Add delimiters around all user-supplied content in the prompt.
3. Run the one-change-per-iteration loop on a set of 10 real inputs for one week; keep a log of change → score.

## Verify Your Work

- Examples match production format exactly and include hard cases.
- All user content is delimited; instructions and material are unambiguous.
- Every prompt change in the last iteration round was tested against a fixed input set with recorded scores.

## Review Questions

- Why do few-shot examples outperform adjectives, and what makes an example *bad*?
- What two problems do delimiters solve, one for the model and one for security?
- Why is one change per iteration non-negotiable in prompt development?
