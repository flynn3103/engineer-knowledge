# Temperature and Sampling — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you assign a sampling setting to each task type your app has — and explain why "more creative" is actively harmful for half of them?

---

## Match the setting to the task

| Task type | Temperature | Why |
|---|---|---|
| Extraction, classification | 0 – 0.2 | There is one right answer; variability is pure error. |
| Structured output (JSON, tool calls) | 0 – 0.2 | Schema violations rise with randomness; every invalid output is a bug you pay for downstream. |
| Code generation | 0 – 0.3 | Code is right or wrong; plausible-but-wrong tokens are the failure mode. |
| Analytical answers, summaries | 0.3 – 0.7 | Slight variation in phrasing is fine; factual drift is not. |
| Marketing copy, brainstorming, naming | 0.8 – 1.2 | The goal *is* varied, surprising candidates; predictability is failure. |
|Data augmentation, synthetic test cases | 0.9 – 1.3 | You want diversity by construction. |

- The pattern: the moment a task has **one correct answer**, lower temperature. The moment a task **values novelty**, higher. Almost no real app task sits at "high by default."

## Why high temperature breaks tool calls and schemas

- A tool call is a sequence of exact tokens: a name, argument keys, valid values. Randomness at any position can corrupt the sequence — a misspelled argument key, a stray character, a hallucinated tool name.
- Downstream, your code parses that output. Every corrupted call becomes a retry, a fallback, or an error path — you've paid for randomness and then paid again to contain it.
- Structured-output features (JSON mode, constrained decoding) reduce *which* tokens are legal — use them, and keep temperature low anyway. Constraints reduce invalid formats; low temperature reduces incoherent *choices* within the valid ones.

## One app, several settings

- Real apps are multi-task: a support agent classifies (low), drafts a reply (mid), suggests empathetic openers (higher).
- Make the setting a per-task property of the code — a config value next to the prompt — not a global default inherited from wherever the client was initialized.

## Common Mistakes

- **One temperature for the whole app.** The brainstorming preset quietly drives the JSON extraction path.
- **Raising temperature because output is "boring."** Boring-but-correct is usually the spec; if phrasing variety is genuinely wanted, scope that to the drafting task only.
- **Constrained decoding treated as a license for high temperature.** Schema-valid gibberish is still gibberish.
- **Copy-pasting example code with its settings.** Demos default to 0.7–1.0 for lively output — wrong for most production tasks.

## Apply It

1. List every distinct LLM task in your app; assign each a temperature from the table above, written next to its prompt.
2. For each structured-output task, confirm both a low setting and a schema constraint are in place.
3. Replace any single global sampling default with per-task values.

## Verify Your Work

- Every task type has an explicit, documented setting — nothing inherited by accident.
- Structured-output tasks are low-temperature *and* schema-constrained.
- Creative-range settings exist only on tasks whose spec values novelty.

## Review Questions

- Why does structured output need low temperature even with constrained decoding on?
- Which of your tasks genuinely benefit from temperature above 0.8, and what in their spec says so?
- Where should the sampling setting live in code, and why not as a global default?
