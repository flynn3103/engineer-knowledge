# Prompt Engineering - Professional

At staff level, prompt behavior is an interaction among instruction
precedence, tokenization, decoding, context construction, and serving
infrastructure. Wording is only one control surface.

## Under the hood in real systems

**Anthropic Messages API** separates system instructions from alternating
user and assistant content blocks. Tool results carry explicit content types;
preserving those boundaries is safer than interpolating everything into one
string. Prompt caching reuses attention work for stable prefixes, so place
large invariant policy and reference material before volatile user content.

**OpenAI Structured Outputs** uses constrained decoding against a supported
JSON Schema subset. At each generation step, invalid next tokens are masked.
This can guarantee syntax and shape, but not semantic truth: a valid
`{"approved": true}` can still be the wrong decision.

**llama.cpp grammars** apply GBNF constraints during local inference. The
grammar narrows token choices and can increase time-to-first-token when its
state is complex. This shows why "return JSON" in prose and grammar-enforced
JSON are different guarantees.

## Scale and failure behavior

At 10x traffic, repeated static prompt prefixes waste input-token billing and
prefill compute; caching and prefix sharing become material. At 100x, a large
few-shot prompt can dominate GPU prefill, reducing batching efficiency and
raising queue latency before output generation starts.

Long prompts also increase failure blast radius. A global prompt release can
change every request immediately. Use immutable versions, tenant-aware
canaries, fast rollback, and a compatibility matrix across model snapshots.
Do not silently edit a shared prompt in place.

## Production operations

Dashboard prompt version, model version, parse-failure rate, task success by
slice, input/output tokens, cache-hit rate, time-to-first-token, and refusal
rate. A runbook for rising parse failures should compare schema changes,
model changes, truncation, and raw response samples before adding retries.

A useful postmortem asks which layer failed: task specification, context
selection, instruction precedence, decoder constraint, output validation, or
downstream authorization. "The model hallucinated" is not a sufficient root
cause.

## Design and operations checklist

- [ ] Prompt and model configurations are immutable, versioned, and traceable.
- [ ] Acceptance tests contain difficult slices, not only happy paths.
- [ ] Untrusted content remains structurally distinct from instructions.
- [ ] Schemas constrain shape; validators and policy code constrain meaning and actions.
- [ ] Rollout supports shadowing, canaries, and immediate rollback.
- [ ] Prefix caching is measured rather than assumed.

## Cheat sheet

```text
instruction text  -> influences behavior
schema/grammar    -> constrains output tokens
validator         -> rejects bad semantics or shape
authorization     -> controls real-world capability
evaluation gate   -> detects regressions before rollout
```

## Test yourself

1. Explain why constrained decoding guarantees valid JSON but not a correct decision.
2. A prompt cache hit rate falls from 90% to 20%. Which prompt-layout change might cause it?
3. Design a rollout plan for a shared prompt used by 500 enterprise tenants.

## Further reading

- Anthropic, "Prompt engineering overview" and prompt caching documentation
- OpenAI, "Introducing Structured Outputs in the API"
- `ggerganov/llama.cpp`, grammar documentation and GBNF implementation
- Reynolds and McDonell, "Prompt Programming for Large Language Models"
- Wei et al., "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models"
