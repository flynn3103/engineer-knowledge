# HTTP and APIs — Hands-On Tasks

> **Topic:** [HTTP and APIs](../README.md)

---

## Warm-Up

1. Build a minimal HTTP server with two routes (`GET /health`, `POST /echo`) using Go 1.22+ `ServeMux` method-based routing, with explicit `ReadTimeout`/`WriteTimeout`/`IdleTimeout` set.
2. Write an `http.Client` with a 3-second `Timeout` and make a request to a slow test endpoint (simulate with `time.Sleep`); confirm the client returns a timeout error instead of hanging.
3. Write logging middleware that wraps a handler and logs method, path, status code, and duration.

## Core

4. Implement graceful shutdown: handle `SIGTERM`, call `srv.Shutdown(ctx)` with a 15-second deadline, and verify (manually or with a test) that an in-flight request started just before shutdown completes successfully rather than being cut off.
5. Build a retry-with-backoff-and-jitter helper for outgoing HTTP calls, retrying only on 5xx/network errors (never on 4xx), capped at 4 attempts. Test it against a mock server that fails twice then succeeds.
6. Reuse a single `http.Client` (with a tuned `Transport`) across 100 concurrent outgoing requests to a local test server, and use `httptrace` or connection counting to confirm connections are being reused rather than recreated per request.

## Advanced

7. Implement a simple concurrency-limiting load shedder middleware: past N concurrent in-flight requests, immediately respond `503` with a `Retry-After` header instead of queuing. Load-test with more than N concurrent requests and confirm the excess are shed immediately, not slowly processed.
8. Implement a basic circuit breaker (open/half-open/closed states) around a call to an unreliable dependency; write a test that drives it from closed → open (after enough failures) → half-open (after a cooldown) → closed (after a successful trial call).
9. Build a request chain (handler → service A → service B) sharing a single `context.WithTimeout` derived from the incoming request, and demonstrate that a slow service A call reduces the remaining time budget available to service B (instead of B getting a fresh, independent timeout).

## Capstone

10. Build a small versioned API (`/v1/items` and `/v2/items` with a breaking field-type change between them) with: a consistent JSON error envelope, `Deprecation`/`Sunset` response headers on `/v1`, graceful shutdown, load shedding past a concurrency limit, and a retry-safe idempotent `PUT` endpoint. Write tests covering the error envelope, the deprecation headers, and the load-shedding behavior.

## If you can do all of these, you have the middle level

You can build an HTTP service with real production characteristics — graceful shutdown, connection reuse, safe retries, and consistent error handling — not just a demo that works until the first slow client or dependency failure.

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Interview](interview.md)
