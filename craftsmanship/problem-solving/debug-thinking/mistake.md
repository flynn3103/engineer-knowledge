# Debug-Thinking — Mistake

Common mistakes at each move, and how to catch them.

- **Changing code before reproducing the bug.** If you edit first and the symptom goes away, you don't know whether you fixed it or just changed timing.
  - Fix: reproduce it on demand first, every time, before touching anything.
- **Shotgun debugging — making undirected changes and seeing if the symptom goes away.** Wikipedia names this exact pattern: "attempting to correct a bug by making largely undirected source code modifications, sometimes resulting in further problems." Changing several things at once means that even if it works, you don't know which change mattered, and the bug can resurface later under a different trigger.
  - Fix: one hypothesis, one test, one variable changed at a time.
- **Writing an unfalsifiable hypothesis.** "Something with the database" or "something with images" can't be proven wrong — there's no specific observation that would contradict it.
  - Fix: name a file, a function, or a line, and a fact about it that could turn out false. In the upload example, "the size check runs after the file is loaded into memory" is falsifiable; "the upload code is broken" is not.
- **Fixing the symptom instead of the cause.** Wrapping the failing call in a `try/catch` that silences the error makes the crash disappear without explaining it — the bug is still there, just quieter.
  - Fix: the fix must explain the specific piece of evidence you found (the exact stack trace, the exact wrong value), not just make the immediate error go away.
- **Reading the failure surface linearly instead of bisecting it.** Checking commits one at a time from newest, or reading a whole call chain top to bottom, doesn't scale once the failure could be anywhere in dozens of commits or several services.
  - Fix: cut the remaining space in half at every step — the same "wolf fence" logic `git bisect` automates for commit history works just as well on a call chain or a data pipeline (checkpoint the midpoint, see which side still reproduces the failure).
- **Trusting one signal when the bug crosses a boundary.** A log showing `200 OK` and a downstream system showing a decline aren't contradictory — they're different points in the same chain, and the bug lives in the gap between them.
  - Fix: correlate signals from every system the request touched, lined up by a shared key (request ID, user ID, timestamp), before picking a hypothesis.
- **Treating correlation as causation.** "It broke right after the deploy" is a timing correlation, not yet a causal mechanism.
  - Fix: state *how*, specifically, the suspected change could produce the symptom, and check whether removing it (rollback, flag off) actually resolves the failure.
- **Declaring victory without re-running the original reproduction steps.** A fix that "looks right" in the code, or makes the immediate symptom disappear once, hasn't been verified.
  - Fix: always re-run the exact trigger from the first reproduction step after the fix, including the case that used to work, to confirm you didn't break it.
- **Verifying a production-scale fix by comparing before-and-after over time, instead of canarying it concurrently.** "Errors dropped after the deploy" doesn't rule out something else changing at the same time — traffic volume, an upstream dependency recovering, a scheduled job ending.
  - Fix: roll the fix out to a random slice of traffic at the same time as the unfixed path, so anything else that changed doesn't get credited to your fix.
- **Optimizing for a vanity signal instead of the one the hypothesis actually predicted.** Checking that overall error rate looks better, when the hypothesis was specifically about *this* error on *this* endpoint, can hide the original bug still happening at a lower rate.
  - Fix: measure the exact signal named in the hypothesis card, not a broader number that merely looks reassuring.
- **Exploring an unclear mechanism with no time limit.** "Let me just check one more thing" without a falsifiable hypothesis yet can run for hours with nothing to show for it.
  - Fix: timebox the exploration. "We don't understand this yet" at the end of the timebox is a valid, reportable result — it's not a reason to keep going unannounced.

Continue to [Best Practise](best-practise.md).
