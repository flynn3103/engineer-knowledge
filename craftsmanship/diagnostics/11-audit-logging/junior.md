# Audit Logging — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Audit Logging** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Audit Logging Roadmap](README.md)
> **Focus:** What an audit log *is*, and why it is not the same thing as your application log. The five questions every audit event must answer — *who, what, which, when, outcome*. Writing your first audit event to a separate sink. The first-principles reasons audit logging exists at all.

---

## Core Concepts

### 1. An Audit Log Is a Record of *Deliberate Actions*, Not of *Code Execution*

Your app log records what the *code* did: "entering `processOrder`", "cache miss", "retrying connection". Your audit log records what a *person or principal deliberately caused*: "alice@corp deleted customer 4471". The unit of an app log is a line of execution. The unit of an audit log is an **intentional act by an identified actor**. If no human or principal *decided* to do the thing, it is probably not an audit event — it's an app log.

### 2. The Five W's Are Non-Negotiable

Every audit event must answer five questions. If any one is missing, the event is much less useful — sometimes useless:

| W | Field | Example |
|---|-------|---------|
| **Who** | actor | `user:alice@corp.com` |
| **What** | action | `delete` |
| **Which** | resource | `customer:4471` |
| **When** | timestamp | `2026-06-11T14:02:09.471Z` (UTC) |
| **Outcome** | result | `success` / `denied` |

A sixth — **where/from** (source IP, device, session) — and a seventh — **why** (a reason, a ticket number) — are strongly recommended. But the five above are the floor.

### 3. Audit Logs Go to a *Separate* Place

This is the single most important practical rule at the junior level. An audit event does **not** go into the same stream as `logger.debug("...")`. It goes to a *separate logger writing to a separate sink* — a different file, a different table, a different stream. Why?

- App logs get **sampled and dropped** under load. Audit logs must not.
- App logs get **deleted in days**. Audit logs are kept for years.
- App logs are **readable by every engineer**. Audit logs often need restricted access.
- App logs are full of **noise**; you cannot find the one "who deleted this?" line among a million debug lines.

Mixing them is the original sin of audit logging. Keep them apart from line one.

### 4. Completeness Beats Verbosity

For an app log, you trade completeness for signal — you drop noise on purpose. For an audit log, the *point* is completeness: every login, every permission change, every sensitive access, recorded. You would rather have a boring, complete audit log than an interesting, sampled one. **If a security-relevant action can happen, it must be audited every single time.**

### 5. The Actor Must Be the *Real* Actor

"System did X" is a useless audit event. *Which user, through which session, triggered the system to do X?* If an admin acts on behalf of a customer (impersonation, support tooling), the audit event must capture *both*: the admin (who really did it) and the customer (on whose behalf). Attribution is the heart of the audit log; getting the actor wrong defeats the entire exercise.

### 6. Audit Events Are Written *After* the Action's Outcome Is Known

You cannot record the outcome before you have it. The audit write generally happens at the end of the operation, once you know whether it succeeded or was denied. A denied attempt (`alice tried to delete customer 4471 — DENIED`) is often *more* valuable than a success, because it can be the first sign of an attack or a misconfigured permission.

---

## The Anatomy of an Audit Event

A minimal but correct audit event, as JSON:

```json
{
  "timestamp": "2026-06-11T14:02:09.471Z",
  "actor": { "type": "user", "id": "alice@corp.com", "session_id": "sess_9f3a" },
  "action": "customer.delete",
  "resource": { "type": "customer", "id": "4471" },
  "outcome": "success",
  "source_ip": "203.0.113.42",
  "request_id": "req_7af3c1",
  "metadata": { "reason": "GDPR erasure request TICKET-882" }
}
```

Walk through each field:

| Field | Why it's here |
|-------|---------------|
| `timestamp` | **When.** Always UTC, always with millisecond precision and a `Z`. Local time and ambiguous formats ruin forensic ordering. |
| `actor` | **Who.** A *type* (user/service/apikey) plus a stable *id*. The session ties it to a specific login. |
| `action` | **What.** A stable, machine-readable verb — `customer.delete`, not "deleted a customer". You'll query on this. |
| `resource` | **Which.** Type + id of the thing acted upon. |
| `outcome` | **Result.** `success`, `failure`, or `denied`. Never omit this — a denied action is a security signal. |
| `source_ip` | **From where.** Helps spot "this admin acted from a country they've never logged in from." |
| `request_id` | **Correlation.** Links the audit event to the operational logs/traces for the same request. |
| `metadata` | **Why / context.** A reason, a ticket, the old and new value of a changed field. Keep it small and relevant. |

