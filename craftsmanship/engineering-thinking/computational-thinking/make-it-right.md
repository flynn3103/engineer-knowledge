# Computational Thinking — Make It Right

Common mistakes at each move, and how to catch them.

## Decomposition mistakes

- **Splitting into tasks instead of parts you can check independently.** "Implement login" cut into 50 steps that only make sense together isn't decomposition — it's a to-do list.
  - Fix: each part should be understandable and checkable on its own, like a wheel is still a wheel off the bike.
- **Boundary too large.** "The whole system" isn't a decomposed part — you can't reason about something you can't hold in your head.
  - Fix: keep splitting until each piece is small enough to fully understand.
- **Boundary too small.** A single line isn't a part either — you lose the shape of the problem.
  - Fix: a part should map to one recognizable piece of the original problem (one bike component, not one bolt).

## Pattern recognition mistakes

- **Calling something a pattern after seeing it once.** One occurrence is a coincidence, not a pattern.
  - Fix: a real pattern shows up across multiple decomposed parts, not just one.
- **Forcing two different things into one pattern.** "Validate email" and "validate discount code" look similar but check different rules — merging them too early hides that difference.
  - Fix: confirm what's actually shared (the shape: "check, then reject with a reason") before merging what differs (the rule itself).

## Abstraction mistakes

- **Abstracting away detail the caller actually needs.** If "resize image" hides *whether it succeeded*, the caller can't handle failure.
  - Fix: abstraction removes irrelevant detail, never relevant behavior.
- **Not abstracting at all.** Exposing every internal detail (raw bytes, storage path, retry count) to the caller means every internal change breaks every caller.
  - Fix: name what the caller needs (`save(bytes) -> url`) and hide the rest.

## Algorithm mistakes

- **Skipping the plan and going straight to code.** You end up debugging logic you never actually wrote down anywhere.
  - Fix: write the ordered steps in plain language first, even five bullet points.
- **No clear stop condition.** An algorithm without a defined end runs forever or fails unpredictably.
  - Fix: state the starting point, the finishing point, and every step between, explicitly.
- **Only describing the happy path.** The steps work when everything succeeds and fall apart the moment one step fails.
  - Fix: for every step, decide what happens on failure before moving to the next one.

## The optimization mistake (it deserves its own section)

- **Optimizing before measuring.** Programmers are frequently wrong about where a program is actually slow — the "obvious" bottleneck usually isn't the real one.
  - Fix: profile first, find where time/resources actually go, then optimize that spot. In practice, a small fraction of the code accounts for most of the resource use — optimize that fraction, not your guess.
- **Optimizing too early, at the cost of clarity.** A "fully optimized" version that nobody can read introduces more bugs than it prevents, and most micro-optimizations save only a few percent.
  - Fix: get the algorithm right first — algorithm-level improvements dwarf micro-optimizations. Only optimize source-level detail once the design and algorithm are already sound.
- **Optimizing something that will change anyway.** Polishing a part of the solution that's about to be redesigned wastes the work twice.
  - Fix: optimize after the design has stabilized, not before.

## The meta-mistake

- **Treating this as a one-time pass before coding, not a loop.** The four moves aren't linear — abstraction can reveal a pattern you missed, a bad algorithm can mean the decomposition was wrong.
  - Fix: after evaluating (understood / complete / efficient / on-spec), go back to whichever move the failure points to — don't just patch the symptom in the code.

Continue to [Make It Scale](make-it-scale.md).
