# Probabilistic Thinking — Junior

**Your question:** What does the base rate and a simple expected-value calculation actually say, instead of my gut feeling?

"This will take 3 days." "That library is probably fine." "It's unlikely to break in prod." Each of these is a guess dressed up as a fact. It hides two different numbers — how *likely* something is, and how *bad* it is if it happens — and it's usually built from whatever example is freshest in your memory, not from what actually happens over many tries.

## The method: base rate first, then expected value

1. **Find the base rate.** Before trusting your gut, ask: "Out of the last N times something like this happened, how many times did it go the way I'm assuming?" This is the base rate — a historical frequency, not a feeling.
2. **Don't let one vivid story override it.** "Last time we upgraded a dependency it broke prod" is one data point. If 9 out of the last 10 dependency upgrades went fine, the base rate is 90% success — the scary story is memorable, not representative.
3. **Separate probability from impact.** "How often does this happen" and "how bad is it when it does" are two different numbers. A common, cheap failure and a rare, expensive failure can look the same in a sentence ("this could go wrong") but demand completely different responses.
4. **Multiply to get expected value (EV).** `EV = probability × impact`. Do this for each option you're comparing, using the same units (hours, dollars, or a consistent severity scale) on both sides.
5. **Compare EVs, not vibes.** The option with the better expected value — not the one that "feels safer" — is your default choice, unless a low-probability outcome is severe enough that you can't absorb it even once (more on that at senior level).

## A concrete example

**Decision:** Add retry logic to a payment-webhook handler before launch, or ship without it and add it later if needed?

**Step 1 — base rate.** Look at the last 12 third-party webhook integrations the team shipped. 5 of them had at least one delivery failure in the first month (timeout, dropped connection, 5xx from our side). Base rate of "this class of integration drops at least one webhook in month one": 5/12 ≈ 42%.

**Step 2 — impact if it happens.** A dropped payment webhook means a customer's order shows as unpaid until manual reconciliation. Support estimates 45 minutes of manual work per incident, and it's a bad customer experience.

**Step 3 — build the EV table.**

| Option | P(at least one drop, month 1) | Cost if it happens | Cost to build now | EV (cost) |
|---|---|---|---|---|
| Ship without retries | 42% | 45 min support time × ~3 expected drops/month ≈ 2.25 hrs | 0 hrs | 0.42 × 2.25 ≈ 0.95 hrs/month |
| Add retry logic now | ~5% (retries absorb transient failures) | 45 min × ~0.3 expected drops ≈ 0.25 hrs | 4 hrs one-time | 0.05 × 0.25 ≈ 0.01 hrs/month + 4 hrs upfront |

**Step 4 — compare.** Retry logic pays for itself in roughly 4 months of avoided support time, and removes an ongoing customer-facing failure. Without the base rate and the table, "add retries" and "ship it, we'll see" sound like equally reasonable opinions. With the table, one option is clearly better under realistic assumptions.

## Recognize a naive point estimate when you hear one

A point estimate with no range and no stated assumption is a warning sign, not a fact:

- "This will take 3 days" → ask: "3 days if what goes right? What's the worst case, and why?"
- "It's unlikely to break" → ask: "Unlikely compared to what — how many times has this class of change broken things before?"
- "It's probably fine" → ask: "What would make it not fine, and how would we know?"

You don't need statistics to fix this at junior level — you need one extra sentence: the assumption behind the number, and roughly how confident you are.

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Estimating from the one time it went badly (or the one time it went great) | A single memorable anecdote is not a rate — it overweights whatever you happened to experience recently | Look at the last 10-ish similar cases before trusting a gut number |
| Stating a probability with no impact ("it's risky") | "Risky" could mean common-and-cheap or rare-and-catastrophic — these need opposite responses | Always pair a likelihood with a concrete cost or consequence |
| Giving a single number with no assumption ("3 days") | Nobody can tell if 3 days assumes the happy path or includes review, tests, and one blocker | State the assumption: "3 days if the API doesn't change; 5 if it does" |
| Treating "unlikely" as "won't happen" | Low probability isn't zero probability — a 5% chance still happens 1 time in 20 | Ask whether you could survive it happening even once |
| Comparing options without matching units | "Option A takes 2 days, Option B is risky" isn't a comparison — one side has no number | Put both options in the same EV table, same units, before deciding |

## Hands-on exercise

Pick a decision you're facing this week (which library to use, whether to add validation, whether to deploy Friday).

1. Name the base rate: how many similar past cases can you recall or look up, and what fraction went the way you're assuming?
2. Write the impact if it goes wrong, in a concrete unit (hours, dollars, incidents).
3. Build a two-row EV table comparing your two real options.
4. Compute EV for each and see which one actually wins.
5. Write one sentence stating the assumption behind your base rate — would 3 more data points change it?

## Verify your thinking

- [ ] Did you use a base rate from multiple past cases, not one anecdote?
- [ ] Did you write probability and impact as two separate numbers?
- [ ] Are both options in your comparison expressed in the same units?
- [ ] Can you state the assumption behind your estimate in one sentence?
- [ ] Would a 5% chance of a severe outcome change your decision, even though it's "unlikely"?

Continue to [`middle.md`](middle.md).
