# Decoding and Sampling — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Given three different tasks — data extraction, a conversational assistant reply, and creative brainstorming — can you choose and justify a decoding configuration for each, and fix a pipeline that intermittently returns malformed JSON?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Matching Decoding Strategy to Task

The junior-level lesson was mechanical: what each parameter does to a distribution. The middle-level question is a design decision: **does this task have one correct answer, or does it benefit from variety?** Variance is a feature in one case and a bug in the other, and the right decoding configuration follows directly from which one you're in.

| Task category | Temperature | Top-p / top-k | Why |
|---|---|---|---|
| Data extraction, classification, code generation | `0` – `0.2` (often just greedy) | `top_p=1` or unset — filtering barely matters when temperature is already near 0 | There is one correct field value, one correct label, one correct syntax. Any variance is a defect, not a feature. |
| Balanced assistant / chat replies | `0.6` – `0.9` | `top_p ≈ 0.9` | Some phrasing variety is desirable (repeated identical replies feel robotic), but drifting into incoherence is a real failure users notice immediately. |
| Creative writing, brainstorming, ideation | `1.0` – `1.3` | `top_p ≈ 0.95` and up | Diversity of ideas *is* the deliverable. A brainstorm that returns the single most statistically likely idea every time isn't a brainstorm. |

This table is a starting point, not a fixed rule — the real skill is being able to justify *why* a given task sits where it does, so that when a new task doesn't fit cleanly (say, a chatbot that also needs to emit a structured API call mid-conversation), you can reason about which sub-behavior needs which setting rather than picking one temperature for the whole interaction.

## Core Concept 2 — min-p: A Confidence-Relative Alternative to top-p

Top-p has a real weakness at the extremes: its cutoff is an *absolute* cumulative-probability threshold, so the size of the resulting candidate pool depends heavily on the shape of the distribution's tail, not just on how confident the model actually is. **min-p sampling** addresses this by setting the cutoff *relative to the top token's own probability* instead of an absolute cumulative mass: keep every token whose probability is at least `min_p × P(top token)`.

```
min_p = 0.1
Top token probability = 0.5  → keep any token with P ≥ 0.05
Top token probability = 0.05 → keep any token with P ≥ 0.005
```

The practical difference from top-p shows up when the model's confidence swings between very peaked and very flat distributions in the same generation (common in longer outputs — a model is often very sure of the next token right after a comma, and much less sure at the start of a new clause). A fixed `top_p` threshold can, depending on how the tail is shaped, admit an unexpectedly large or small pool at either extreme; because min-p's threshold moves with the top token's own probability, the *relative* bar for "good enough to be a candidate" stays consistent whether the model is very sure or genuinely torn. It's newer than top-p and not universally supported across every provider's API yet, but it's available in common local-inference stacks (`llama.cpp`, `vLLM`, Hugging Face `transformers`, Ollama) and is worth reaching for specifically when top-p is producing inconsistent quality across a mix of confident and uncertain generations.

## Core Concept 3 — Repetition, Frequency, and Presence Penalties

Sampling controls decide *which* token to pick from the distribution at a single step; **repetition penalties** change the distribution itself based on what's already been generated, discouraging (or in some implementations, outright ranking down) tokens the model has already used.

Two common forms:

- **Repetition penalty** (used in most open-source inference stacks, e.g. `repetition_penalty=1.2` in Hugging Face `transformers`): divides the logit of any already-generated token by the penalty factor before sampling, making repeats less likely proportional to the factor.
- **Frequency and presence penalties** (OpenAI's API, each ranging `-2.0` to `2.0`): `frequency_penalty` scales down a token's logit proportionally to *how many times* it has already appeared — the more repeats, the stronger the discouragement. `presence_penalty` applies a flat penalty the moment a token has appeared *at all*, regardless of count, which pushes toward introducing new topics rather than just avoiding exact repeats.

These are genuinely useful for long-form generation, where an unpenalized model can fall into "the the the" loops or repeat a whole sentence verbatim. But they actively hurt any task where legitimate repetition is part of correct output:

- **Code generation** — keywords like `if`, `return`, `self.`, and common variable names are supposed to appear dozens of times in a working function. A repetition penalty tuned for prose can nudge the model away from the syntactically correct repeated token toward an incorrect substitute.
- **Structured data extraction** — a JSON array of ten similar objects legitimately repeats the same field names (`"name"`, `"id"`, `"status"`) ten times. Penalizing that repetition can corrupt field names partway through the output.

The rule: repetition penalties belong on long-form, free-text generation tasks, and should be off (or very close to it) on tasks where the correct output is expected to repeat tokens verbatim.

## Core Concept 4 — Constrained Decoding: Guaranteeing Structure, Not Requesting It

"Please respond only in valid JSON matching this schema" in the prompt is an *instruction* — the model is still sampling from its normal token distribution and can, and does, occasionally violate it: a missing closing brace, a stray trailing comma, a field name spelled slightly differently than requested. At moderate-to-high temperature this happens often enough to be a real production problem, not an edge case.

**Constrained decoding** (also called structured output or grammar-constrained generation) fixes this at the decoding step itself rather than through the prompt: at every token position, the decoder masks out — sets to zero probability — any token that would make the output invalid according to a target grammar or JSON schema, *before* sampling. The model is structurally unable to emit an invalid token, because it was never a candidate to begin with. This is a different mechanism than prompting: prompting hopes the model chooses correctly from an unconstrained distribution; constrained decoding removes the incorrect options from the distribution entirely.

Concrete implementations worth knowing by name:

- **OpenAI Structured Outputs** (`response_format: {"type": "json_schema", "json_schema": {...}, "strict": true}`) — guarantees the output conforms to the supplied JSON Schema via constrained decoding. This is a stronger guarantee than the older `{"type": "json_object"}` JSON mode, which only guarantees syntactically valid JSON, not that it matches any particular schema.
- **Anthropic tool use for structured extraction** — defining a tool with an `input_schema` and forcing the model to call it constrains the model's output to match that schema, using extraction through the tool-calling mechanism rather than free-text JSON in the message body.

## Core Concept 5 — Scenario: Fixing an Intermittently Malformed Extraction Pipeline

A pipeline extracts structured fields (invoice number, date, total, vendor name) from scanned documents. The prompt says *"Respond only with a JSON object matching this schema: ..."*, temperature is set to `0.7` because a teammate copied a chat-assistant config, and roughly 1 in 20 documents comes back with output that fails to parse as JSON — a missing bracket, an extra field, a number formatted as `"$1,204.50"` instead of `1204.50`.

Diagnosis, in order:

1. **Temperature is wrong for the task.** This is data extraction — Core Concept 1 says `0`–`0.2`. A temperature of `0.7` is actively injecting variance into a task that has exactly one correct answer per document, which explains why the failure is intermittent rather than constant: most samples land on the correct structure, some don't.
2. **The schema is enforced only by the prompt, not by the decoder.** Even at `temperature=0`, a prompt-only instruction is a request the model can still misinterpret or drift from — it does not structurally prevent an invalid token.

Fix: drop temperature to `0`–`0.2`, and switch from prompt-only formatting instructions to a real constrained-decoding feature — OpenAI Structured Outputs with the exact target schema, or Anthropic tool use with a forced tool call carrying the schema as `input_schema`. The prompt no longer needs to *beg* for correct JSON; the decoder cannot produce anything else.

## Verification: Measure the Rate, Don't Eyeball a Few Outputs

A fix that "looks right" on the five documents an engineer happened to check is not verified. The correct check is a **schema-validity rate** measured across a real sample size:

```
Run the pipeline against 200 representative documents.
Count: how many outputs parse as JSON AND validate against the target schema?

Before fix:  187 / 200 valid  (93.5%)
After fix:   200 / 200 valid  (100%)
```

200 is a practical minimum for a rate that started around 90–95% — small enough to run cheaply, large enough that a handful of new failures shows up as a real percentage-point change rather than getting lost in noise. Track this number the same way you'd track a test pass rate: rerun it whenever the prompt, the model version, or the decoding configuration changes, not just once at rollout.

## Real-World Examples

- **A "creative" temperature setting silently breaks an unrelated extraction call.** A team copies a decoding config from their chat-assistant feature (`temperature=0.8`, tuned deliberately for conversational variety) into a new extraction endpoint because it was the nearest example in the codebase. The extraction endpoint's malformed-output rate is high from day one, and the root cause isn't the prompt or the model — it's an inherited setting that was correct for a different task.
- **Switching to JSON mode alone doesn't fully fix malformed extraction.** A team adopts `{"type": "json_object"}` expecting the malformed-JSON problem to disappear, and syntax errors do stop — but field names still occasionally drift from the requested schema (an extra field, a renamed key), because JSON mode guarantees valid JSON syntax, not schema conformance. Moving to schema-aware structured outputs (or a forced tool call with a defined `input_schema`) closes that remaining gap.
- **A repetition penalty tuned for blog-post generation corrupts a code-generation feature reusing the same service.** A shared "long-form generation" decoding profile with `frequency_penalty=0.5` gets applied to a code-completion feature by default; the model starts avoiding the repeated `self.` and `return` tokens that correct Python requires, producing subtly broken completions that pass a quick glance but fail linting.

## Common Mistakes

- **Copying a decoding config from a different task without re-justifying it.** A setting correct for chat is not automatically correct for extraction, code generation, or brainstorming — Core Concept 1's table exists because the right answer depends on the task, not on precedent.
- **Treating prompt-only JSON instructions as equivalent to constrained decoding.** They fail at different, non-zero rates; only constrained decoding structurally guarantees conformance.
- **Applying a repetition penalty uniformly across all tasks.** Correct for long-form prose, actively harmful for code and structured data with legitimate repeated tokens.
- **"Fixing" a malformed-output bug by only lowering temperature, without also adopting structured output.** Lower temperature reduces the *rate* of malformed output but doesn't eliminate it the way decoder-level constraints do — the two fixes address different layers of the same problem.
- **Declaring a fix verified after checking a handful of outputs by eye.** A handful of samples can look perfect while the underlying rate is still meaningfully below 100% — measure the rate across a real sample.

---

## Apply it

1. Take (or build) a small pipeline that extracts 3–4 structured fields from unstructured text using an LLM call.
2. Run it against 20 varied inputs at `temperature=0.7` with prompt-only JSON instructions, and record how many outputs fail to parse or fail schema validation.
3. Apply the fix from Core Concept 5: lower temperature to `0`–`0.2` and switch to a real structured-output/constrained-decoding feature for your provider.
4. Re-run the same 20 inputs (plus at least 20 more, for a total of 40+) and recompute the schema-validity rate.
5. Separately, take a creative or open-ended task and deliberately configure it with the extraction task's low-temperature settings — observe and describe in one paragraph why the output is now worse for that task, to confirm the trade-off runs in both directions.

## Verify your work

- You have a schema-validity rate (a fraction, not an impression) for the pipeline before and after the fix.
- The after-fix rate is measurably higher, and you can name specifically which change — temperature, structured output, or both — closed the largest part of the gap.
- You can explain, for your chosen extraction task, why `top_p` and repetition penalty were left at defaults or disabled rather than tuned.
- You produced at least one concrete example of a decoding setting that is *wrong* for a task (the reversed test in step 5), not only examples of correct settings.
- You can name, without looking it up, one real API feature (by name) that performs constrained decoding rather than prompt-only formatting.

## Review questions

- Why is temperature variance a defect for data extraction but a desirable property for creative brainstorming?
- What does min-p change relative to the top token's probability, and what specific top-p weakness does that address?
- Why does a repetition penalty tuned for long-form prose actively hurt code generation and structured data extraction?
- What is the mechanical difference between a prompt asking for JSON and a constrained-decoding feature enforcing a JSON schema?
- Why is checking a handful of outputs by eye insufficient to declare a malformed-output fix verified?