### The action naming convention

Pick a convention and hold it. The common one is `resource.verb` in lower snake/dot case:

```text
auth.login          auth.logout         auth.login_failed
user.create         user.delete         user.role_granted
customer.read       customer.export     customer.update
billing.refund      config.change       data.export
```

Stable names matter because in two years someone will run `WHERE action = 'customer.export'` across six years of data. If half your events say `exported_customer` and half say `customer.export`, that query silently misses records.

---

## Audit Log vs Application Log

This table is the heart of the junior level. Internalize it.

| Dimension | Application / Debug Log | Audit Log |
|---|---|---|
| **Question answered** | "What is the system doing?" | "Who did what, and can I prove it?" |
| **Primary consumer** | On-call engineers | Security, compliance, legal, auditors |
| **Unit** | A line of code execution | A deliberate act by an identified actor |
| **Sampling** | Fine — drop noise to save money | **Forbidden** — completeness is the point |
| **Retention** | Days to weeks | Months to **years** (often legally mandated) |
| **Tampering** | Tolerable in extreme cases | **Unacceptable** — must be tamper-evident |
| **PII** | Avoid logging it | Often *required* — the actor identity is the point |
| **Storage** | Cheap, hot, mutable | Separate, restricted, ideally append-only |
| **Format** | Structured-ish; freeform tolerated | Strictly structured, schema-stable |
| **Failure handling** | Drop the line, move on | Failing to write may need to *block* or alert |

> The clearest tell that someone has confused the two: a `logger.info("user alice deleted customer 4471")` sitting in the middle of the application log stream. It's not queryable, it's not retained long enough, it'll be sampled away under load, and there is no integrity guarantee. It *looks* like an audit log and is not one.

For the operational side of logging — levels, correlation IDs, sampling, libraries — see [`../02-logging/junior.md`](../02-logging/junior.md) and [`../02-logging/middle.md`](../02-logging/middle.md). This roadmap is deliberately the *other* discipline.

---

## Code Examples

The examples all do the same thing: emit a structured audit event to a **separate sink** from the application log. That separation is the lesson; everything else is detail.

### Go — `slog` with a dedicated audit logger

```go
package audit

import (
	"context"
	"log/slog"
	"os"
	"time"
)

// auditLogger writes ONLY audit events, to its own file — never mixed
// with the application log. In production this file is shipped to a
// restricted, append-only store (see senior.md).
var auditLogger *slog.Logger

func init() {
	f, err := os.OpenFile("/var/log/app/audit.log",
		os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0o640)
	if err != nil {
		// If we cannot open the audit sink, that is a startup failure —
		// do not silently fall back to stdout. (See "Common Mistakes".)
		panic("cannot open audit log: " + err.Error())
	}
	auditLogger = slog.New(slog.NewJSONHandler(f, &slog.HandlerOptions{
		Level: slog.LevelInfo,
	}))
}

type Actor struct {
	Type      string // "user", "service", "apikey"
	ID        string
	SessionID string
}

// Record writes one audit event. Outcome is "success", "failure", or "denied".
func Record(ctx context.Context, a Actor, action, resType, resID, outcome string, meta map[string]any) {
	auditLogger.LogAttrs(ctx, slog.LevelInfo, "audit",
		slog.Time("timestamp", time.Now().UTC()),
		slog.Group("actor",
			slog.String("type", a.Type),
			slog.String("id", a.ID),
			slog.String("session_id", a.SessionID),
		),
		slog.String("action", action),
		slog.Group("resource",
			slog.String("type", resType),
			slog.String("id", resID),
		),
		slog.String("outcome", outcome),
		slog.String("request_id", requestIDFromCtx(ctx)),
		slog.Any("metadata", meta),
	)
}
```

Usage at the call site, *after* the outcome is known:

```go
func (h *Handler) DeleteCustomer(w http.ResponseWriter, r *http.Request) {
	id := chi.URLParam(r, "id")
	actor := actorFromCtx(r.Context())

	err := h.store.DeleteCustomer(r.Context(), id)
	outcome := "success"
	if err != nil {
		outcome = "failure"
	}
	// Audit happens regardless of success/failure.
	audit.Record(r.Context(), actor, "customer.delete", "customer", id, outcome,
		map[string]any{"reason": r.Header.Get("X-Reason")})

	if err != nil {
		http.Error(w, "delete failed", http.StatusInternalServerError)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
```

