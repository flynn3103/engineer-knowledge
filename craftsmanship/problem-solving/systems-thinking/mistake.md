# Systems Thinking — Mistake

## When it's worth doing, and when it's not

- **Do it when:** the same problem keeps coming back after you "fix" it, or the system has retries, caches, queues, or shared numbers that people are measured on — anywhere something coming out can go back in as an input.
- **Do it when:** you're about to change a number (a timeout, a retry count, a limit) while the system is under real load — that's exactly where a loop that feeds on itself can turn a small change into a bigger outage.
- **Skip it when:** the problem really is simple and one-way — one clear cause, no loop, nothing feeding back. Not every bug needs a loop diagram.
- **The real cost:** mapping the parts and the loop takes longer than just patching what broke. Doing this for every tiny, obvious problem is its own way of wasting time.

## Mistakes when drawing the system

- **Calling the whole codebase or the whole company "the system."** Too big — you can't trace a loop through something you can't fully see.
  - Fix: draw the smallest area that still contains the loop you're chasing.
- **Calling one function "the system."** Too small — the loop closes somewhere outside it, so you'll never spot it.
  - Fix: zoom out until you can see the arrow that comes back to where you started.
- **Treating something you don't own as a magic box that "just works."** Ignoring how it slows down or fails under load hides half the loop.
  - Fix: treat its response time or error rate as something that changes, not a fixed number.

## Mistakes about where the problem really is

- **Fixing the symptom, and the fix backfires later.** A quick patch stops the visible problem today, but it quietly causes a new problem that shows up later and makes things worse.
  - Fix: before you ship a fix, ask "and then what happens because of that?" twice.
- **Patching around the hard problem instead of fixing it.** The real problem is hard or awkward to fix, so a quick patch gets used instead — and the quick patch makes the real fix even harder to do later.
  - Fix: write down what the real fix would be, even if you're choosing the quick patch for now. Don't let the patch quietly become the whole plan.
- **Assuming cause and effect only run one way.** "A caused B" and stopping there, without checking if B also feeds back and changes A.
  - Fix: ask directly, "does this ever loop back around and become an input again?"

## Mistakes when naming the loop

- **Changing a number inside a loop that never stops on its own.** A bigger retry count or a longer timeout doesn't fix the fact that nothing stops the loop — it just moves the point where it breaks.
  - Fix: check if the loop has something built in that stops it. If not, add one (a hard cap, a circuit breaker) instead of a bigger number.
- **Calling a loop "broken" just because it goes up and down.** Some things — autoscalers, rate limiters — are supposed to hunt back and forth around a target. That's not broken.
  - Fix: check whether it's settling toward a target, not whether it looks perfectly flat.
- **Expecting things to grow in a straight line.** People are bad at guessing how fast something builds up on its own — a backlog, a cost, a slow cache — because it doesn't grow in a straight line, it speeds up.
  - Fix: watch the trend over time, not one snapshot. If a number keeps climbing after the thing that triggered it is over, that's a loop still feeding itself.
- **Calling a fix "done" right after you ship it.** A fix that only accounts for the fast-moving part of a loop can still fail weeks later once a slow-moving part (a cache that takes time to refill, a system that takes time to warm back up) catches up.
  - Fix: name the slowest-moving thing in the loop, and check your fix still holds once that catches up too.

## The one mistake underneath all of these

- **Jumping straight to the first fix that seems to make sense.** This skips tracing the loop entirely — the same mistake as recombining into the first option instead of generating a few, covered in [First-Principles Thinking](../first-principles-thinking/README.md).
  - Fix: trace the loop and name its kind before proposing any fix — every time, not just after the first fix has already failed once.

Continue to [Best Practise](best-practise.md).
