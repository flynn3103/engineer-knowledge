# Error Handling — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Error Handling** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Client errors vs. server errors need different alerting

A `4xx`-equivalent (bad input, not found, unauthorized) is a client mistake — expected traffic noise, not something that should page anyone. A `5xx`-equivalent (database down, unhandled panic, timeout to a dependency) is a server fault and should feed error-rate SLOs and alerting. Conflating the two in metrics (e.g., counting all non-nil errors as "failures") produces alert noise that trains engineers to ignore pages.

### 2. Structured errors survive serialization; string messages don't

Across a gRPC or HTTP boundary, a Go `error` value doesn't cross intact — only what you explicitly serialize does. Using `google.golang.org/grpc/status` (gRPC) or a structured JSON error body (`{"code": "NOT_FOUND", "message": "...", "request_id": "..."}` for HTTP) preserves the error's *kind* across the wire, so the calling service can still branch on it programmatically instead of string-matching a human-readable message.

```go
st := status.New(codes.NotFound, "user not found")
return st.Err()

// caller
if status.Code(err) == codes.NotFound { ... }
```

### 3. Attach a request ID / trace ID to every error that crosses a boundary

An error returned to a client (or logged) without a correlating request ID is nearly useless for incident response in a system with concurrent traffic — you can't find the corresponding logs, traces, or upstream calls. Every error path that reaches a log line or an API response should include the request's trace ID, sourced from `context.Context`.

### 4. Don't leak internal detail into client-facing error messages

```go
// BAD — leaks schema/implementation detail
return fmt.Errorf("pq: duplicate key value violates unique constraint \"users_email_key\"")

// GOOD — client-safe message, full detail logged server-side
log.Printf("db error [req=%s]: %v", reqID, err)
return &AppError{Kind: KindInvalidInput, Message: "email already in use"}
```

Internal errors (stack traces, SQL errors, file paths) are a security and UX concern if surfaced directly to clients — map them to a generic, safe message at the boundary while preserving full detail in server-side logs correlated by request ID.

### 5. Error budgets and SLOs are built on this classification

An SLO like "99.9% of requests succeed" is only meaningful if "success" and "failure" are defined consistently — which requires the client/server fault distinction from concept 1 to already be baked into how errors are counted. Retrofitting this distinction after an SLO is already in place, once metrics have been recorded inconsistently for months, is expensive; get the classification right early.

---

## Worked Example — An Alert Storm From Miscounted Client Errors

A service's error-rate alert fired at 2 a.m. for three nights running, each time traced to a burst of a specific `400 Bad Request` from a misbehaving upstream client retrying malformed requests. The alert was defined on "any non-2xx response," conflating client and server faults. The fix: split the metric into `client_error_total` (4xx-equivalent) and `server_error_total` (5xx-equivalent), and re-scope the paging alert to only the latter — instantly eliminating the false pages without losing visibility (the client-error metric remained available on a dashboard for investigating the misbehaving upstream separately).

---

## Best Practices

1. Classify every error as client-fault or server-fault at the point it's produced, and count them separately in metrics.
2. Use structured, code-based errors (gRPC status codes, a JSON error envelope) across service boundaries — never bare strings.
3. Thread a request/trace ID through `context.Context` and attach it to every log line and client-facing error.
4. Never expose raw internal error detail (SQL errors, stack traces, file paths) in a client-facing response.

---

## Edge Cases & Pitfalls

- **A downstream 5xx surfaced as-is** can misclassify what should be *your* service's client-facing error (e.g. treating a downstream's internal error as your own service's fault when it might actually indicate the caller sent a request your downstream can't handle).
- **Sensitive data in error messages** (emails, tokens, internal hostnames) logged or returned to clients is a real security/compliance issue — sanitize before crossing a trust boundary.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Counting all non-nil errors as "failures" in SLO metrics | Split client-fault vs. server-fault explicitly |
| Returning raw internal error strings to API clients | Map to a generic, safe client-facing message; log full detail server-side |
| Errors crossing a service boundary as unstructured strings | Use gRPC status codes or a structured JSON error envelope |

---

## Common Misconceptions

> *"More detailed error messages are always better for clients."* — Not when the detail leaks internal implementation and provides no actionable next step. Client-facing messages should be safe and actionable; full detail belongs in server-side, request-ID-correlated logs.

---

## Apply it

1. State the system invariant that **Error Handling** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Error Handling fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
