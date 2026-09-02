# Agentic Techniques — Middle

<!-- level-focus -->
At middle level, focus on this question:

> For a task where the first attempt often fails, can you add a reflection/self-correction step that checks the output against an objective signal, feed a genuine failure back as a new observation, and measure — with real before/after numbers — whether it actually improves reliability?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — What Reflection Actually Is

**Reflection** (sometimes called self-critique or, in the research literature, the Reflexion pattern — Shinn et al., "Reflexion: Language Agents with Verbal Reinforcement Learning") is a loop within a step: after producing a candidate output, check it against a signal that reveals whether it's actually correct, and if it fails, feed that specific failure back as a new observation and retry with revised reasoning — rather than either accepting the first attempt unconditionally or retrying blindly with no new information.

This only works if the checking signal is trustworthy. That's the design decision that separates reflection that improves reliability from reflection that just adds latency.

## Core Concept 2 — Objective Signals Beat Subjective Ones

| Signal type | Example | Reliability |
|---|---|---|
| **Objective / executable** | Does the generated SQL query execute without a syntax or schema error? Does the generated code pass its unit tests? Does the API call return a 2xx status? | High — the signal is a fact about the world, not another model's opinion |
| **Structural validation** | Does the output parse as valid JSON against the expected schema? Are required fields present? | High — mechanically checkable |
| **Subjective / LLM-graded** | A second LLM call asked "does this look correct?" with no ground truth to check against | Low — a model grading another model's output shares the same blind spots, and can produce confident-sounding approval of a wrong answer |

The practical rule: **prefer an objective, executable check whenever one exists.** Reflection built on a subjective LLM-grading step can compound hallucination rather than fix it — a wrong answer that "looks right" to the generating model often looks right to a grading model for the same underlying reason. Reserve LLM-based grading for cases where no objective signal is available at all, and treat its verdict as weaker evidence than an execution result.

## Core Concept 3 — A Concrete Example: Natural-Language-to-SQL

Task: convert a natural-language question into a SQL query against a real schema, execute it, and return the result. This is a well-known task where first-attempt failure is common — column names, join paths, and aggregation semantics are easy to get subtly wrong from a schema description alone.

**Without reflection:**

```
Thought: The user wants total revenue by region last quarter.
Action: generate_sql("SELECT region, SUM(amount) FROM orders
         GROUP BY region WHERE quarter = 'Q2-2026'")
Tool result: SQL syntax error — WHERE must precede GROUP BY
Final Answer: [returns the error to the user, or fails silently]
```

**With reflection:**

```
Thought: The user wants total revenue by region last quarter.
Action: generate_sql("SELECT region, SUM(amount) FROM orders
         GROUP BY region WHERE quarter = 'Q2-2026'")
Tool result: SQL syntax error — WHERE must precede GROUP BY
Reflection: The query failed because WHERE was placed after GROUP BY.
  SQL clause order requires WHERE before GROUP BY. Revise the clause order.
Action: generate_sql("SELECT region, SUM(amount) FROM orders
         WHERE quarter = 'Q2-2026' GROUP BY region")
Tool result: 4 rows returned successfully
Final Answer: [formats and returns the actual result]
```

The signal here — did the query execute — is objective and unambiguous. The reflection step feeds the *exact database error message* back into context, not a vague "try again," which is what makes the second attempt more likely to succeed than a blind retry.

## Core Concept 4 — Capping Retries and Failing Controlled

Reflection is not unlimited retry. Cap it — typically 2 to 3 attempts — and if the objective signal still fails after the cap, return a controlled, explicit failure rather than looping further or silently guessing:

```
Attempt 1: fails (clause order)
Attempt 2 (after reflection): fails (references a column that doesn't
  exist in the schema)
Attempt 3 (after reflection): fails (same missing-column error, model
  is not converging)
→ Cap reached. Return: "I wasn't able to generate a working query for
  this request — it may be referencing data that isn't in the schema
  I have access to. Escalating to a person."
```

A model that fails identically on attempts 2 and 3 is exhibiting the same non-convergence signal covered by the repeated-identical-call detector in the [senior architecture guide](../agent-architectures/senior.md) — reflection needs its own version of that same safeguard: if the *nature* of the failure isn't changing between attempts, further retries are unlikely to help, and the cap should trigger even before the raw attempt count does.

## Core Concept 5 — Distinguishing Transient Failures From Logical Failures

Not every retry should involve reflection. Two different failure classes need two different responses:

| Failure class | Example | Correct response |
|---|---|---|
| **Transient** | Network timeout, tool briefly unavailable, rate limit | Plain retry with backoff — no reasoning change needed, because nothing about the *output* was wrong |
| **Logical** | Wrong column name, wrong join, malformed output | Reflection — the output itself was incorrect and needs revised reasoning, not just a repeat |

Applying reflection to a transient failure wastes a model call reasoning about a problem that wasn't a reasoning problem at all. Applying a plain retry to a logical failure just reproduces the same wrong output, since nothing about the input to the model changed. Distinguish them by what the error actually says: a timeout or 5xx status is transient; a syntax error, schema mismatch, or validation failure is logical.

## Core Concept 6 — Measuring Whether Reflection Actually Helps

Don't assume reflection improves reliability — measure it, on a held-out set of representative test cases:

1. **Build a test set** of NL-to-SQL prompts against your real schema — at least 30–50 for a meaningful comparison, covering a range of query complexity.
2. **Run without reflection**, recording first-attempt success rate (**pass@1**): the fraction that execute successfully on the first generated query.
3. **Run with reflection enabled**, recording success rate after up to N reflection retries (**pass@N**), and separately record the *average number of attempts* used per successful case.
4. **Compare the two rates**, and compute the cost multiplier: if pass@1 is 61% and pass@3-with-reflection is 89%, that's a real reliability gain — but if the average successful case now costs 1.8x the LLM calls of a single attempt, that's the price, and it needs to be weighed against the task's tolerance for that added latency and spend.

A reflection step that raises pass@N by 2 percentage points while tripling average cost per request is not obviously worth shipping — the point of measuring is to make that trade-off visible instead of assumed.

## Cross-Component Scenario

The NL-to-SQL agent above is one step inside a larger reporting workflow: a user asks a natural-language business question, the agent generates and reflects on SQL until it gets a working query (or hits the cap), then formats and returns the result. The reflection loop is entirely internal to one step of that larger flow — the surrounding workflow only sees two outcomes: a successful result, or a controlled failure message. This is the same principle as the middle-level [architecture guide](../agent-architectures/middle.md)'s sub-agent isolation: verify the reflection loop's behavior on its own, with its own test set, independent of whatever calls it.

## Common Mistakes

- **Grading with a second LLM call instead of an objective check when an objective check is available.** SQL execution success is a fact; "does this look right to another model" is an opinion that can share the same blind spot as the first model.
- **Feeding a vague "try again" instead of the actual error.** The reflection step's value comes specifically from surfacing what went wrong — a generic retry prompt throws away the most useful piece of information the failed attempt produced.
- **No retry cap, or a cap that doesn't check whether the failure is actually changing.** Three identical failures in a row is evidence the model isn't converging, not evidence that a fourth attempt will.
- **Applying reflection to transient failures.** Wastes a reasoning step on a problem — a timeout, a rate limit — that reasoning can't fix.
- **Shipping reflection without measuring pass@1 vs. pass@N first.** Without the before/after numbers, you can't tell whether the added latency and cost bought a real reliability improvement or nothing at all.

---

## Apply It

1. Pick a task with a genuinely objective success signal — code that can be executed and tested, a query that can run, structured output that can be schema-validated.
2. Build a test set of at least 20–30 representative cases and run them without any reflection, recording pass@1.
3. Add a reflection step that feeds the actual failure signal (not a generic retry prompt) back into context, cap it at 2–3 attempts, and re-run the same test set, recording pass@N and average attempts per success.
4. Compute the cost multiplier (average LLM calls per successful case, with vs. without reflection) and write one sentence on whether the reliability gain justifies it for this specific task.
5. Identify one failure mode in your test set that reflection did *not* fix even after the retry cap, and classify why — a persistent logical error, or a transient failure reflection couldn't have addressed anyway.

## Verify Your Work

- You have real pass@1 and pass@N numbers from the same test set, not an assumption that reflection "should" help.
- The reflection step's prompt includes the actual failure signal (error message, failed test name), not a generic "try again."
- The retry cap is enforced and was actually observed triggering on at least one test case.
- You can name, for at least one case, which failure class it was (transient vs. logical) and confirm the response matched — a plain retry for transient, reflection for logical.
- The cost multiplier is a real computed number, not an estimate.

## Review Questions

- Why does an objective, executable signal make reflection more trustworthy than a second LLM call grading the first one's output?
- What specifically should the reflection step feed back into context, and why does a generic "try again" lose most of the value?
- Why should a transient failure get a plain retry instead of a reflection step, and vice versa for a logical failure?
- What does it mean for a reflection loop to stop "converging," and why should that end the retry loop even before a raw attempt-count cap is hit?
- What two numbers do you need, at minimum, to know whether adding reflection was actually worth its cost?
