# Testing Anti-Patterns

> Named shapes of bad tests that make a suite lie — staying green while the code is broken, flipping red when nothing changed, or growing so slow and brittle the team quietly stops running it.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Fragile Tests](01-fragile-tests/junior.md) | A test breaks on a change that didn't change behavior; testing behavior through the public API, not internals |
| 02 | [Flaky Tests](02-flaky-tests/junior.md) | Same code, same test, different result run to run; controlling time, awaiting conditions, isolating state, seeding randomness |
| 03 | [Mystery Guest](03-mystery-guest/junior.md) | A test depends on data you can't see in the test; making fixtures local and explicit |
| 04 | [Assertion Roulette](04-assertion-roulette/junior.md) | Many unlabelled assertions where you can't tell which failed; one logical assertion per test |
| 05 | [Slow Tests](05-slow-tests/junior.md) | A suite so slow nobody runs it before pushing; the test pyramid, fakes over real I/O, parallelization |
| 06 | [Over-Mocking](06-over-mocking/junior.md) | Tests that assert on mocks instead of behavior and break on every refactor; mocking only at real boundaries |

## How to use this section

Each topic has five depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank and hands-on **tasks**. Each topic folder also includes `find-bug.md` (spot-the-test-smell drills) and `optimize.md` (refactor the bad test). Start at your level and climb.

---

> Part of the [Anti-Patterns](../README.md) roadmap.
