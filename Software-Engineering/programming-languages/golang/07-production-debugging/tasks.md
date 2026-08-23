# Production Debugging — Hands-On Tasks

> **Topic:** [Production Debugging](../README.md)

---

## Warm-Up

1. Add `net/http/pprof` to a small server on an internal-only port, and capture a 10-second CPU profile while running a synthetic CPU-bound load; identify the top function in `go tool pprof`'s `top10`.
2. Adopt `log/slog` for a small service, replacing `log.Printf` calls with structured `logger.Info("event_name", "key", value, ...)` calls, including a request ID field.
3. Deliberately leak a goroutine (block on an unbuffered channel with no receiver) in a test server, capture `/debug/pprof/goroutine?debug=2`, and identify the leaking stack trace in the dump.

## Core

4. Set up basic OpenTelemetry tracing for a two-function call chain (`handleRequest` calling `queryDatabase`), and view the resulting trace (console exporter is fine) showing parent/child spans with timing.
5. Write a script or short program that captures two heap profiles 60 seconds apart from a service with a deliberate slow leak (e.g., a map that's never cleared), and use `go tool pprof -base` to identify the specific call site responsible for the growth.
6. Instrument `db.Stats()` on a connection pool, deliberately undersize `MaxOpenConns` relative to concurrent load, and observe `WaitCount`/`WaitDuration` rising — then fix by resizing the pool and confirm the wait metrics drop.

## Advanced

7. Build a small flame-graph-producing profile (via `go tool pprof -http=:8081`) for a function with a deliberately slow child call nested three levels deep, and practice identifying the wide bar (not the deepest one) as the actual bottleneck.
8. Simulate an on-CPU vs. off-CPU distinction: build one endpoint that's slow due to genuine CPU-bound computation, and another that's slow due to blocking on a simulated slow downstream (e.g., `time.Sleep` standing in for network I/O). Capture a CPU profile for both and explain, in writing, why the second one doesn't show up as "hot" despite being slow.
9. Write a runbook (a short markdown document) for diagnosing "goroutine count climbing" in your own words, referencing the specific `pprof` commands and what to look for at each step — then hand it to someone else and see if they can follow it cold.

## Capstone

10. Build a small service with full production-debugging scaffolding: `net/http/pprof` on an internal port, structured logging with a request ID, basic OpenTelemetry tracing across at least two internal function calls, and a `/internal/status` endpoint exposing goroutine count and connection-pool stats. Then deliberately inject one bug (a goroutine leak, a slow query, or a connection-pool undersizing) and write up a short incident report: detection signal, diagnostic steps taken (with actual `pprof`/trace output), root cause, and the fix.

## If you can do all of these, you have the middle level

You can instrument a service for observability before an incident happens, and when something does go wrong, you can pull the right profile, trace, or log query first — instead of guessing and restarting.

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Interview](interview.md)
