# Agentic Techniques — Junior

<!-- level-focus -->
At junior level, focus on this question:

> For a well-defined task whose steps are knowable in advance, can you write an explicit plan before executing anything, run it step by step, and check each step's output before moving to the next?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

---

## Core Concept 1 — Plan-Then-Execute vs. Interleaved Reasoning

The [Agent Architectures](../agent-architectures/junior.md) loop reasons one step at a time: observe, decide the *next* single action, act, observe again. That interleaved style is necessary when what to do next genuinely depends on what just happened. But many tasks don't have that shape — their steps are knowable in full before any of them run.

**Plan-then-execute** is the alternative: the agent produces a complete, ordered plan upfront, *before* executing a single step, and then works through that plan in order — reasoning only about *how* to perform each step, not *whether* the step sequence itself needs to change.

| | Interleaved (ReAct-style) | Plan-then-execute |
|---|---|---|
| When to use | Next step depends on the last observation | Full step sequence is knowable in advance |
| Reasoning per step | "What should I do next, given everything so far?" | "How do I execute this specific, already-decided step?" |
| Failure if misapplied | — | Applied to a task that actually needs branching: a fixed plan can't adapt when step 2's result should change step 4 |

## Core Concept 2 — The Method

1. **Write the plan before touching any tool.** List each step as an ordered action with its expected output type — not "get the data" but "fetch total sales by category for the date range, expect a table of category → dollar amount."
2. **Execute steps strictly in order.** Each step reasons about how to perform itself (which tool, what arguments) but does not reconsider whether the step belongs in the plan at all.
3. **Validate each step's output against its expectation before moving on.** This is a basic check, not full reflection (that's the middle-level technique) — just confirming the output is the right *shape* and not obviously empty or malformed before letting it feed the next step.
4. **Only replan if a step fails validation**, and treat that as an explicit, visible event — not a silent fallback to improvising.

## Core Concept 3 — A Concrete Example

Task: "Generate this week's sales summary report and post it to the #sales-weekly channel."

**The plan, written upfront:**

```
1. Fetch total sales by category for the current week.
   Expect: table of {category, total_dollars}
2. Fetch the same for the prior week.
   Expect: table of {category, total_dollars}
3. Compute week-over-week percentage change per category.
   Expect: table of {category, current, prior, pct_change}
4. Format the result as a markdown table with a one-line headline
   summarizing the overall trend.
   Expect: markdown string
5. Post the formatted report to #sales-weekly.
   Expect: post confirmation
```

**Execution, step by step:**

- Step 1 runs `get_sales_by_category(week="current")`, returns a 6-row table. Validation: non-empty, all rows have both fields. Passes.
- Step 2 runs the same tool for `week="prior"`. Passes the same check.
- Step 3 computes the delta locally (no tool call — this is the model or surrounding code doing arithmetic on data already fetched). Validation: row count matches steps 1 and 2. Passes.
- Step 4 formats the markdown table and headline. Validation: output is a non-empty string containing a markdown table marker (`|`). Passes.
- Step 5 posts to the channel and returns a confirmation. Validation: confirmation received. Passes.

Nothing here needed the model to decide, mid-task, "should I fetch a third week's data instead?" — because the task's structure never required that decision. That's exactly the signal that plan-then-execute was the right technique.

## Core Concept 4 — When the Fixed Plan Is Wrong

Contrast with a task where plan-then-execute would be the wrong fit: "Look into why the sales-summary bot's Slack posts have been failing for the last three days, and fix it." Here, the second step genuinely depends on what the first step finds — if step 1 (check the bot's error logs) shows an authentication failure, step 2 should be "check the bot's token," not whatever was written into a plan before anyone knew what was wrong. Writing a fixed 5-step plan for this task means either the plan is wrong the moment reality diverges from the guess, or the model quietly abandons the plan mid-execution — which is a worse outcome than never using plan-then-execute for this task at all, because it hides an architecture mismatch behind an agent that "sort of" adapted.

## Common Mistakes

1. **Writing a plan, then not validating step outputs.** Garbage from step 1 (an empty table, a malformed value) silently flows into steps 2 through 5, and the failure only surfaces at the very end — usually as a confusing final error far from its actual cause.
2. **Using plan-then-execute for a task that needs branching.** If the *content* of one step's result should change a later step's instructions, a fixed upfront plan is the wrong technique — see Core Concept 4.
3. **Treating "expected output" as optional.** A plan step without a stated expected shape gives you nothing to validate against — you can't tell a wrong-but-plausible-looking output from a correct one.
4. **Silently re-planning on failure instead of surfacing it.** If step 3 fails validation and the agent quietly picks a new approach without that being a visible, logged event, you lose the ability to tell "the plan worked" from "the plan failed and something else covered for it."

## Apply It

1. Pick a task with steps you can fully enumerate before starting — a report, a data pull with a fixed transformation, a scheduled multi-step notification.
2. Write the plan as an ordered list, each step with its tool (or computation) and its expected output shape.
3. Execute the plan step by step, writing down the actual output at each step next to its expectation.
4. For each step, check explicitly: did the output match the expected shape? Record pass/fail, not just "looks fine."
5. Identify one plausible way this exact task could need branching (a step whose result should change a later step), and explain why your plan either handles it or why plan-then-execute was still the right choice despite it.

## Verify Your Work

- The plan was written in full before the first tool call, not discovered incrementally.
- Every step states an expected output shape, not just an action.
- Each step's actual output was checked against its expectation before the next step ran.
- You can point to the exact step (if any) where a validation check would have caught a bad output before it propagated.
- You can name one task where plan-then-execute would be the wrong technique, and explain what specifically makes it wrong for that task.

## Review Questions

- What distinguishes a task suited to plan-then-execute from one suited to interleaved, step-by-step reasoning?
- Why does writing an expected output shape for each plan step matter, beyond just listing the actions?
- What goes wrong when a step's output isn't validated before the next step consumes it?
- What's the risk of silently abandoning a fixed plan mid-execution instead of surfacing the failure explicitly?
- Give an example of a task where a fixed upfront plan would break because a later step genuinely needs to depend on an earlier step's specific result.
