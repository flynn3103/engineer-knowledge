# Observability — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a single LLM call in a small service, can you instrument it so a trace captures the prompt, the completion, the latency, the token counts, and the cost — and then read that trace back to answer a concrete question about what happened?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — What's Different From Standard APM

Standard application observability already gives you request duration, status codes, and structured logs. An LLM call needs the same discipline plus fields that don't exist in ordinary HTTP instrumentation, because the thing you're calling is expensive, non-deterministic, and can fail in ways a status code won't show:

| Standard APM field | LLM-specific addition | Why it's needed |
|---|---|---|
| `duration_ms` | same, but latency varies 10x call-to-call for the same endpoint | A slow call isn't necessarily a bug — model latency is intrinsically variable |
| `status_code` | `finish_reason` (`stop`, `length`, `content_filter`, `tool_calls`) | A `200` response can still be a truncated, refused, or malformed answer |
| — | `prompt` / `completion` (the actual text sent and received) | The only way to know *why* a model produced a given output is to see what it was given |
| — | `model`, `prompt_tokens`, `completion_tokens` | Token counts drive both cost and whether you're near the context window limit |
| — | `cost_usd` | Unlike a database query, every call has a metered, per-token dollar cost |

A **trace** is the record of one request; a **span** is one timed unit of work inside it (here, one model call). At junior level you're producing exactly one span per request. `middle.md` covers what happens once a request spans multiple calls.

## Core Concept 2 — Fields to Capture on Every Call

For a single LLM call, capture at minimum:

- `trace_id` — a unique ID for this request, so you can find it again
- `model` — the exact model string sent to the provider (`gpt-4o-mini`, not just "the summarizer model")
- `prompt` — the full system + user messages sent
- `completion` — the full text (or structured output) returned
- `latency_ms` — wall-clock time for the call
- `prompt_tokens`, `completion_tokens` — from the provider's response, not estimated
- `cost_usd` — computed from token counts × that model's per-token rate
- `finish_reason` — did the model stop normally, hit a length limit, or get filtered

Miss `prompt_tokens`/`completion_tokens` or `cost_usd` and you can't answer "why did this call cost more than usual" without re-deriving it after the fact — which you often can't, because the provider's pricing or the exact prompt text may no longer be available to you by then.

## Core Concept 3 — Instrumenting a Single Call

Take a small summarization endpoint: it accepts text, calls a model, returns a summary. Using [Langfuse](https://langfuse.com)'s Python SDK — one concrete, real tool, not a hypothetical one — instrumentation is a decorator plus a drop-in wrapped client:

```python
from langfuse.decorators import observe
from langfuse.openai import openai  # drop-in replacement for the openai client

@observe()
def summarize(text: str) -> str:
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Summarize the input in 2 sentences."},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content
```

`@observe()` opens a trace for the function call. The wrapped `openai` client automatically records the request messages, the response text, `model`, `prompt_tokens`, `completion_tokens`, `latency_ms`, and `finish_reason` onto that trace — you didn't write any of that logging by hand. Langfuse computes `cost_usd` from the token counts and the model's published rate.

The same fields have a vendor-neutral name if you instrument with raw OpenTelemetry instead of a vendor SDK: the [OpenTelemetry Generative AI semantic conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) (an evolving part of the OTel spec) define attributes like `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, and `gen_ai.response.finish_reasons` on a span. Langfuse, LangSmith, and Arize Phoenix all either speak this convention directly or map their own fields onto it — which is *why* a trace captured with one tool's SDK can often be read, or migrated, with minimal translation. You don't need to hand-roll `gen_ai.*` spans at junior level; knowing the names exist is enough to recognize them later.

## Core Concept 4 — Reading the Trace Back

Instrumentation is only useful if it answers a real question. Say a teammate reports: "the summarize endpoint felt slow and expensive around 2pm." Opening that trace in Langfuse's UI (or querying it via the API) should show you, for that specific call:

```
trace_id:          8f1c2a...
model:              gpt-4o-mini
latency_ms:         4213
prompt_tokens:      1,840
completion_tokens:  312
cost_usd:           0.0071
finish_reason:      stop
prompt:             "Summarize the input in 2 sentences.\n\n<article text>"
completion:         "The article discusses ..."
```

That single record answers the question without guessing: 1,840 prompt tokens is unusually high for this endpoint (a caller passed in a long article instead of an excerpt), and the elevated latency and cost both follow directly from that — not from a model outage or a code regression. Without the trace, "it felt slow" stays an anecdote; with it, it's a specific input-size problem you can now decide whether to fix (truncate input, chunk it, or accept the cost).

## Common Mistakes

1. **Logging only the completion, not the prompt.** Without the prompt, you can't explain *why* the model produced a given output, and you can't reproduce the call to debug it.
2. **Estimating tokens instead of reading them from the response.** Every major provider returns exact `prompt_tokens`/`completion_tokens` in the response payload — using a rough character-count estimate instead produces cost figures that are wrong and drift further wrong as prompts change.
3. **Not capturing `finish_reason`.** A response truncated by `length` or blocked by `content_filter` still returns `200` from the HTTP layer; without `finish_reason` in the trace, a truncated-output bug looks identical to a working call.
4. **Treating latency as a bug signal by itself.** LLM latency is intrinsically variable call-to-call; a single slow trace only becomes a signal once you check what else it has in common (input size, model, time of day) with other slow traces.
5. **Hardcoding a stale price to compute cost.** Provider pricing changes; compute cost from the token counts and a rate table you can update, not a number baked into application code.

## Apply it

1. Take a small endpoint that makes exactly one LLM call (or write one — a summarizer, a classifier, anything with a single prompt in, single completion out).
2. Instrument it so every call captures: `trace_id`, `model`, `prompt`, `completion`, `latency_ms`, `prompt_tokens`, `completion_tokens`, `cost_usd`, `finish_reason`. Use Langfuse, LangSmith, or raw OpenTelemetry spans with `gen_ai.*` attributes — pick one and be consistent.
3. Make three calls with different input sizes (short, medium, long).
4. Without looking at your code, open the trace view and answer: which call cost the most, and why? Which had the longest latency, and does that correlate with token count or something else?
5. Deliberately send an input long enough to hit the model's output length limit and confirm `finish_reason` shows `length`, not `stop`.

## Verify your work

- Every call produces a trace with all eight fields from Core Concept 2 populated — none are blank, estimated, or hardcoded.
- You can find a specific trace by its `trace_id` and read the exact prompt and completion that produced it.
- `cost_usd` for a given trace matches token counts × the model's published per-token rate, computed, not guessed.
- A truncated or filtered response shows a `finish_reason` other than `stop`, and you can find it without re-reading the completion text.
- You answered the "which call cost the most, and why" exercise using only the trace view, not your code or memory of what you sent.

## Review questions

- Why isn't an HTTP `200` status code sufficient evidence that an LLM call produced a usable response?
- What can you learn from a trace that includes both the prompt and the completion, that you cannot learn from the completion alone?
- Why should token counts come from the provider's response rather than an estimate?
- What is the relationship between the vendor-specific fields a tool like Langfuse records and the `gen_ai.*` attributes in the OpenTelemetry GenAI semantic conventions?

---

*Continue to [`middle.md`](middle.md). Part of [Observability](README.md) → [AI Evaluation](../README.md).*
