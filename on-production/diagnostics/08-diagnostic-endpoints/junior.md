# Diagnostic Endpoints — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Diagnostic Endpoints** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Diagnostic Endpoints Roadmap](README.md)
> **Focus:** What a diagnostic endpoint is. Liveness vs readiness. Your first `/healthz` and `/metrics`. Why a running service exposes URLs that nobody outside the team is ever supposed to call.

---

## Core Concepts

### 1. A Diagnostic Endpoint Talks About the Service, Not the Data

The handler for `/orders` returns orders. The handler for `/healthz` returns *the service's opinion of itself*. This is the defining distinction. When you see a path like `/health`, `/ready`, `/metrics`, `/version`, `/debug/*`, `/actuator/*` — you're looking at the **control and introspection surface**, not the product. Different audience, different rules, different security posture.

### 2. Liveness and Readiness Answer Two Different Questions

This is the single most important idea on this page, and the one juniors most often get wrong.

- **Liveness** = *"Am I broken in a way only a restart can fix?"* Examples of a real liveness failure: a deadlock where every request hangs forever, a corrupted in-memory state, an event loop that stopped turning. The orchestrator's response: **kill and restart me.**
- **Readiness** = *"Should traffic come to me *right now*?"* Examples of a real readiness failure: I'm still loading a 2 GB model into memory, my database connection pool is temporarily empty, I'm draining before shutdown. The orchestrator's response: **leave me running, just stop routing to me.**

If you swap them, disaster follows. Put "is the database reachable?" in your *liveness* check, and a 30-second database blip will make Kubernetes **restart every single one of your pods at once** — turning a recoverable hiccup into a full outage. (More on this exact failure in `senior.md`.)

### 3. The Status Code *Is* the Answer

Health endpoints communicate through the HTTP status code, not the body. `200` means healthy; anything else (almost always `503`) means not. The body is for *humans* reading `curl` output — it can say *why* — but the machine probing you only reads the code. Get the code right first.

### 4. Cheap Checks Beat Thorough Checks

A health check runs *constantly* — every few seconds, on every instance, forever. If your check does real work (queries the DB, calls another service), you've built a tiny load test that runs 24/7 and can amplify outages. A liveness check should be nearly free: *"is my process responding to HTTP at all?"* often just returns `200 ok` and that's correct.

### 5. `/metrics` Is a Snapshot, Not a Log

`/metrics` exposes *current values* of counters and gauges — `http_requests_total 48213`, `goroutines 142`. It is read on a schedule by a monitoring system, which stores the time series. You don't call `/metrics` to "log an event"; you increment a counter in your code, and `/metrics` reports the running total whenever it's scraped. See [`../04-metrics/junior.md`](../04-metrics/junior.md) for the signals themselves.

### 6. These Endpoints Leak Internals — Treat Them Carefully

`/metrics` reveals your traffic volumes and error rates. `/version` reveals your exact build (and thus its known CVEs). `/debug/pprof` can dump memory. None of this should be reachable by the public internet. Even as a junior, internalize: **diagnostic endpoints are not public endpoints.** `senior.md` and `professional.md` go deep on this; for now, know that they belong behind auth, on a separate port, or both.

---

## The First Toolkit

Your day-one diagnostic toolkit is small:

1. **A `/healthz` endpoint** that returns `200 ok`. (`z` is a Google convention to avoid clashing with a real `/health` business page.)
2. **A `/readyz` endpoint** that returns `200` only once startup is finished and dependencies you *truly need* are usable.
3. **A `/metrics` endpoint** using your language's Prometheus client library.
4. **A `/version` (or `/buildinfo`) endpoint** returning the git SHA and build time, so you can answer *"did the new version actually deploy?"* in one `curl`.
5. **`curl`** — your client for all of the above. `curl -i localhost:8080/healthz` shows you the status code (`-i` prints headers).

That's the whole starter kit. Everything else in this roadmap — pprof, heap dumps, runtime toggles, continuous profiling — is depth on top of these four endpoints.

---

## Code Examples

The same four endpoints — `/healthz`, `/readyz`, `/metrics`, `/version` — in four ecosystems. Read them side by side; the *shape* is identical everywhere.

