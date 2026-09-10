# Tool Interfaces and MCP — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you run a shared tool/MCP-server registry across an org at 100+ tools — with schema versioning, security review, and disclosure control — so tool sprawl doesn't quietly become a cost and security liability?

---

## The sprawl problem at scale

At 5 tools, every team can eyeball what's connected. At 100+ tools across a fleet of agents, unmanaged growth causes two distinct failures:

- **Token cost**: an agent connected to "every MCP server the team has ever built, just in case" can burn tens of thousands of tokens on schemas before the first user message, even if only 3 are ever called in a typical session.
- **Security exposure**: a third-party MCP server, once connected, can execute arbitrary logic the org didn't write and may not have reviewed — never trust a tool's result as ground truth without validating it, the same trust-boundary discipline that applies to every tool call, applies doubly to servers pulled in from outside the org.

## Progressive / dynamic tool disclosure

Instead of exposing every tool on every connected server all the time, expose tools progressively:

- **Session-scoped connection**: connect only to the MCP servers relevant to the current task, decided at session start, not "connect to everything the agent might ever need."
- **On-demand discovery**: some MCP-aware frameworks support listing tool *categories* first and only fetching full schemas for a category once the model indicates it needs it — trading one extra round trip for avoiding the cost of unused schemas on every turn.
- **Per-agent allow-lists**: an agent doing financial analysis doesn't need the schema for a tool that manages Kubernetes deployments, even if both servers exist in the org's registry.

## Schema versioning

Tool schemas change — a parameter gets renamed, a new required field is added. Without versioning:

- A prompt or few-shot example baked into one agent's system prompt, written against schema v1, silently breaks when the server upgrades to v2 with a renamed parameter.
- **Require semantic versioning on tool schemas** and a deprecation window (old schema version still callable for N weeks after a new one ships) so consuming agents have time to migrate rather than breaking on the day of a server update.
- **Log which schema version was actually presented to the model** on each call, so a regression can be traced to "the schema changed" rather than "the model got worse" (the same diagnostic discipline as [Context Fundamentals — Senior](../context-fundamentals/senior.md)).

## Security review process for tool infrastructure

- **Every new MCP server (internal or third-party) goes through review before being added to the shared registry** — what data can it read, what actions can it take, what's the blast radius of a malicious or buggy call.
- **Third-party servers get stricter review** than internally built ones — the org didn't write the code executing on the other end of that tool call, so the review must cover what that server's operator can see or do with the requests it receives.
- **Periodic re-review, not just at onboarding** — a server's capabilities or the data it touches can change after it's initially approved; schedule re-review on a cadence, don't treat approval as permanent.

## Comprehension check

- Name the two distinct failures caused by unmanaged tool sprawl at 100+ tools.
- What's the benefit of progressive/dynamic tool disclosure over connecting to every server upfront?
- Why does a tool schema need semantic versioning and a deprecation window, concretely?
- Why should third-party MCP servers get stricter security review than internally built ones?
