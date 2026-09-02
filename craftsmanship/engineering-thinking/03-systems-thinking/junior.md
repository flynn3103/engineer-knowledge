# Systems Thinking — Junior

**Your question:** What are this system's actual boundaries, connections, and at least one feedback loop inside it?

"The checkout error rate spiked" tells you where a symptom was *observed*, not where the problem *lives*. A system is not the file where the error was thrown — it's the set of components, the connections between them, and the loops those connections form. If you fix the file that logged the error without seeing the loop it sits in, you fix the symptom and leave the loop running.

## The method: map, then trace one loop

1. **List the actual components.** Not "the checkout code" — name the concrete pieces: `CheckoutService`, `PaymentGateway` (external), `RetryQueue`, `InventoryService`, `ProductCache`.
2. **Draw the connections.** For each pair, name what moves and in which direction: `CheckoutService → PaymentGateway` (charge request), `PaymentGateway → CheckoutService` (response or timeout), `CheckoutService → InventoryService` (reserve stock).
3. **Decide the boundary.** What's inside the system you're reasoning about, and what's an external input or output? You don't control `PaymentGateway`'s internals, but its response time is a variable that affects your system — treat it as an external actor with behavior, not a black box that only ever returns "success."
4. **Trace one signal all the way around.** Find a place where an output eventually becomes an input again. That circle is a feedback loop. If you can't find one, you haven't traced far enough — most systems with retries, caches, or queues have at least one.
5. **Separate symptom from origin.** The symptom is what you observed (checkout returns 500). The origin is where in the loop the behavior actually starts (payment gateway latency climbing under retry load). They are rarely the same place.

## A concrete example

**Symptom:** Checkout error rate jumps from 0.3% to 8% during a Friday traffic peak.

**Components:** `CheckoutService`, `PaymentGateway` (external, fixed capacity), `RetryQueue`, `InventoryService`.

**Connections:**
```
Client -> CheckoutService -> PaymentGateway (charge)
PaymentGateway -> CheckoutService (response, or timeout after 3s)
CheckoutService -> RetryQueue (on timeout, retry after 2s)
RetryQueue -> PaymentGateway (retry attempt)
```

**Boundary:** `CheckoutService`, `RetryQueue`, and `InventoryService` are inside the system you own and can change. `PaymentGateway` is outside your boundary — you can't change its code, but its saturation behavior is part of the system you're reasoning about.

**The loop:**
```
More traffic -> more charge requests -> PaymentGateway queue grows
  -> PaymentGateway latency climbs -> requests exceed the 3s timeout
  -> CheckoutService enqueues a retry -> retry adds another request
  -> PaymentGateway queue grows further (back to start)
```

**Symptom vs. origin:** The 500 errors are *observed* in `CheckoutService`'s response handler. The problem *originates* in the loop between retry volume and gateway saturation — `CheckoutService`'s code is working exactly as written. A junior fix that adds a `try/catch` around the charge call, or "improves error messages," touches the symptom's location and leaves the loop untouched.

## Recognize common feedback-loop shapes

Most junior-visible incidents hide one of a small set of loop shapes. Learning the shape narrows where to look:

| Shape | How it looks | Where the loop actually closes |
|---|---|---|
| Retry storm | Errors spike under load, then keep climbing after load levels off | Timeout → retry → more load → more timeouts |
| Cold cache | A quiet service gets *slower* the longer it's quiet | Fewer requests → entries expire → next requests are slow → users bounce → traffic drops further |
| Alert fatigue | Real incidents get missed after a run of noisy ones | Too many alerts → channel gets muted → real signal buried → incident grows → more alerts |
| Onboarding drop-off | A slow signup flow never gets prioritized | Slow flow → fewer signups → less perceived value in fixing it → stays slow |

In every row, the thing you'd naturally stare at (the error, the slow response, the missed alert) is the *symptom column*. The loop is in the *shape* — a quantity feeding back into the condition that produced it.

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Treating the whole codebase or company as "the system" | Boundary too large — you can't trace a loop across something you can't fully see | Draw the smallest boundary that still contains the loop you're chasing |
| Treating one function as "the system" | Boundary too small — the loop closes somewhere outside that function, so you'll never see it | Zoom out until the arrow that feeds back into your starting point is visible |
| Fixing the code where the symptom appeared | The code there may be correct; the defect is in the loop's structure, not that line | Trace the connections in both directions before changing anything |
| Assuming straight-line cause and effect | Systems with retries, caches, or queues rarely have a single cause — output loops back as input | Explicitly ask "does this output ever become an input again, later?" |
| Treating an external dependency as a black box that "just works" | Ignoring its saturation behavior hides half the loop | Model the external system's response time or error rate as a variable, not a constant |

## Hands-on exercise

Pick one system you work on daily (a service, a batch job, a UI flow with retries or caching).

1. List its actual components by name — not layers like "backend," but concrete pieces.
2. Draw the connections between them and name what moves along each one.
3. Decide the boundary: what's inside the system you're reasoning about, what's external?
4. Trace one signal until it becomes an input again. Write the loop as a short chain of arrows.
5. Write the symptom you'd normally observe first, and the point in the loop where it actually originates. Are they the same place?

If you can't find a loop, look at anything with a retry, a cache, a queue, or a rate limit — that's almost always where one lives.

## Verify your thinking

- [ ] Can you name the system's boundary — what's inside vs. what's an external input or output?
- [ ] Did you list actual components, not vague layers like "the backend"?
- [ ] Can you draw a chain of connections where the last arrow feeds back into the first?
- [ ] Can you state the symptom and the loop's origin as two different places?
- [ ] Would someone else, reading only your loop diagram, understand why fixing the symptom's location wouldn't fix the problem?

Continue to [`middle.md`](middle.md).
