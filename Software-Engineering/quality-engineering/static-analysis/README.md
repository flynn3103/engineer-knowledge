# Static Analysis & Linting

> Tools that read your source code without running it — linters, formatters, type-checkers, security scanners, and data-flow engines that find bugs, enforce style, and trace tainted input at the speed of a keystroke.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Linters & Style Checkers](01-linters-and-style-checkers/junior.md) | What a linter proves vs. enforces; rule classes, severity, the false-positive budget |
| 02 | [Formatters](02-formatters/junior.md) | Deterministic rewriting vs. lint; gofmt/Prettier/Black/rustfmt; format-on-save |
| 03 | [Type Checkers & Gradual Typing](03-type-checkers-and-gradual-typing/junior.md) | mypy/pyright, TypeScript, Flow; soundness vs. ergonomics, strictness ratchets |
| 04 | [SAST & Security Scanners](04-sast-security-scanners/junior.md) | Semgrep, CodeQL, Bandit, gosec; sources/sinks, rule packs, signal-to-noise |
| 05 | [Dead Code & Complexity](05-dead-code-and-complexity/junior.md) | Unused code/imports, cyclomatic & cognitive complexity, reachability |
| 06 | [Dependency & License Scanning](06-dependency-and-license-scanning/junior.md) | SCA, CVE matching (OSV/Trivy/Dependabot/Snyk), license compliance |
| 07 | [Custom Lint Rules & AST](07-custom-lint-rules-and-ast/junior.md) | ASTs and matchers; writing Semgrep rules, ESLint plugins, codemods |
| 08 | [Taint & Data-Flow Analysis](08-taint-and-dataflow-analysis/junior.md) | Interprocedural data-flow; sources, sinks, sanitizers, propagation |
| 09 | [Static Analysis in CI](09-static-analysis-in-ci/junior.md) | Editor → pre-commit → CI placement; baselines, blocking vs. advisory gates, SARIF |

## How to use this section

Each topic has four depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank. Start at your level and climb.

---

> Part of the [Quality Engineering](../README.md) roadmap.
