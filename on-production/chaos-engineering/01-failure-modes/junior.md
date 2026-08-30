# Failure Modes — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a small service and its direct dependencies, can you list its realistic failure modes and describe how each one would actually be observed?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

> **Roadmap:** [Chaos Engineering](../README.md) → Failure Modes

*Before you break anything on purpose, you have to know what "broken" can even look like. Cataloging failure modes is that homework.*

---

## Core Concept 1 — Vocabulary: Fault, Failure, Failure Mode

Three words get used loosely in conversation. Keep them apart, because the rest of this topic depends on it:

- **Fault** — the underlying thing that goes wrong: a disk fills up, a cable is cut, a dependency returns a 500.
- **Failure** — the visible consequence for a user or caller: a request times out, an order isn't placed, a page shows an error.
- **Failure mode** — the *named, describable way* a component can fail, tying a class of fault to its observable failure. "The payment API returns 5xx for more than ten seconds" is a failure mode. "The database" is not a failure mode — it's a component.

This topic is about building the list of failure modes a system can exhibit, not about causing them on purpose (that's Fault Injection) or rehearsing them as a team exercise (that's Game Days). Cataloging comes first: you cannot inject or rehearse a failure mode you haven't named.

## Core Concept 2 — Five Families of Failure Modes

Most software failure modes fall into a small number of recurring families. Learn these first; specific instances of each family will keep showing up in every system you touch.

| Family | What breaks | Typical trigger |
|---|---|---|
| **Infrastructure** | A host, container, VM, or availability zone disappears | Hardware fault, spot-instance reclaim, AZ outage |
| **Network** | Requests get slow, dropped, or partitioned | Packet loss, DNS failure, routing change |
| **Dependency** | A downstream service errors or degrades | Upstream bug, upstream overload, upstream deploy |
| **Resource exhaustion** | A local resource runs out | Connection pool full, disk full, memory pressure, thread starvation |
| **Data** | The data itself is the problem | Malformed message, schema mismatch, corrupted record |

Each family carries a different question. Infrastructure asks "what if this process just isn't there." Network asks "what if the call is slow instead of failing outright." Dependency asks "what if someone else's system misbehaves." Resource asks "what if I run out of something." Data asks "what if the input is the wrong shape."

## Core Concept 3 — A Repeatable Method

For any one component, run this loop:

1. **List its dependencies** — everything it calls, and everything that calls it (a database, a cache, another service, a queue).
2. **For each dependency, ask**: what happens if it's unreachable? if it's slow but still responding? if it returns an error? if it returns a wrong-but-valid-looking answer?
3. **Write the observable symptom** — not "the database fails" but "requests to `GET /orders/:id` return 500 within two seconds" or "requests hang for the full 30-second timeout."
4. **Write the downstream effect** — what does the *caller* of this component actually experience because of it?

Do this one component at a time. Resist cataloging the whole system in a single pass — a shallow list covering everything is worth less than a complete list for one request path.

## Core Concept 4 — Worked Example: a URL Shortener

Take a small `shorten` service: it accepts a long URL, writes a mapping to Postgres, caches it in Redis, and reads from the cache first on lookup.

Direct dependencies: Postgres (writes, and cold-cache reads), Redis (cache), and the network between the service and both.

Running the method from Concept 3 produces this catalog:

| Component | Failure mode | Observable symptom | Downstream effect |
|---|---|---|---|
| Postgres | Unreachable | Write requests return 500 after a 5s connection timeout | New short links can't be created |
| Postgres | Slow (high latency, no error) | `POST /shorten` p99 climbs from 40ms to 4s | Clients time out even though the server technically "works" |
| Redis | Unreachable | Reads fall through to Postgres; Postgres read load rises | If Postgres was already near capacity, losing the cache can push it over |
| Redis | Returns a stale entry | Lookup returns an outdated mapping | User is redirected to a URL that was since changed or deleted |
| Network (service ↔ Postgres) | Partial packet loss | Some requests succeed, some time out, no clean pattern | Looks like an intermittent app bug, not a network problem, unless you already know to check for it |

The two rows worth re-reading: **"unreachable" and "slow" are different failure modes for the same dependency**, with different symptoms and different fixes. A beginner catalog that only lists "Postgres is down" has covered one row out of five.

## Core Concept 5 — When an Entry Is Actually Done

A failure-mode entry is complete when it has all four parts:

1. A **named component or edge** — which service, which call, not "the backend."
2. A **specific trigger** — unreachable, slow, errors, or wrong data. Pick one; don't lump several triggers into one row.
3. An **observable symptom** stated so a monitor, a log grep, or a human on call could confirm it — a status code, a latency number, a specific log line, never just "it breaks."
4. A **downstream effect** — who else is affected, and how.

If any of the four is missing, the entry isn't ready. Go find the missing piece before moving on to the next component.

---

## Real-World Examples

- **The "database is down" trap.** A junior engineer catalogs only "Postgres down → 500s." Weeks later Postgres gets *slow* (not down) during a nightly maintenance job, and nothing in the runbook describes that, because "slow" was never written down as its own entry.
- **Cache confused with source of truth.** A catalog entry says "Redis down → service down," but the real behavior is a fallback read from Postgres. Writing the wrong downstream effect means the on-call person expects an outage that never happens — and can miss the actual problem, Postgres overload from the extra read traffic.
- **Symptom too vague to use.** "Payment fails" is not a usable symptom. "Payment API returns HTTP 503 for all requests" is — the first can't be matched to any alert, the second can be matched to one directly.

## Common Mistakes

- **Cataloging only total outages.** Every dependency has at least two failure modes worth separating: gone entirely, and degraded (slow, partial errors, wrong data). Beginners usually only write the first.
- **Writing the fault instead of the symptom.** "Disk fills up" is a cause; "writes return `ENOSPC` and the health check starts failing" is the symptom you can actually detect in the moment.
- **Skipping the downstream effect.** A failure-mode row without "who else is affected" can't later be prioritized or acted on.
- **Trying to catalog the whole system in one sitting.** A thin pass over twenty components is worth less than a complete pass over three. Go deep on one request path first.
- **Confusing a failure mode with an incident.** An incident is one specific real event; a failure mode is the general, reusable description that lets you recognize the *next* one of its kind before it happens again.

---

## Apply it

1. Pick one small service you can describe in two sentences — a real one you maintain, or the `shorten` service from Concept 4 — and list every direct dependency it has.
2. For each dependency, write at least two failure modes: "unreachable" and "slow/degraded."
3. For each failure mode, write the observable symptom as a concrete, checkable statement — a status code, a latency threshold, or an exact log message.
4. For each failure mode, write the downstream effect on this service's own callers.
5. Check your table against the four-part checklist from Core Concept 5 and fix any row that's missing a part.

## Verify your work

- Every dependency has at least two distinct failure-mode rows, not just one labeled "down."
- Every symptom is something a monitor, a log grep, or a manual test could confirm — no row reads only "it breaks" or "it fails."
- Every row names a downstream effect, not just the immediate local one.
- A teammate reading only the finished table, with no explanation from you, can tell exactly what to check to confirm each failure mode is actually happening.

## Review questions

- What is the difference between a fault, a failure, and a failure mode?
- Why does "the database is down" need a separate catalog entry from "the database is slow"?
- What four parts must a complete failure-mode entry contain?
- Why is a shallow catalog across an entire system less useful than a complete catalog for one request path?