### Go — `net/http`, `expvar`, and Prometheus

```go
package main

import (
	"encoding/json"
	"net/http"
	"sync/atomic"

	"github.com/prometheus/client_golang/prometheus/promhttp"
)

// ready is flipped to true once startup finishes. Atomic so the probe
// goroutine and the startup goroutine don't race on it.
var ready atomic.Bool

var buildInfo = map[string]string{
	"version":   "1.4.2",
	"gitSHA":    "a1b2c3d",
	"buildTime": "2026-06-11T09:00:00Z",
}

func main() {
	mux := http.NewServeMux()

	// LIVENESS: dirt cheap. If the process can answer HTTP, it's alive.
	// Never touch the DB or downstreams here.
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("ok"))
	})

	// READINESS: 200 only once we've finished booting (and, if you truly
	// need them, only when required dependencies are usable).
	mux.HandleFunc("/readyz", func(w http.ResponseWriter, r *http.Request) {
		if !ready.Load() {
			http.Error(w, "still starting", http.StatusServiceUnavailable)
			return
		}
		w.Write([]byte("ready"))
	})

	// VERSION: which build is actually running?
	mux.HandleFunc("/version", func(w http.ResponseWriter, r *http.Request) {
		json.NewEncoder(w).Encode(buildInfo)
	})

	// METRICS: Prometheus exposition format.
	mux.Handle("/metrics", promhttp.Handler())

	go warmUp() // simulate slow startup

	http.ListenAndServe(":8080", mux)
}

func warmUp() {
	// ... load config, prime caches, open the DB pool ...
	ready.Store(true) // now and only now do we accept traffic
}
```

Go's standard library also ships **`expvar`**: importing it registers `/debug/vars`, a JSON blob of runtime counters (memory stats, GC, plus anything you publish). It's the zero-dependency cousin of `/metrics`:

```go
import (
	"expvar"
	_ "expvar" // registers /debug/vars on http.DefaultServeMux
)

var ordersProcessed = expvar.NewInt("orders_processed")

// later: ordersProcessed.Add(1)
// curl localhost:8080/debug/vars  ->  {"orders_processed": 42, "memstats": {...}}
```

### Python — Flask + `prometheus_client`

```python
# pip install flask prometheus_client
from flask import Flask, Response
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
import threading

app = Flask(__name__)

_ready = threading.Event()  # set once startup completes

BUILD = {"version": "1.4.2", "git_sha": "a1b2c3d", "build_time": "2026-06-11T09:00:00Z"}
requests_total = Counter("http_requests_total", "Total HTTP requests", ["path"])

@app.get("/healthz")          # LIVENESS — cheap, no dependencies
def healthz():
    return "ok", 200

@app.get("/readyz")           # READINESS — only after warm-up
def readyz():
    if not _ready.is_set():
        return "still starting", 503
    return "ready", 200

@app.get("/version")
def version():
    return BUILD, 200

@app.get("/metrics")          # Prometheus exposition
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

def warm_up():
    # ... prime caches, open the DB pool ...
    _ready.set()

if __name__ == "__main__":
    threading.Thread(target=warm_up, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
```

### Node.js — Express + `prom-client`

```js
// npm i express prom-client
const express = require("express");
const client = require("prom-client");

const app = express();
let ready = false; // flipped true after warm-up

const BUILD = { version: "1.4.2", gitSha: "a1b2c3d", buildTime: "2026-06-11T09:00:00Z" };
const registry = new client.Registry();
client.collectDefaultMetrics({ register: registry }); // event-loop lag, heap, etc.

app.get("/healthz", (_req, res) => res.status(200).send("ok"));          // liveness

app.get("/readyz", (_req, res) =>                                        // readiness
  ready ? res.status(200).send("ready") : res.status(503).send("starting"));

app.get("/version", (_req, res) => res.json(BUILD));

app.get("/metrics", async (_req, res) => {                                // metrics
  res.set("Content-Type", registry.contentType);
  res.send(await registry.metrics());
});

app.listen(8080, () => {
  setTimeout(() => { ready = true; }, 3000); // simulate slow warm-up
});
```

