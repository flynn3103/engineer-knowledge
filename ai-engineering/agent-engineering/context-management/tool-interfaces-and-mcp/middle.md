# Tool Interfaces and MCP — Middle

<!-- level-focus -->
At middle level, focus on this question:

> For a concrete capability — querying BigQuery — can you compare exposing it as a plain CLI command via a generic shell tool vs. as a purpose-built MCP server, on token cost and on control?

---

## The comparison: `bq` CLI vs. BigQuery MCP server

Two ways to give the data-analyst agent access to BigQuery:

- **Option A — `bq` CLI via a generic bash tool.** The agent already has one general-purpose `bash`/shell tool. It runs `bq query --use_legacy_sql=false 'SELECT ...'` the same way a human engineer would from a terminal.
- **Option B — a BigQuery MCP server.** A dedicated server exposes typed tools like `run_query(sql, max_rows)`, `list_datasets()`, `get_table_schema(table)`, each with its own schema, discovered and called through MCP.

| Dimension | `bq` CLI via bash | BigQuery MCP server |
|---|---|---|
| Schema token cost | ~1 generic `bash` tool, near-zero marginal cost per capability | N typed tool schemas resident in context every turn |
| Model familiarity | High — `bq` commands appear extensively in general training data | Lower — a custom tool's exact name/args must be explained in its schema, adding tokens the model needs to actually read |
| Composability | Pipe to `jq`, `head`, `wc -l`, redirect to a file — full shell composability | Fixed call signature only; no piping between calls |
| Output control | Unbounded by default — a `SELECT *` can return gigabytes unless the agent remembers to add `LIMIT` | Server-enforced `maxRows`/column projection — the server can refuse an unbounded query outright |
| Error handling | Unstructured stderr text the model must parse itself | A typed error object (e.g., `{"error": "quota_exceeded"}`) the model can branch on reliably |
| Guardrails | Whatever the shell sandbox happens to allow | Purpose-built: dry-run cost estimate before execution, read-only service account, dataset allow-list |
| Auth | Ambient credentials already in the shell (e.g., `gcloud` ADC) — broad, whatever scope the shell already has | Explicit, narrowly scoped credentials configured specifically for this server |
| Portability | Requires a shell and the `bq` binary installed | Works with any MCP-compliant client, no shell dependency |

## The rule to apply

**If the model already knows the CLI well, the output is easy to bound with normal shell composition, and the sandbox running that shell is trustworthy — the CLI wins on token cost and flexibility.** Reach for a dedicated MCP server specifically when you need one or more of:

- **Governance** — a hard guardrail the model cannot bypass (e.g., a bytes-scanned cost cap enforced server-side, not just suggested in a prompt).
- **Structured, typed results** — an error the agent can branch its logic on, rather than parsing free-text stderr.
- **Discovery at scale** — many capabilities that benefit from being independently listed, versioned, and enabled per-agent, rather than "give the agent a shell and hope it uses the right CLI flags."
- **A non-shell client** — the calling application has no shell available at all (a hosted API endpoint), so a raw CLI isn't reachable regardless of preference.

MCP is not "the newer, better default" — it's the right choice when governance or structure is the actual requirement, and it costs real tokens on every turn to get that. A 1:1 wrapper MCP server around a CLI that adds no cost control, no structured errors, and no new capability is pure token overhead with no benefit over the CLI it wraps.

## Applying it to the data-analyst agent

- **Exploratory, ad-hoc queries** during investigation (the agent trying several `SELECT` variants to find the anomaly) — the `bq` CLI via shell is lower cost and the model is already fluent in it.
- **The final, repeated "check GMV daily" query that runs unattended** in a scheduled job with no human reviewing each query before it runs — this is exactly the governance case: a BigQuery MCP server with a query allow-list, a cost cap, and a read-only credential is the safer default once there's no human in the loop.

## Comprehension check

- Name two dimensions where the `bq` CLI wins over a dedicated MCP server, and one where the MCP server wins.
- What's the actual rule for choosing between them — is MCP always the safer choice? Why or why not?
- Give a concrete example of a BigQuery MCP server design flaw described here as "pure token overhead with no benefit."
- For the data-analyst agent, which option fits an unattended scheduled query better, and which fits ad-hoc human-reviewed exploration better?
