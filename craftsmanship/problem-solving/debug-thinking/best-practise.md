# Debug-Thinking — Best Practise

How to make reproduce-hypothesize-test-verify a habit, not a special occasion.

## The core techniques

- **The Wolf Fence algorithm (bisection).** Edward Gauss described it in a 1982 *Communications of the ACM* piece: "There's one wolf in Alaska; how do you find it? First build a fence down the middle of the state, wait for the wolf to howl, determine which side of the fence it is on. Repeat process on that side only, until you get to the point where you can see the wolf." Git automates exactly this loop as `git bisect` to find which commit introduced a bug — the same halving move works on a call chain or a data pipeline, not just commit history.
- **Rubber duck debugging.** Coined in *The Pragmatic Programmer* (Andy Hunt & Dave Thomas): explain your code, step by step, to a rubber duck, a colleague, or anything that will listen. The listener doesn't need to say a word — the act of stating out loud what the code is *supposed* to do, next to what it *actually* does, is often what makes the gap visible. It works better than silently thinking it through, even when nobody's really listening.
- **The hypothesis card.** Barry O'Reilly's Hypothesis-Driven Development template, adapted for a bug: **We Believe** `<this is the cause>` — **We Will Have Confidence To Proceed When** `<this specific observation>`. Naming the confirming signal before you test keeps you from unconsciously moving the goalposts once you see the result.

## Daily practice

- **Before every ticket you're debugging, write expected vs. actual in one sentence each**, before opening the debugger.
- **Read the actual error output word by word before forming a theory.** Most bugs are solved by the error message alone, not by intuition.
- **Change exactly one thing before re-testing.** If you're tempted to change three things at once, that's the shotgun-debugging pattern — stop and pick one.
- **Reach for bisection as soon as "read the whole thing" stops being feasible** — a failing range of commits, a multi-service call chain, or a long data pipeline are all bisectable the same way.
- **When a fix is going to production at real scale, canary it to a random slice of traffic concurrently with the unfixed path**, and check the specific signal your hypothesis predicted — not just that things feel better.

## Build the habit

- **Keep a bug journal.** For each bug: the reproduction steps, the hypothesis, what disproved or confirmed it, and the fix. Review monthly — which bugs took far longer than they should have, and why?
- **Build a shared failure-pattern library from your own system's actual bugs** (off-by-one, stale cache, race condition, N+1 query, silently-swallowed partial failure), not generic textbook examples — so the next person can pattern-match instead of starting from zero.
- **Narrate your hypothesis out loud during code review**, not just when stuck — "here's how I'd verify this is correct, here's what would tell me it's wrong in production" builds the habit before code ships.

## Level up as stakes grow

- **One bug, one function →** reproduce, one falsifiable hypothesis, cheap test, verify. The full loop above is enough.
- **A failure that crosses a call chain, a range of commits, or several services →** bisect to find *where* before you ask *why*, and correlate signals across every system involved by a shared key instead of trusting the most convenient log.
- **A failure no single component caused (retry storms, cascading failure, resource exhaustion under a specific load shape) →** mitigate on a plausible, reversible hypothesis first (roll back, flip a flag) — you don't need full certainty to stop the bleeding — then model the shared resources (pools, locks, rate limits) between components, not just the call graph, to find the actual mechanism. Once you have a fix, validate it the same way you'd validate any hypothesis: canary it, measure the specific signal, and only call it resolved once that signal — not just the absence of complaints — confirms it.
- **A team that depends on one person to find anything →** that's a bus-factor problem, not a hiring problem. Pair on real incidents so the reasoning transfers, not just the fix; run debugging retrospectives framed around "what signal would have helped," never "who missed it"; track bus factor and time-to-first-plausible-hypothesis, not just time-to-resolution — the latter alone rewards heroics from one expert instead of showing whether the skill is spreading.

## Self-check before calling it done

- [ ] Did I reproduce the bug on demand before changing anything?
- [ ] Is my hypothesis falsifiable — is there an observation that could prove it wrong?
- [ ] Did I change exactly one thing before re-testing?
- [ ] Did I bisect instead of reading linearly, once the failure surface got too large to hold in my head?
- [ ] Does the fix explain the specific evidence I found, not just make the symptom go away?
- [ ] Did I re-run the original reproduction steps — including the case that used to work — to verify?
- [ ] If this fix ships to real traffic, did I validate it with a concurrent, randomized canary instead of a before/after comparison?

## Signs you're getting fluent

- You reproduce first, automatically, before your hands go anywhere near a fix.
- You reach for bisection the moment "read everything" stops being realistic.
- You explain the bug out loud (to a person or a rubber duck) before you're stuck, not just after.
- You write the hypothesis as a card — cause and confirming signal — before you go looking for it.
- Your postmortems and PRs describe a reasoning trail someone else could follow, not just the fix.
