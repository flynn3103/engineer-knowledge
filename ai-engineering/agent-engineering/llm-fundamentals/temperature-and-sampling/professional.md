# Temperature and Sampling — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you set sampling defaults as an org standard — and stop "creative" settings from leaking into the paths that must stay deterministic?

---

## Defaults as policy, not preference

- Publish org-wide defaults per task class: extraction/structured → 0–0.2; analytical → 0.3–0.7; creative → 0.8+, *only* where the spec demands novelty.
- The standard exists because individual choices drift: each team copies a demo, raises a number to "make it less boring," and the org accumulates unexplainable settings. Defaults make the boring choice the easy choice.

## Stopping creative leakage

- The failure pattern: a demo, a prototype, or one team's copywriting preset becomes a shared client default — and every downstream task inherits randomness it never asked for.
- Concrete controls:
  - Sampling settings live **per task, next to the prompt**, in config — never as a global client default.
  - Structured-output and tool-calling paths get a lint/CI rule: low temperature is required, higher values fail the build.
  - Any request to exceed a class default states *why the spec values novelty* — the burden of proof sits with the raise, not the default.

## Settings in the trace

- Record temperature, top-p, and seed on every trace (see [Tracing and Observability](../../agent-evaluation/tracing-and-observability/)) — half of "model quality" incidents are settings incidents, and you can't see that without the record.
- Aggregate settings across services periodically: the audit finds the leaked 1.0s and the inherited demo values.

## Testing standards org-wide

- Standardize the repeat-count and rate-assertion approach from [Senior](senior.md): no exact-match assertions on free text, N repeats, rate thresholds as gates.
- Tie it to the eval pipeline: eval suites encode the sampling settings under test, so a "pass" is meaningless without knowing the settings it ran at.

## Common Mistakes

- **A defaults document nobody enforces.** Leakage is prevented by CI rules and config structure, not prose.
- **Global client defaults.** One setting for all tasks is the mechanism leakage exploits.
- **Settings invisible in traces.** Incidents get attributed to "model quality" and the real cause survives the postmortem.
- **Raising a default to fix a complaint.** Inconsistency complaints are diagnostic material (see [Senior](senior.md)), not a reason to add randomness.

## Apply It

1. Publish the per-task-class defaults; name an owner for the document.
2. Move every sampling setting in your services into per-task config; add a CI rule that fails structured-output paths with high temperature.
3. Add temperature/top-p/seed to your trace schema; audit current production values against the policy.
4. Standardize the N-repeats + rate-assertion testing pattern in your eval suite.

## Verify Your Work

- No global sampling default exists anywhere in production code.
- Structured-output paths enforce low temperature mechanically, not by convention.
- Every trace records the sampling settings used.
- The defaults document has an owner and production values have been audited against it.

## Review Questions

- Why must the burden of proof sit with raising a temperature, not with the default?
- What two mechanical controls stop creative settings leaking into deterministic paths?
- Why does a "model quality" postmortem fail without settings in the trace?
