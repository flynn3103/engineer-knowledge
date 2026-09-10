# Tool Interfaces and MCP — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you decide, for a real system, which capabilities deserve a purpose-built typed server and which stay as one generic shell tool — and design the guardrails and failure semantics for the ones that need them?

---

## Drawing the boundary

Not every capability needs its own MCP server, and not everything should be one generic shell tool either. Decide per-capability:

| Signal | Belongs in a dedicated typed server | Stays as generic shell/CLI |
|---|---|---|
| Needs a hard, unbypassable cost/scope cap | Yes — server enforces it in code, not via a prompt instruction the model could ignore | No |
| Runs unattended, no human reviewing each call | Yes | No — riskier without server-side caps |
| Model is already fluent in the underlying CLI | Weaker case for a wrapper | Yes |
| Result needs to be typed for downstream logic (agent branches on error codes) | Yes | No |
| One-off, exploratory, human-supervised | Weaker case | Yes |
| Capability doesn't exist as a CLI at all (e.g., a proprietary internal API) | Yes, by necessity | N/A |

For the data-analyst agent: BigQuery access for the *scheduled anomaly-detection job* (unattended, needs a hard cost cap) belongs behind a typed MCP server; BigQuery access for a *human-supervised investigation session* can stay as `bq` via shell.

## Guardrails a real tool boundary needs

- **Dry-run cost estimate before execution** — for BigQuery specifically, `bq query --dry_run` reports bytes that would be scanned before the query runs; a server-side wrapper can refuse to execute if that estimate exceeds a configured threshold, rather than discovering the cost after the fact.
- **Read-only credentials by default** — the service account or API key the server uses should have the minimum scope the capability needs (the least-privilege principle: a query tool doesn't need write access to any dataset).
- **Row/result limits enforced server-side** — `maxRows` as a hard parameter the server clamps, not a suggestion in the tool's description that the model may forget to include.
- **Allow-listed datasets/tables** — if the agent only ever needs three specific datasets, the server should reject queries against anything outside that list, rather than trusting the model's SQL to only ever touch the intended scope.

## Failure semantics the model can act on

A tool boundary is only as good as what happens when it fails:

- **Typed, distinguishable errors** — `quota_exceeded`, `permission_denied`, `query_timeout`, `syntax_error` should be distinct codes, not one generic "error occurred" string, so the model's next action (retry vs. reformulate vs. give up and report to the user) can actually depend on which one occurred.
- **Partial results should say they're partial** — if a query was truncated at `maxRows`, the result should say so explicitly ("showing first 1000 of an unknown larger total"), not return exactly 1000 rows indistinguishable from a query that only had 1000 rows total.
- **Timeouts should be distinguishable from empty results** — a query that timed out and a query that legitimately found zero matching rows must not look the same to the model, or it will report "no anomaly found" when the real answer is "the check couldn't complete."

## Comprehension check

- Give one signal that pushes a capability toward a dedicated typed server, and one that pushes it toward staying as generic CLI access.
- Why is a dry-run cost estimate a real guardrail while a prompt instruction saying "please use LIMIT" is not?
- Why must a timed-out query result be distinguishable from a legitimately empty result?
- What's the risk of returning exactly `maxRows` rows with no indication that results were truncated?
