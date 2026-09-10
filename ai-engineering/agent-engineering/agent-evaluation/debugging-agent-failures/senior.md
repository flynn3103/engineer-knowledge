# Debugging Agent Failures — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you root-cause a failure that only emerges across multiple steps, and tell a provider-side model regression apart from a regression you introduced yourself?

---

## Cascading errors

- A small, subtle error early in a run (a slightly wrong summary of a tool result, a mildly ambiguous instruction) may not look like a failure at that step in isolation — it only becomes visibly wrong several steps later, once it's compounded by steps built on top of it.
- Debug by checking each step not just for "is this step wrong on its own" but "is this step's *input* exactly what a correct upstream step would have produced" — the divergence is often subtle enough to miss without that comparison.

## Context pollution and poisoning

- **Context pollution**: irrelevant or stale information accumulates in the agent's context across steps (e.g., an old tool result from three steps ago that's no longer relevant but still present), degrading the model's ability to attend to what currently matters.
- **Context poisoning**: a specific wrong fact (a hallucination or a wrong tool result) enters the context and gets treated as true in every subsequent step, since the model has no way to distinguish "this earlier statement was actually wrong" without an explicit correction mechanism.
- Both are diagnosed by checking whether removing or correcting the suspect context content and replaying the remaining steps produces the correct outcome.

## Non-determinism only visible under specific conditions

- A failure that occurs at non-zero temperature but not at temperature zero is telling you the failure sits in the model's variance, not in your logic — worth confirming by running the exact same input at both settings before spending time on a code-level fix that won't touch a sampling-variance issue.
- A failure that only occurs under concurrent load (but not when replayed alone) suggests a race condition or shared-state bug in your orchestration code, not the model — replay alone won't reproduce it; you need a concurrent-load repro instead.

## Provider-side regression vs. your regression

- When behavior changes with no corresponding change on your side (no prompt edit, no code deploy), check: did the model version silently update (many providers auto-update a model alias to a newer underlying version), did an upstream dependency's API contract change, did the input distribution shift (new customer segment, new product line).
- Confirm by testing the same input against a pinned/known-good model version if available — if the failure disappears, it's provider-side; if it persists, keep looking in your own code and data.

## Incident workflow

- **What to capture immediately**: the failing trace(s), the model/prompt version in use at the time, recent deploys or config changes, and the scope (how many customers/runs affected).
- **How to roll back a prompt**: keep prompt versions in version control with a fast rollback path — pinning to the last known-good version should be a single deploy, not a multi-step manual reconstruction under pressure.
- **Kill switch**: for a high-risk agent, have a way to disable the automated path entirely and fall back to full human handling while the root cause is being investigated, rather than leaving a known-broken agent running against real customers.

## Common Mistakes

- **Judging each step only in isolation, missing cascading errors.** A step can look locally reasonable while still being wrong because of what it inherited from an upstream mistake.
- **No context-poisoning check.** Assumes every piece of context is equally trustworthy, missing that one earlier wrong fact can corrupt every subsequent step that reads it.
- **Assuming a behavior change is your bug without checking for a provider-side model version change first.** Wastes debugging time on code that isn't the actual cause.
- **No fast prompt-rollback path.** Turns an incident into a slow manual reconstruction instead of an immediate mitigation.

## Apply It

1. For a failure that seems to emerge gradually, compare each step's actual input against what a correct upstream step should have produced, to find where divergence actually started.
2. Check whether a suspected context-poisoning case resolves when the offending earlier content is manually corrected and the rest of the run replayed.
3. Confirm whether a recent behavior change correlates with a model version update, a dependency change, or an input-distribution shift, before assuming it's a bug in your own logic.
4. Confirm a prompt rollback and a kill switch both exist and can be executed in under a defined time target (e.g., 5 minutes) for your highest-risk agent.

## Verify Your Work

- The root cause identified is the earliest point of divergence, confirmed against the correct upstream input, not just the most visible failure point.
- A context-poisoning hypothesis is tested by correction-and-replay, not assumed.
- A provider-side change is ruled in or out before concluding the bug is in your own code.
- A prompt rollback and kill switch exist and are tested, not theoretical.

## Review Questions

- Why can a step look locally correct while still being the actual cause of a downstream failure?
- What's the difference between context pollution and context poisoning, and how do you test for poisoning specifically?
- Why check for a provider-side model version change before assuming a behavior regression is your own bug?
