# Evaluation Fundamentals — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you write down what a correct run looks like before you measure anything, and grade a small set of cases without asserting exact-match output?

---

## Core vocabulary

- **Run**: one full execution of the agent on one input, start to finish.
- **Trace**: the recorded detail of a run — every prompt, tool call, and response (see [Tracing and Observability](../../tracing-and-observability/)).
- **Outcome**: whether the final result was correct (e.g., the refund amount matches policy).
- **Trajectory**: whether the *steps* the agent took to get there were reasonable (e.g., it checked the order status before refunding).
- **Ground truth**: the correct answer for a case, decided by a human before the agent runs.
- **Grader**: the function or rubric that compares the agent's output to ground truth and produces a score.
- **Golden set**: a fixed set of cases with known-correct answers, used to grade any version of the agent consistently.

## Why exact-match breaks

- Asking an LLM the same question twice can produce two different but equally correct phrasings. An exact-match assertion (`response == "Your refund has been processed"`) fails one of them for no real reason.
- Use exact-match only for values that must be literally exact — a tool argument, a refund amount, a status code. Use a rubric or LLM-as-judge for free-text quality (see [Datasets and Graders](../../datasets-and-graders/)).

## A repeatable method

1. Write 15–20 cases. Each case has: the input, any needed context (e.g., the customer's order history), and a written expected outcome.
2. Run the agent on each case and record the trace.
3. Grade each case against the *written* expected outcome, not against what "seems reasonable" after seeing the output.
4. Report a pass rate and list every failing case with a one-line reason.

## Example

- Case: `input: "Where is my order #4521?"`, `context: order 4521 shipped 2 days ago, tracking #ABC123`.
- Expected outcome: "Agent looks up order 4521 and returns the tracking number, without asking the customer to repeat information already in context."
- Grade: pass if tracking number is returned and no redundant question is asked; fail otherwise, with the specific step that broke it.

## Common Mistakes

- **Deciding the expected outcome after seeing the agent's answer.** This is confirmation bias with extra steps — write the expected outcome first, sealed before you run the agent.
- **Using exact-match on natural-language output.** Fails good answers for surface-level phrasing differences and teaches you nothing about actual quality.
- **Grading only the final answer.** A refund agent that approves the right amount but never checked eligibility got the outcome right and the trajectory wrong — you need both if the trajectory matters for your case.

## Apply It

1. Pick one agent you have access to (or the support-ticket scenario). Write 15 cases with sealed expected outcomes before running anything.
2. Run the agent, record the trace for each case.
3. Grade every case, and for each failure, write the exact step where it diverged from the expected outcome.

## Verify Your Work

- Every case has a written expected outcome recorded before the agent ran.
- No case is graded by exact-match on free-text output.
- Every failure has a named step, not just a pass/fail flag.

## Review Questions

- Why does grading after seeing the output introduce bias, and how do you avoid it?
- What's the difference between an outcome metric and a trajectory metric, and when does trajectory matter even if the outcome was correct?
- Why does exact-match fail on natural-language responses, and where is exact-match still the right tool?
