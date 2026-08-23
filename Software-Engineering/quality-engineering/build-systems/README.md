# Build Systems

> How source code becomes a runnable artifact — compilation, linking, packaging, dependency resolution, and the tooling that orchestrates it all reproducibly.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Build Fundamentals](01-build-fundamentals/junior.md) | Compile / assemble / link, static vs. dynamic linking, the C ABI |
| 02 | [Dependency Graphs](02-dependency-graphs/junior.md) | DAGs, topological order, incremental rebuilds, the "diamond problem" |
| 03 | [Make & Descendants](03-make-and-descendants/junior.md) | `make`, `ninja`, `meson`, `cmake` — the lineage and why they exist |
| 04 | [Per-Language Tools](04-per-language-tools/junior.md) | `go build`/`go mod`, `cargo`, `gradle`/`maven`, `pip`/`poetry`/`uv`, `npm`/`pnpm`/`bun` |
| 05 | [Polyglot / Hermetic Builds](05-polyglot-hermetic-builds/junior.md) | `bazel`, `buck2`, `pants` — when one tool must build everything reproducibly |
| 06 | [Dependency Management](06-dependency-management/junior.md) | Semantic versioning, lock files, Minimum Version Selection, vendoring |
| 07 | [Build Caching](07-build-caching/junior.md) | Local caches, remote caches, content-addressable storage, build farms |
| 08 | [Cross-Compilation](08-cross-compilation/junior.md) | Building for a target that isn't your host |
| 09 | [Reproducible Builds](09-reproducible-builds/junior.md) | Bit-identical outputs, timestamps, paths, `SOURCE_DATE_EPOCH` |
| 10 | [Build Performance](10-build-performance/junior.md) | Parallelism, fan-out, profiling slow builds, the cost of incremental |

## How to use this section

Each topic has four depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank. Start at your level and climb.

---

> Part of the [Quality Engineering](../README.md) roadmap.