### Java — Spring Boot Actuator (almost no code)

The JVM's answer is **Actuator**: add one dependency and you get `/actuator/health`, `/actuator/info`, `/actuator/metrics`, and more, for free.

```xml
<!-- pom.xml -->
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<!-- For /metrics in Prometheus format: -->
<dependency>
  <groupId>io.micrometer</groupId>
  <artifactId>micrometer-registry-prometheus</artifactId>
</dependency>
```

```properties
# application.properties
# Liveness vs readiness as SEPARATE health groups (Spring supports this directly):
management.endpoint.health.probes.enabled=true
management.health.livenessstate.enabled=true
management.health.readinessstate.enabled=true

# Prometheus scrape endpoint at /actuator/prometheus
management.endpoints.web.exposure.include=health,info,metrics,prometheus

# Put diagnostics on a SEPARATE port (see senior.md on why this matters):
management.server.port=9090
```

Now `curl localhost:9090/actuator/health/liveness` and `.../readiness` return `{"status":"UP"}` separately, and `/actuator/prometheus` is your `/metrics`. You wrote zero handler code.

---

## Health vs Metrics — Don't Confuse Them

Juniors routinely blur these. They answer different questions for different consumers:

| | Health/readiness | `/metrics` |
|---|---|---|
| **Question it answers** | "Should I get traffic / be restarted?" | "How much / how fast / how many?" |
| **Consumer** | Load balancer, Kubernetes | Prometheus, dashboards, alerts |
| **Response** | A status code (`200`/`503`) | A block of numbers |
| **Called when** | Every few seconds, per instance | Every scrape interval (e.g. 15s) |
| **What failure means** | "Take action on this instance" | Nothing — it's just data |
| **Should it be cheap?** | Yes, extremely | Yes (don't compute on scrape) |

A health check that returns rich metrics is over-engineered. A `/metrics` endpoint that load balancers probe for routing is misused. Keep the lanes separate.

---

## Coding Patterns

### Pattern 1 — Separate Liveness From Readiness From Day One

```go
mux.HandleFunc("/healthz", liveness)  // restart me if this fails
mux.HandleFunc("/readyz", readiness)  // skip me if this fails
```

Even if both return `200` today, having two endpoints means you can evolve them independently without re-plumbing your probes later.

### Pattern 2 — The Readiness Flag

```python
_ready = threading.Event()
# ... after warm-up ...
_ready.set()
```

A single boolean/event flipped at the end of startup is the simplest correct readiness signal. Default it to *not ready* so you never accept traffic before you're done booting.

### Pattern 3 — Liveness Returns a Constant

```js
app.get("/healthz", (_req, res) => res.status(200).send("ok"));
```

The cheapest possible handler. If the process can run this, it's alive enough to keep. Resist the urge to "make it more useful" by adding checks — that's how you accidentally turn a DB blip into a restart storm.

### Pattern 4 — Echo the Build So You Can Trust the Deploy

```go
mux.HandleFunc("/version", func(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(buildInfo) // version, gitSHA, buildTime
})
```

The first question in many incidents is "what's actually running?" A `/version` endpoint answers it in seconds instead of guessing from CI logs.

---

## Clean Code

- Use the conventional paths: `/healthz`, `/readyz`, `/metrics`, `/version`. Operators and tooling expect them; don't invent `/are-you-ok`.
- **Default readiness to false.** A service that's "ready" before it finished booting is worse than one that's slow to come up.
- Keep liveness free of I/O. No DB, no downstream calls, no disk.
- Don't log on every health probe — they fire every few seconds and will drown your logs. (See [`../02-logging/junior.md`](../02-logging/junior.md).)
- Put diagnostic handlers in one obvious place (`diagnostics.go`, `health.py`) so the next person finds them instantly.
- Never expose secrets via `/version` or `/metrics` — no DB passwords, no API keys, no full config dumps. (Big topic in `senior.md`.)

---

## Best Practices

1. **Two endpoints, two questions.** Liveness ("restart me") and readiness ("skip me") are distinct. Implement both.
2. **Liveness must not depend on anything but the process itself.** No databases, no caches, no other services.
3. **Readiness may check *required* dependencies — sparingly.** Only the ones without which you genuinely cannot serve a single request, and even then, prefer "is the pool open?" over "run a query."
4. **Make checks cheap.** They run forever, on every instance.
5. **Use a real metrics library**, not hand-rolled string concatenation — `prometheus_client`, `prom-client`, Micrometer, `client_golang`. They get the format and escaping right.
6. **Expose `/version`.** One `curl` should tell you the exact running build.
7. **Don't put diagnostics on the public internet.** Even before you learn the full security story, default to a separate port or localhost binding.
8. **Test your health logic.** A health check that always returns `200` even when the process is broken is worse than none — it lies confidently.

---

## Edge Cases & Pitfalls

- **The "always 200" liveness that lies.** If your handler returns `200` no matter what, a wedged process is never restarted. (But don't overcorrect — see the DB-in-liveness trap below.)
- **The database in the liveness check.** The classic catastrophe: a brief DB outage makes liveness fail on every pod, the orchestrator restarts them all simultaneously, and now you have *zero* capacity plus a thundering herd of reconnects. DB belongs (cautiously) in readiness, never liveness.
- **Readiness that never flips back.** If you set `ready = true` and never set it `false` during shutdown, the LB keeps sending requests to a draining pod. (Graceful shutdown is a `middle.md` topic.)
- **Forgetting the startup window.** A 40-second boot plus a liveness probe that starts at second 5 means the orchestrator kills the pod before it ever comes up — an infinite crash loop. Use a startup probe or a generous initial delay.
- **Logging every probe.** Thousands of `GET /healthz 200` lines per hour bury the logs that matter.
- **`/metrics` doing work on scrape.** Computing expensive values *inside* the metrics handler means every scrape (every 15s) runs that work. Update metrics as events happen; just *report* on scrape.
- **Health endpoint on the public port.** Now anyone on the internet can probe your internals and infer your deploy times and traffic.

---

## Common Mistakes

1. **Treating liveness and readiness as the same thing.** They trigger opposite actions (restart vs skip). Conflating them turns recoverable issues into outages.
2. **Putting downstream dependencies in liveness.** A dependency blip should never restart your process.
3. **Returning `200` for everything in readiness**, so traffic arrives before the service can serve it — users get errors during every deploy.
4. **Hand-writing the Prometheus format.** Miss one newline or escape and the whole scrape fails. Use the library.
5. **Exposing diagnostics publicly.** `/metrics` and `/version` on the open internet hand attackers a reconnaissance map.
6. **No `/version` endpoint**, so "is the fix live?" becomes a 20-minute archaeology dig through CI.
7. **Health checks that block.** A slow check (full DB query) can time out and be read as a *failure*, restarting a perfectly fine pod.
8. **Logging or allocating heavily inside the probe handler.** Multiply by "every few seconds, forever" and it adds up.

---

## Tricky Points

1. **`/healthz` returning `200` does not mean "the service works."** It means "the process answers HTTP." A liveness pass is a *low* bar by design — that's the point. Don't read more into a green liveness than it claims.
2. **Readiness failing is *normal*, not an error.** During startup and shutdown, returning `503` from readiness is the *correct* behavior. Don't alert on it the way you'd alert on a `500`.
3. **A counter that resets to 0 looks like a problem but is usually a restart.** Prometheus counters reset when the process restarts; monitoring systems handle this, but seeing `http_requests_total` drop to 0 means "this instance just restarted," not "we lost data."
4. **The status code matters more than the body.** A probe reading your endpoint cares about `200` vs `503`. A pretty JSON body with `"status": "ok"` and an HTTP `500` will be read as **unhealthy** — the machine never reads your JSON.
5. **`/debug/vars` (expvar) is registered just by *importing* the package** in Go (a blank import). It's easy to expose it accidentally on your public port. Know what your imports register.
6. **"Ready" and "live" can disagree, and that's healthy.** A draining pod is *live* (don't restart it) but *not ready* (don't send it traffic). The two endpoints existing separately is what lets you express that.

---

## Apply it

1. Choose one small, known input for **Diagnostic Endpoints**.
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

- What problem does Diagnostic Endpoints solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
