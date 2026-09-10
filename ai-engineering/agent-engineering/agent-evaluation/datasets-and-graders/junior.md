# Datasets and Graders — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you build a small golden set with a clear expected outcome per case, and grade what can be graded deterministically without an LLM judge?

---

## Anatomy of a case

- **Input**: what the user (or upstream system) sends the agent.
- **Fixtures/context**: any state the case depends on — the mock order database, the customer's account history — kept alongside the case so the run is reproducible.
- **Expected outcome**: written before running the agent, stating what a correct result looks like.
- **Notes**: why this case exists (e.g., "regression case for bug #412 — agent previously refunded the wrong order").

## Deterministic graders first

- Prefer a deterministic grader whenever the correct answer has a checkable exact form:
  - **Schema validation**: does the output match a required JSON structure.
  - **Field exact-match**: does a specific field (refund amount, order ID) equal the expected value.
  - **Regex/substring check**: does the response contain a required phrase or avoid a forbidden one.
  - **Tool-call assertion**: was a specific tool called with a specific argument (e.g., "was `look_up_order` called with `order_id=4521`").
- Deterministic graders are cheap, fast, and have zero judgment variance — use them for anything they can cover before reaching for an LLM judge (see [Middle](middle.md)).

## Building a 30-case set

1. Cover the agent's main responsibilities first (the common-path cases), then edge cases (ambiguous input, missing data, policy boundary).
2. Include at least a few adversarial cases (a customer asking for a refund outside policy) to check the agent doesn't just comply with anything asked.
3. Write the expected outcome and grading method (which deterministic check applies) for every case before running the agent.

## Reading the result

- Report: overall pass rate, and the full list of failing cases with which specific check failed (not just "case 14 failed" — say which field or tool-call assertion didn't match).
- A pass rate alone with no list of specific failures isn't actionable — you need to know exactly what to fix.

## Common Mistakes

- **Reaching for an LLM judge before checking if a deterministic grader would work.** Deterministic checks are cheaper, faster, and have no grading variance — use them wherever the correct form is checkable exactly.
- **A golden set with only common-path cases.** Never catches the edge cases and adversarial inputs that cause real production incidents.
- **Reporting pass rate with no detail on what failed.** Tells you something is wrong without telling you what to fix.

## Apply It

1. Build a 30-case golden set for one agent, covering common-path, edge-case, and adversarial inputs.
2. For each case, write the expected outcome and identify the deterministic check (schema, exact-match, regex, tool-call assertion) that grades it.
3. Run the agent against all 30 cases and report pass rate plus a specific reason for every failure.

## Verify Your Work

- Every case has a written expected outcome and a named deterministic grading method.
- The set includes edge-case and adversarial inputs, not only common-path cases.
- Every failure is reported with the specific check that failed, not just a pass/fail flag.

## Review Questions

- Why prefer a deterministic grader over an LLM judge whenever one is available?
- What's missing from a golden set that only has common-path cases?
- Why does "case 14 failed" without further detail fail to be actionable?