### Python — `logging` with a separate handler

```python
import json
import logging
from datetime import datetime, timezone

# A dedicated logger. propagate=False stops audit events from also
# flowing into the root (application) logger.
audit_log = logging.getLogger("audit")
audit_log.propagate = False
audit_log.setLevel(logging.INFO)

_handler = logging.FileHandler("/var/log/app/audit.log")
_handler.setFormatter(logging.Formatter("%(message)s"))  # message is already JSON
audit_log.addHandler(_handler)

def record(actor: dict, action: str, resource: dict, outcome: str,
           request_id: str | None = None, metadata: dict | None = None) -> None:
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor,                 # {"type": "user", "id": "alice@corp", "session_id": "..."}
        "action": action,               # "customer.delete"
        "resource": resource,           # {"type": "customer", "id": "4471"}
        "outcome": outcome,             # "success" | "failure" | "denied"
        "request_id": request_id,
        "metadata": metadata or {},
    }
    audit_log.info(json.dumps(event, separators=(",", ":")))
```

```python
@app.delete("/customers/{cust_id}")
def delete_customer(cust_id: str, request: Request):
    actor = actor_from_request(request)
    try:
        store.delete_customer(cust_id)
        outcome = "success"
    except Exception:
        outcome = "failure"
        raise
    finally:
        record(
            actor=actor,
            action="customer.delete",
            resource={"type": "customer", "id": cust_id},
            outcome=outcome,
            request_id=request.headers.get("X-Request-ID"),
            metadata={"reason": request.headers.get("X-Reason")},
        )
    return Response(status_code=204)
```

### Java — SLF4J with a dedicated audit logger and appender

A *named* logger routed to its own file via Logback configuration:

```xml
<!-- logback.xml -->
<configuration>
  <!-- The application log -->
  <appender name="APP" class="ch.qos.logback.core.ConsoleAppender">
    <encoder><pattern>%d %-5level %logger - %msg%n</pattern></encoder>
  </appender>

  <!-- A SEPARATE appender just for audit, writing JSON to its own file -->
  <appender name="AUDIT" class="ch.qos.logback.core.FileAppender">
    <file>/var/log/app/audit.log</file>
    <encoder class="net.logstash.logback.encoder.LogstashEncoder"/>
  </appender>

  <!-- Route the "audit" logger ONLY to the AUDIT appender, never to APP -->
  <logger name="audit" level="INFO" additivity="false">
    <appender-ref ref="AUDIT"/>
  </logger>

  <root level="INFO">
    <appender-ref ref="APP"/>
  </root>
</configuration>
```

```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import net.logstash.logback.argument.StructuredArguments;
import java.time.Instant;
import java.util.Map;

public final class Audit {
    // The logger name "audit" matches the <logger name="audit"> above.
    private static final Logger AUDIT = LoggerFactory.getLogger("audit");

    public static void record(Actor actor, String action, String resType,
                              String resId, String outcome, Map<String, Object> meta) {
        AUDIT.info("audit",
            StructuredArguments.keyValue("timestamp", Instant.now().toString()),
            StructuredArguments.keyValue("actor", actor),
            StructuredArguments.keyValue("action", action),
            StructuredArguments.keyValue("resource",
                Map.of("type", resType, "id", resId)),
            StructuredArguments.keyValue("outcome", outcome),
            StructuredArguments.keyValue("metadata", meta));
    }
}
```

### Node.js — Pino with a separate transport

```js
const pino = require("pino");

// A dedicated audit logger writing to its own file destination.
// Do NOT reuse the application logger instance.
const auditLogger = pino(
  { base: null, timestamp: pino.stdTimeFunctions.isoTime },
  pino.destination({ dest: "/var/log/app/audit.log", sync: false })
);

function recordAudit({ actor, action, resource, outcome, requestId, metadata }) {
  auditLogger.info({
    event: "audit",
    actor,                 // { type, id, sessionId }
    action,                // "customer.delete"
    resource,              // { type, id }
    outcome,               // "success" | "failure" | "denied"
    requestId,
    metadata: metadata || {},
  });
}

// Express handler
app.delete("/customers/:id", async (req, res) => {
  const actor = actorFromReq(req);
  let outcome = "success";
  try {
    await store.deleteCustomer(req.params.id);
  } catch (err) {
    outcome = "failure";
    throw err;
  } finally {
    recordAudit({
      actor,
      action: "customer.delete",
      resource: { type: "customer", id: req.params.id },
      outcome,
      requestId: req.headers["x-request-id"],
      metadata: { reason: req.headers["x-reason"] },
    });
  }
  res.sendStatus(204);
});
```

