# Per-Language Tools — Senior

## Purpose

Reason from first principles across system boundaries. This guide keeps the topic practical: compare resolver, cache-key, hermeticity, and supply-chain properties across ecosystems.

## Before You Start

- Read the change, task, or build output end to end.
- State the expected result and the evidence that will prove it.
- Start with the smallest reproducible example; widen scope only when needed.

## Working Method

1. **Set the boundary.** Name inputs, outputs, owners, and assumptions.
2. **Find the important path.** Follow dependencies, data, control flow, or the review path from cause to effect.
3. **Check failure modes.** Include empty input, retries, partial failure, version drift, and concurrent work where relevant.
4. **Choose the smallest safe action.** Prefer an explicit rule, test, target, or documented decision over a workaround.
5. **Verify.** Repeat from a clean or independent state and record what changed.

## Core Ideas

- compare resolver, cache-key, hermeticity, and supply-chain properties across ecosystems.
- Correctness comes before speed or convenience; a fast wrong result is a defect.
- Make dependencies and contracts visible. Hidden inputs, implicit ownership, and unclear defaults create delayed failures.
- Keep work reversible: small changes, observable behavior, and a rollback path lower risk.
- Automate repeatable checks, but inspect the assumptions behind automation.

## Practical Checklist

- [ ] What must remain true before and after this work?
- [ ] Which inputs, versions, permissions, and environment values affect the result?
- [ ] What downstream targets, callers, reviewers, or users are affected?
- [ ] Does the happy path, failure path, and boundary case have evidence?
- [ ] Is the outcome understandable by the next engineer without oral history?

## Example: Make Evidence Explicit

```python
from pathlib import Path
import hashlib

def content_key(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.read_bytes())
    return digest.hexdigest()

assert content_key([Path("src/app.py")])
```

The example illustrates the habit, not a universal implementation: declare the relevant inputs, make ordering deterministic, and fail visibly when an assumption is missing.

## Common Failure Modes

- Treating a symptom as the cause; inspect the dependency or data path first.
- Trusting a local success that depends on undeclared state.
- Optimizing a metric without a quality counter-check.
- Making a broad change before proving a narrow one.
- Leaving a decision undocumented, so the same argument returns later.

## When to Escalate

Escalate when the work changes a public contract, trust boundary, data model, platform support, release behavior, or another team’s ownership. Bring a short problem statement, alternatives, evidence, and a recommended reversible next step.

## Practice

1. Pick one recent change in this area. Write its expected result, key inputs, failure mode, and verification command.
2. Identify one hidden assumption. Decide whether to declare it, test it, or remove it.
3. Explain the trade-off to a teammate in three sentences.

## Takeaway

You should be able to expose hidden assumptions, set strategy, and handle difficult trade-offs. Keep the loop simple: make the contract explicit, test the risky path, measure the result, and improve the system that produced it.
