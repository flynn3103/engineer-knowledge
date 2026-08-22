# Quality Engineering

The disciplines that turn _code that compiles_ into _code that survives production_. Language-agnostic, applies across the [languages/](../languages/) tracks.

---

## Sections

### The three pillars

- **[Testing](testing/)** — taxonomy (unit / integration / contract / E2E / property / fuzz / mutation / load / snapshot), test doubles, coverage, flakiness, fixtures, TDD/BDD.
- **[Performance](performance/)** — measurement, profiling (CPU / memory / allocation / flame graphs), benchmarking, latency budgets, memory, concurrency overhead, regression detection.
- **[Build Systems](build-systems/)** — dependency management, reproducible builds, CI build optimisation, caching, supply-chain hardening, cross-compilation.

### Code-level quality signals

- **[Static Analysis & Linting](static-analysis/)** — linters, formatters, type-checkers, SAST; what can be proved without running the code.
- **[Code Coverage](code-coverage/)** — line / branch / mutation coverage; the diagnostic value vs the "coverage as KPI" trap.
- **[Code Quality Metrics](code-quality-metrics/)** — cyclomatic / cognitive complexity, coupling & cohesion, churn & hotspots, duplication, maintainability index, health dashboards.
- **[Code Review](code-review/)** — the engineering side: what to look for, in what order, how to give technically useful feedback.

### Deeper verification

- **[Dynamic Analysis & Sanitizers](dynamic-analysis-and-sanitizers/)** — ASan / TSan / UBSan / Valgrind, coverage-guided dynamic analysis, runtime contracts; the memory-safety and concurrency bugs you can only catch by *running* the code.
- **[Formal Methods & Verification](formal-methods-and-verification/)** — formal specs, model checking, TLA+, property/contract verification, proof assistants; *proving* properties instead of testing for them — and when that's worth it.

### Release & operational quality

- **[Release Engineering](release-engineering/)** — versioning (semver / calver), changelogs, RC / GA flow, artifact signing, SBOMs, rollback, deprecation policy.
- **[Quality Gates](quality-gates/)** — the policy layer that decides "is this change allowed to merge / deploy?"; required CI checks, branch protection, merge queues, deploy gates.
- **[Documentation Quality](documentation-quality/)** — Diataxis, API docs, runbooks, ADRs, doc-as-code, doc testing.

### Measuring & managing quality

- **[Engineering Metrics & DORA](engineering-metrics-and-dora/)** — the DORA four keys, flow metrics, the SPACE framework, lead/cycle time, reliability metrics; using metrics to improve without falling into Goodhart's law.
- **[Technical Debt Management](technical-debt-management/)** — what debt actually is, the debt quadrant, measuring it, prioritising paydown, and stopping its accumulation.

---

## Related

- **[Design Patterns](../design-patterns/README.md)**, **[Refactoring](../refactoring/README.md)**, **[Anti-Patterns](../anti-patterns/README.md)** — the design side; this section is the verification and operational side.
- **[Soft Skill › Engineering Thinking › Diagnostics & Observability Thinking](../../Soft-Skill/engineering-thinking/11-diagnostics-and-observability-thinking/)** — what to do when quality fails in production.
