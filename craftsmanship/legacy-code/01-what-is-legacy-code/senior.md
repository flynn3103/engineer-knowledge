# What Is Legacy Code — Senior

## Treat legacy as a system property

- A system is legacy when a small change has a disproportionately large, unpredictable cost or risk.
- The target is not “old code elimination” or a coverage number. It is **cheap, predictable change**.
- Tests matter because they restore the fast feedback that keeps risk proportional to the change.

## Read fear, risk, and feedback as data

| Signal | What it causes | Useful response |
| --- | --- | --- |
| Engineers avoid a module | Copy-paste and workarounds | Add feedback around the next change. |
| Unknown dependencies | Large blast radius | Map seams and dependencies. |
| Defects found late | Expensive recovery | Move detection into local and CI tests. |

- Fear is not a personal failure; it is a signal that feedback is missing.
- Break the loop at feedback. It is the part engineers can directly improve.

```text
missing feedback → risky change → avoidance and duplication
      ↑                                      ↓
      └──────── complexity and fear ─────────┘
```

## Manage compounding cost

- Untested hot code gets harder to understand with every change.
- Each production defect can add hotfixes, hidden behavior, and more caution.
- Knowledge decays as authors leave; characterization tests preserve the contract.
- Cover code the next time it is touched. Waiting normally increases the price.

## Protect against key-person risk

1. Identify modules that only one person can safely change.
2. Pair that person with another engineer on the next change.
3. Turn important observed behavior into characterization tests.
4. Record known boundaries, risks, and ownership.
5. Re-check the risk after the expert is no longer required for ordinary changes.

## Choose a proportional strategy

| Situation | Strategy |
| --- | --- |
| Small, high-risk change | Characterize the narrow behavior, then modify it. |
| Frequently changed hotspot | Incrementally build a fast regression suite. |
| Expensive-to-test component with a clean edge | Put a seam around it and replace it gradually. |
| Stable, low-risk code | Defer; do not start a cleanup campaign without a pull. |

## Hold the important tensions

- **Preserve behavior vs. improve it:** first pin current behavior, then make intended changes visible in tests.
- **Local safety vs. broad cleanup:** buy enough safety for the next change; avoid a speculative rewrite.
- **Speed today vs. compounding cost:** state the risk explicitly and choose deliberately.
- **Coverage quantity vs. useful feedback:** test business-critical behavior, not implementation trivia.

## Senior operating checklist

- [ ] Change cost is visible through lead time, incidents, or rework.
- [ ] Hot, risky modules have a feedback-improvement path.
- [ ] Characterization tests capture knowledge that would otherwise leave with people.
- [ ] The team can explain why it is covering, deferring, replacing, or strangling an area.

## Recall questions

- What makes legacy a system-level problem?
- Why does fear create structural problems such as duplication?
- When is a gradual replacement better than deeper test investment?
