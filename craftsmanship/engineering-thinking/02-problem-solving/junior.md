# Problem-Solving — Junior

**Your question:** How do I make sure I'm solving the actual problem, not my guess at it?

"Make search better" is not a problem you can solve — it's a mood. If you start coding from your own guess at what "better" means, you'll ship something, it will pass code review, and it still might not fix anything, because you never wrote down what "fixed" would look like. The first skill in problem-solving isn't planning or coding — it's slowing down long enough to understand the problem you're actually being asked to solve.

## The method: Understand, plan, execute, verify

1. **Restate the problem in your own words.** One or two sentences, written down, not just thought. If you can't write it, you don't understand it yet.
2. **Identify the actual inputs, outputs, and constraints.** What data or state do you start with? What result is wanted? What can't change (deadline, systems you're not allowed to touch, backward compatibility)?
3. **Define concrete, observable success criteria before writing any code.** A number, a test, or a specific behavior — never an adjective like "better," "cleaner," or "faster" on its own.
4. **Devise the smallest workable plan.** List the fewest steps that could plausibly reach the success criteria. It doesn't need to be the best plan — it needs to be one you can start and revise.
5. **Execute in small, independently verifiable steps.** Each step should produce something you can check before you move to the next one.
6. **Verify the result actually matches the original intent.** Go back to the success criteria from step 3 and check each one explicitly. "The code runs without errors" is not on that list.

## A concrete example

**Request:** "Make search better."

**Restate:** Users frequently abandon a search session (no click within 30 seconds) when searching for common, well-known items.

**Inputs / outputs / constraints:**
- Input: 30 days of search query logs, current ranking function, click-through data.
- Output wanted: fewer abandoned searches.
- Constraints: can't change the search UI (owned by another team), must ship within two weeks, can't raise p95 search latency above 300 ms.

**Success criteria (write these before touching code):**
- Search abandonment rate on the top 200 queries drops from 34% to under 25%.
- p95 latency stays at or below 300 ms.

**Plan (five steps):**
1. Pull the 30-day abandonment numbers for the top 200 queries — this is the baseline you'll compare against later.
2. Read 20 abandoned-search sessions by hand to find the actual failure pattern (turns out: exact-match items are buried below fuzzy matches).
3. Prototype boosting exact-match items in ranking; test offline against a fixed sample of 50 queries.
4. Ship behind a feature flag to 5% of traffic; measure abandonment and latency for 3 days.
5. Compare against the baseline from step 1; roll out fully only if both success criteria hold.

**Verify:** After step 5, check abandonment rate *and* latency against the numbers from step 3 of the method — not "the flag works and nothing crashed."

## Recognize the guess-and-build trap

Before you plan anything, check whether you've actually understood the problem or just absorbed a vague impression of it. Warning signs:

- You can't describe "done" without using a word like "better," "cleaner," or "improved" — with no number or test attached.
- The request came from a hallway comment or a one-line Slack message, not from acceptance criteria.
- You've never seen an actual example of the failure — only someone's description of it.
- Two people who asked for the "same" thing describe different outcomes when you ask them each separately.

The fix for all four is the same question, asked before you write a plan: **"What would I observe if this were already fixed?"** If you can't answer it concretely, you're not ready to plan yet — go find or generate that evidence first (read logs, watch a session, ask one specific clarifying question).

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Start coding from the request's wording alone | You solve your interpretation, not the real problem — and only find out after building it | Restate the problem in your own words and confirm it before writing code |
| Treat "the code runs" as the finish line | A bug-free implementation of the wrong fix is still the wrong fix | Verify against the success criteria you wrote in step 3, not against "no errors" |
| Skip writing success criteria because the request "seems obvious" | Obvious to you may not match what the requester meant; you can't verify against a feeling | Write the criteria down as numbers or testable statements before planning |
| Plan the full solution before checking any assumption | If your first assumption is wrong, the whole plan is wasted work | Do the smallest step that tests your riskiest assumption first |
| Treat the first plan as fixed | Small early steps often reveal the request was different than you thought | Re-check the plan after each step; revise instead of forcing through |

## Hands-on exercise

Pick one vague ticket from your own backlog (or a request someone gave you informally).

1. Write the request exactly as it was given to you.
2. Restate it as a concrete problem in one or two sentences.
3. List the actual inputs, outputs, and constraints — even if some are guesses you need to confirm.
4. Write 2-3 concrete, observable success criteria (numbers or testable statements, no adjectives).
5. Write a 4-5 step plan to reach those criteria, ordered so the riskiest assumption is tested first.
6. For step 1 of your plan only, write how you'd verify it worked before moving to step 2.

If you can't turn step 2 into a sentence without an adjective like "better," go find one concrete example of the problem before continuing.

## Verify your thinking

- [ ] Can you write the problem in your own words without repeating the requester's exact phrasing?
- [ ] Did you write success criteria as numbers or testable statements, not adjectives?
- [ ] Does your plan test the riskiest assumption before the easiest one?
- [ ] Can you verify each step of your plan on its own, before the next step?
- [ ] Did you check the final result against your success criteria, not just "it works"?

Continue to [`middle.md`](middle.md).