Across all four: the audit logger is a *distinct object* pointed at a *distinct destination*, and the event carries the five W's. That is the whole junior-level lesson, expressed four ways.

---

## What to Audit on Day One

You do not need to audit everything. Start with the high-value, security-relevant events. A tiny app should audit at least:

| Category | Examples |
|---|---|
| **Authentication** | login success, login failure, logout, password change, MFA enrollment |
| **Authorization changes** | role granted/revoked, permission changed, account enabled/disabled |
| **Sensitive data access** | reading/exporting customer PII, downloading a report, viewing a medical record |
| **Sensitive data changes** | create/update/delete of records that matter (customers, money, config) |
| **Administrative actions** | impersonation, settings changes, key rotation, feature flags affecting security |
| **Data export** | any bulk export — the single most-audited action in breach investigations |

A useful filter: *"If this action showed up in a breach investigation or a compliance audit, would someone want a record of it?"* If yes, audit it.

What you usually do **not** audit (these are app-log territory): page views, health-check pings, internal retries, cache hits, every individual row of a normal read. Auditing those buries the signal and explodes your storage.

---

## Pros & Cons of Approaches

| Approach | Pros | Cons |
|---|---|---|
| **Audit into the app log** (the anti-pattern) | Zero extra setup | Sampled away under load; deleted in days; unqueryable; no integrity; mixes with noise. **Avoid.** |
| **Separate audit file/stream** (junior default) | Simple; clean separation; easy to ship to a restricted store | Still mutable on disk; integrity is up to the downstream store |
| **Audit to a dedicated DB table** | Queryable; transactional with the action; structured | Mutable unless you enforce append-only; needs care to not block the request |
| **Audit to a managed service** (CloudTrail, GCP Audit Logs) | Tamper-resistant, retained, queryable by default | Covers *infrastructure* actions, not your app's business actions; you still write your own for those |

At junior level, **separate file/stream** or a **dedicated table** is the right answer. The managed services are great but they audit *cloud API calls*, not "alice deleted customer 4471 in your app."

---

## Coding Patterns

### Pattern 1 — Audit at the Boundary, Once

Write the audit event at the *handler/service boundary* where the deliberate action enters, not scattered through ten helper functions. One action → one audit call, in one place.

```python
# Good: one audit call, at the boundary, after the outcome is known.
def handle_delete(req):
    outcome = do_delete(req)           # may raise/return failure
    record(actor=..., action="customer.delete", resource=..., outcome=outcome)
```

### Pattern 2 — Always in a `finally` / `defer`

You must record the event *whether or not the action succeeded*. Put the audit write where it runs on both paths.

```go
outcome := "success"
defer func() { audit.Record(ctx, actor, "customer.delete", "customer", id, outcome, nil) }()
if err := store.Delete(ctx, id); err != nil {
	outcome = "failure"
	return err
}
```

### Pattern 3 — A Tiny, Explicit Event Type

Don't pass loose strings everywhere. A small struct/dataclass with the five W's as named fields makes it impossible to forget one.

```python
@dataclass
class AuditEvent:
    actor: Actor
    action: str
    resource: Resource
    outcome: str             # forces you to set it
    metadata: dict = field(default_factory=dict)
```

### Pattern 4 — Capture the Actor at the Edge

The real actor lives in the request context (the authenticated session). Extract it once at the middleware layer and pass it down — never reconstruct "who is this" deep in the call stack where you might get it wrong.

---

## Clean Code

- **Never** write audit events with `logger.info(...)` on your application logger. Use a *named, separate* audit logger.
- Name actions as stable machine identifiers (`customer.delete`), not human sentences ("deleted a customer").
- Always include `outcome`. An audit event without an outcome is half a record.
- Timestamps are **UTC, ISO 8601, millisecond precision**. No local time, ever.
- Don't put secrets (passwords, tokens, full card numbers) in the audit event — record *that* a password changed, not the password. (More in `senior.md` on minimization.)
- One action, one event. Don't emit five events for one logical delete.
- Keep `metadata` small and relevant. The audit log is not a place to dump the whole request body.

