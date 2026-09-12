# Computational Thinking — Make It Scale

How to make the four moves automatic, not effortful.

## Daily practice

- **Before every ticket:** write the decomposed parts before writing any code. Time-box it to 10 minutes.
- **Before merging a PR:** ask "is each part here checkable on its own?" — not just "does the whole thing work end to end?".
- **Before optimizing anything:** measure first. Don't trust intuition about where the slow part is — profile it, then fix the actual bottleneck.

## Build the habit

- **Keep a decomposition log.** For one month, write the parts, the pattern, and the algorithm before coding — even on trivial tasks. Review weekly: which parts turned out wrong, and why?
- **Practice waiting for the real pattern.** When you see something twice, say "not yet, I need a third example" before you abstract it.
- **Re-derive one existing abstraction per month.** Pick something already in the codebase, pretend it doesn't exist, and decompose the problem again from scratch. Compare with what's there — does it still hold up?
- **Profile before you touch performance code, every time.** Make it a rule with no exceptions, until it's automatic.

## Level up as scope grows

- **Solo task →** decompose into parts, name one pattern, write the algorithm, evaluate against the four checks.
- **Shared module →** the abstraction has to survive someone else calling it without asking you first.
- **Whole system →** the decomposition has to survive the system changing shape later — a part should still make sense on its own after the rest of the system moves.

## Self-check before calling it done

- [ ] Can I check any single part without the rest existing yet?
- [ ] Did I confirm the pattern shows up more than once before abstracting it?
- [ ] Does the abstraction hide only irrelevant detail, never relevant behavior?
- [ ] Did I write the algorithm's steps down before writing the code?
- [ ] Did I evaluate against all four checks: understood, complete, efficient, on-spec?
- [ ] If I optimized anything, did I measure first?

## Signs you're getting fluent

- You decompose a problem before anyone asks you to.
- You wait for the third occurrence before reaching for an abstraction.
- You reach for a profiler instead of a guess when something feels slow.
- You can explain your algorithm's steps to someone else without opening the code.