---

## Best Practices

1. **Separate sink from line one.** A distinct logger to a distinct destination. This is the rule that prevents the most pain later.
2. **Capture all five W's, plus source and request ID.** Treat a missing W as a bug.
3. **Audit denials, not just successes.** A blocked action is a security signal.
4. **Write the event after the outcome is known**, on both the success and failure paths.
5. **Use stable, queryable action names.** You will query them years later.
6. **Get the actor from the authenticated context**, captured once at the edge.
7. **Don't sample, don't drop, don't level-filter** audit events. They are not `DEBUG`.
8. **Start with the high-value events** (auth, authz, sensitive access/changes, exports) and grow from there.

---

## Edge Cases & Pitfalls

- **The "system" actor.** When a cron job or background worker acts, the actor is a *service account*, not a blank. Record `actor.type=service, id=nightly-reconciler`. "Who: (empty)" is a bug.
- **Impersonation / on-behalf-of.** A support agent acting as a customer must record *both* identities. Recording only the customer hides the agent; recording only the agent loses the affected resource. (Deep dive in `middle.md` and `senior.md`.)
- **Failed login = no logged-in user yet.** The actor for `auth.login_failed` is the *attempted* identity (the username typed), plus the source IP. You can't use a session that doesn't exist.
- **Bulk actions.** Deleting 10,000 records: do you emit 10,000 events or one event with a count? At junior level, one event with `metadata.count` is usually fine, but know that for some regimes each record access must be individually auditable.
- **Time zones and clock skew.** Two servers with skewed clocks produce out-of-order audit events. Always UTC; rely on NTP. (Ordering is a senior/professional topic.)
- **Audit write fails.** If the audit sink is down, what happens to the action? At junior level, at minimum *alert loudly* — never silently swallow. (The "fail-open vs fail-closed" decision is a senior topic.)

---

## Common Mistakes

1. **Putting audit events in the application log.** The number-one mistake. Different consumer, retention, integrity needs. Use a separate sink.
2. **Omitting the outcome.** "Alice deleted customer 4471" — did it *succeed*? A denied attempt looks identical without `outcome`.
3. **Recording "system did X" with no real actor.** The whole point is attribution. Find the principal.
4. **Human-sentence action names.** `"deleted the customer record"` can't be queried; `customer.delete` can.
5. **Local timestamps / ambiguous formats.** `06/11/26 2:02 PM` is forensically useless. Use UTC ISO 8601.
6. **Sampling or level-filtering audit events.** Treating them as `DEBUG`/`INFO` that can be dropped. They are not.
7. **Logging secrets into the audit event.** Recording the new password instead of "password changed". A breach in the audit log itself.
8. **Auditing everything indiscriminately.** Auditing every page view buries the real signals and explodes cost. Audit *deliberate, significant* actions.
9. **Silently swallowing audit-write failures.** If you can't record it, at least scream about it.
10. **Reconstructing the actor deep in the stack** instead of capturing it once at the authenticated edge — and getting it wrong.

---

## Tricky Points

1. **Audit logging is the *opposite* of normal logging on PII.** Standard logging advice says "don't log PII." Audit logging often *requires* PII — the actor's identity is the entire point. The two disciplines have inverted rules; don't apply app-log instincts blindly.
2. **A successful action and a denied action are both audit events.** Beginners audit only the happy path. The denied path is often the more important security signal.
3. **The actor of a failed login is not a user object.** There's no session yet. The actor is the *claimed* identity plus the origin.
4. **"Audit" and "log" share a verb but not a discipline.** They look the same in code (`logger.info`) and are completely different in purpose, retention, and integrity. The similarity is a trap.
5. **The timestamp on the event is the *server's* time of recording, not necessarily the *user's* clock.** Be clear about which clock you mean. For forensics, server UTC at the moment of the action is standard.
6. **Where you write the event matters as much as what you write.** A perfect event in a mutable, sampled, 3-day-retention stream is not an audit log.

---

## Apply it

1. Choose one small, known input for **Audit Logging**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Audit Logging solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
