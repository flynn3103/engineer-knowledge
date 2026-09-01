# Diagnostic Endpoints — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Diagnostic Endpoints** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Focus:** Implement health and readiness *correctly* — dependency checks that don't lie and don't cascade. Drive `net/http/pprof` and Spring Actuator like power tools. Toggle log levels at runtime. Wire Kubernetes liveness/readiness/startup probes so they help instead of hurt.

> **Topic:** [Diagnostic Endpoints Roadmap](README.md)

---

## Core Concepts

### 1. The Right Dependency in the Right Check

There is a decision matrix you must internalize:

| Dependency | Liveness? | Readiness? | Why |
|---|---|---|---|
| The process itself responding | ✅ | ✅ | The whole point. |
| A *required* DB you can't serve any request without | ❌ | ⚠️ cautiously | A DB blip should skip you, not restart you — and even skipping the whole fleet is dangerous. |
| An *optional* cache (you degrade without it) | ❌ | ❌ | Degrade gracefully; don't fail health for it. |
| A downstream service you call | ❌ | ❌ usually | Its health is *its* problem; failing yours cascades the outage upward. |
| In-flight startup (caches warming) | ❌ | ✅ | Readiness is exactly "have I finished booting?" |

The default answer for *every* external dependency in *liveness* is **no**. The default for readiness is "only if you literally cannot serve a single request without it, and even then think twice."

### 2. Deep Checks Cascade; Shallow Checks Don't

A "deep" readiness check that pings every dependency feels thorough. But consider the topology: service A's readiness checks service B; B's checks C; C has a 5-second blip. Now A and B both report unready, the LB drops them, traffic concentrates on fewer instances, they overload, *their* readiness fails too — a **cascading failure** triggered by one downstream hiccup. (Senior territory; introduced here so you stop reaching for deep checks reflexively.) Prefer checking *your* ability to function, not *their* health.

### 3. Profiling Endpoints Are Always-On, On-Demand

`/debug/pprof/*` costs nothing until you hit it. A CPU profile is captured *only* while you're requesting `?seconds=30`; a heap profile is computed *only* on GET. So you mount them permanently (on the admin port) and pay only when diagnosing. This is the model: the surface is ready; the cost is deferred to the moment of need.

### 4. Toggle, Don't Redeploy

The mid-level reflex during an incident is *"I wish I had DEBUG logs for this code path."* Redeploying with a higher log level takes minutes you don't have and changes the system you're debugging. A **runtime log-level toggle** flips one logger to DEBUG for ten minutes, then back — no redeploy, no restart, surgical. Spring gives it for free (`/actuator/loggers`); in Go/Python/Node you wire a tiny `/admin/loglevel` handler over an atomic level.

### 5. Probes Have Parameters, and the Defaults Bite

A Kubernetes probe isn't just a URL — it's `initialDelaySeconds`, `periodSeconds`, `timeoutSeconds`, `failureThreshold`, `successThreshold`. Most production incidents involving probes come from *wrong parameters*, not wrong endpoints: a liveness `timeout` shorter than a GC pause, an `initialDelay` shorter than boot time, a `failureThreshold` of 1 that restarts on a single blip. Knowing the endpoint is half the job; tuning the probe is the other half.

---

## Implementing Health & Readiness Correctly

### The shape of a correct readiness check

A good readiness check is: *started up* AND *required dependencies are usable* — where "usable" is checked **cheaply, with a timeout, and ideally from cached state**, not by hammering the dependency on every probe.

```go
type Readiness struct {
	started  atomic.Bool
	dbOK     atomic.Bool // updated by a background poller, NOT on every probe
}

// Background goroutine pings the DB every few seconds and caches the result,
// so the probe handler reads an atomic instead of doing I/O on the hot path.
func (rd *Readiness) pollDB(db *sql.DB) {
	for range time.Tick(5 * time.Second) {
		ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
		rd.dbOK.Store(db.PingContext(ctx) == nil)
		cancel()
	}
}

func (rd *Readiness) handler(w http.ResponseWriter, r *http.Request) {
	if !rd.started.Load() {
		http.Error(w, "starting", http.StatusServiceUnavailable)
		return
	}
	if !rd.dbOK.Load() {
		http.Error(w, "db unavailable", http.StatusServiceUnavailable)
		return
	}
	w.Write([]byte("ready"))
}
```

Why this shape:

- **No I/O in the probe handler.** The probe reads an atomic; the actual DB ping happens on a background timer with its *own* timeout. A slow DB can't make your probe slow.
- **The check is bounded.** The background ping has a 2s timeout, so it can't hang.
- **It degrades, it doesn't crash.** A `503` from readiness deregisters you; it never restarts you.

### Liveness: keep it dumb on purpose

```go
func liveness(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("ok")) // that's it. that's the check.
}
```

A liveness check that does anything more is a liability. The one *legitimate* enrichment is detecting a **wedged event loop / deadlocked runtime** — e.g., a watchdog goroutine that updates a "last tick" timestamp and liveness fails if it's stale. But that detects *your own* wedge, never a dependency's.

### Graceful drain: the often-missed half

Readiness isn't only for startup. On `SIGTERM`, flip readiness to `false` *first*, wait for the LB to notice and stop routing, then finish in-flight requests and exit:

```go
func onShutdown(rd *Readiness, srv *http.Server) {
	rd.started.Store(false)         // /readyz now returns 503 → LB drains us
	time.Sleep(5 * time.Second)     // let the LB's next probe cycle deregister us
	srv.Shutdown(context.Background()) // finish in-flight, then stop
}
```

Skip this and the LB keeps sending requests to a process that's already closing connections — instant errors on every deploy.

---

## Profiling Endpoints — pprof in Anger

In Go, a single blank import wires the entire profiling surface onto a mux:

```go
import _ "net/http/pprof" // registers /debug/pprof/* on http.DefaultServeMux
```

The endpoints, and what each answers:

| Endpoint | Question it answers | How to pull it |
|---|---|---|
| `/debug/pprof/profile?seconds=30` | "What's using CPU?" | `go tool pprof http://host:9090/debug/pprof/profile?seconds=30` |
| `/debug/pprof/heap` | "What's holding memory?" | `go tool pprof http://host:9090/debug/pprof/heap` |
| `/debug/pprof/goroutine?debug=2` | "What is everything stuck on?" | `curl ...goroutine?debug=2 > gs.txt` |
| `/debug/pprof/mutex` | "Where is lock contention?" | requires `runtime.SetMutexProfileFraction(n)` |
| `/debug/pprof/block` | "Where do goroutines block?" | requires `runtime.SetBlockProfileRate(n)` |
| `/debug/pprof/allocs` | "What allocates the most (cumulative)?" | `go tool pprof ...allocs` |
| `/debug/pprof/trace?seconds=5` | "Full execution trace" | `go tool pprof` / `go tool trace` |

The interactive workflow you'll use most:

```bash
# Pull a 30s CPU profile from a live (admin-port) service and explore it.
go tool pprof -http=:0 'http://localhost:9090/debug/pprof/profile?seconds=30'
# In the browser: Flame Graph view. Widest frame = hottest. Done.

# Or text-mode:
go tool pprof 'http://localhost:9090/debug/pprof/heap'
(pprof) top          # biggest retainers
(pprof) list LRU.Set # annotated source of a suspect function
(pprof) web          # SVG call graph
```

> **Mid-level discipline:** mount pprof on the **admin port**, never the public one. A CPU profile request makes the runtime do work; an attacker who can hit `/debug/pprof/profile` repeatedly has a cheap DoS *and* a memory-disclosure vector. (Why, in [`senior.md`](senior.md).)

**Python** has no built-in equivalent, but `py-spy` attaches to a running PID with no code changes — the on-demand spirit, externalized:

```bash
sudo py-spy dump   --pid $PID            # all thread stacks (≈ goroutine dump)
sudo py-spy top    --pid $PID            # live "top" of Python functions
sudo py-spy record --pid $PID -o flame.svg --duration 30
```

**Node** exposes the V8 inspector for profiling: start with `--inspect` (bound to localhost!), connect Chrome DevTools, use the Profiler tab — or use `clinic flame` / `0x` for flame graphs without a UI.

**Rust** (axum/tower) has no built-in surface; `pprof-rs` gives you a CPU profiler you mount behind a handler that returns a pprof- or flamegraph-format body on demand.

---

## Spring Boot Actuator — The Full Surface

The JVM's batteries-included answer. With `spring-boot-starter-actuator` on the classpath, you opt endpoints in and get a rich diagnostic surface:

```properties
# Expose only what you want, on a SEPARATE port.
management.server.port=9090
management.endpoints.web.exposure.include=health,info,metrics,prometheus,threaddump,heapdump,loggers,env

# Real liveness/readiness groups, mapped to k8s probes:
management.endpoint.health.probes.enabled=true
management.health.livenessstate.enabled=true
management.health.readinessstate.enabled=true

# Show health detail only to authenticated callers (default is "never"):
management.endpoint.health.show-details=when-authorized
```

What you get:

| Endpoint | Use |
|---|---|
| `/actuator/health/liveness` | k8s liveness probe target. |
| `/actuator/health/readiness` | k8s readiness probe target. |
| `/actuator/threaddump` | JSON thread dump — "what's stuck?" Replaces SSHing in for `jstack`. |
| `/actuator/heapdump` | Downloads a `.hprof` — open in Eclipse MAT for leak analysis. **Heavy & sensitive.** |
| `/actuator/loggers/{name}` | GET the level; POST to *change it at runtime*. |
| `/actuator/prometheus` | `/metrics` in Prometheus format (via Micrometer). |
| `/actuator/info` | Build/version info (wire git-commit-id plugin for SHA). |
| `/actuator/env` | Current config (with sensitive keys masked). |

A Spring app can also signal readiness/liveness programmatically:

```java
@Component
public class WarmUp {
    private final ApplicationAvailability availability;
    private final ApplicationEventPublisher publisher;
    // ...
    void onCacheLoaded() {
        // Tell Actuator we're ready to receive traffic.
        AvailabilityChangeEvent.publish(publisher, this, ReadinessState.ACCEPTING_TRAFFIC);
    }
    void onFatalCorruption() {
        // Tell Actuator we're broken — liveness flips, k8s restarts us.
        AvailabilityChangeEvent.publish(publisher, this, LivenessState.BROKEN);
    }
}
```

This is the JVM's superpower: liveness/readiness/threaddump/heapdump/log-toggle, standardized, with almost no code. The *risk* is exposing too much (`/actuator/env` leaks config, `/actuator/heapdump` leaks memory) — covered in [`senior.md`](senior.md).

---

## expvar and Runtime Variables

Go's `expvar` is the minimal, zero-dependency `/metrics`. Importing it registers `/debug/vars`, which serves a JSON object of published variables plus `memstats` and `cmdline`:

```go
import "expvar"

var (
	ordersTotal = expvar.NewInt("orders_total")
	cacheStats  = expvar.NewMap("cache").Init()
)

func init() {
	// You can publish computed values via a function, evaluated on each scrape.
	expvar.Publish("goroutines", expvar.Func(func() any {
		return runtime.NumGoroutine()
	}))
}

// usage: ordersTotal.Add(1) ; cacheStats.Add("hits", 1)
```

```bash
curl localhost:9090/debug/vars
# {"orders_total": 1287, "cache": {"hits": 9001, "misses": 42},
#  "goroutines": 138, "memstats": { ... }, "cmdline": [...] }
```

When to use `expvar` vs Prometheus: `expvar` is great for quick, dependency-free introspection and ad-hoc counters; Prometheus client is what you wire to dashboards and alerting. Many services run both — `expvar` for a fast human `curl`, `/metrics` for the monitoring system. Note: `/debug/vars` is registered on `DefaultServeMux`, so a naïve setup can leak it onto your public port. Mount it deliberately.

---

## Runtime Log-Level Toggles

The single highest-value "control" endpoint after health. The pattern: an **atomic level variable** that your logger reads, plus a tiny handler to set it.

### Go (`slog` with a `LevelVar`)

```go
var logLevel = new(slog.LevelVar) // safe for concurrent use; default INFO

func init() {
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout,
		&slog.HandlerOptions{Level: logLevel})))
}

// POST /admin/loglevel  body: {"level":"DEBUG"}
func setLogLevel(w http.ResponseWriter, r *http.Request) {
	var body struct{ Level string }
	json.NewDecoder(r.Body).Decode(&body)
	switch strings.ToUpper(body.Level) {
	case "DEBUG":
		logLevel.Set(slog.LevelDebug)
	case "INFO":
		logLevel.Set(slog.LevelInfo)
	case "WARN":
		logLevel.Set(slog.LevelWarn)
	default:
		http.Error(w, "bad level", http.StatusBadRequest)
		return
	}
	w.Write([]byte("ok"))
}
```

`logLevel.Set(slog.LevelDebug)` takes effect immediately, process-wide, no restart. Pair it with a self-revert (a timer that resets to INFO after 15 minutes) so a forgotten DEBUG toggle doesn't flood your log pipeline forever.

### Java (Actuator gives it free)

```bash
# Read the level:
curl localhost:9090/actuator/loggers/com.example.orders
# Set it at runtime:
curl -X POST localhost:9090/actuator/loggers/com.example.orders \
  -H 'Content-Type: application/json' -d '{"configuredLevel":"DEBUG"}'
# Reset:
curl -X POST localhost:9090/actuator/loggers/com.example.orders \
  -H 'Content-Type: application/json' -d '{"configuredLevel":null}'
```

### Python / Node

Python: a handler that calls `logging.getLogger(name).setLevel(...)`. Node: many loggers (`pino`, `winston`) expose `logger.level = "debug"` at runtime; wrap it in an admin route. Same shape everywhere: one atomic-ish level, one guarded endpoint.

---

## On-Demand Dumps — Thread, Goroutine, Heap

When a process is *stuck* (not crashed), a dump is the tool. Each ecosystem:

| Ecosystem | "What's stuck?" (stacks) | "What's leaking?" (memory) |
|---|---|---|
| **Go** | `curl .../debug/pprof/goroutine?debug=2` | `go tool pprof .../debug/pprof/heap` |
| **Java** | `curl .../actuator/threaddump` (or `jstack <pid>`) | `curl .../actuator/heapdump > h.hprof` → MAT |
| **Python** | `py-spy dump --pid <pid>` | `tracemalloc` snapshots / `py-spy --memory` |
| **Node** | `kill -USR1` (inspector) or `process.report` | `require('v8').writeHeapSnapshot()` → DevTools |
| **Rust** | `pprof-rs` handler / `tokio-console` for async tasks | heap via external (`jemalloc` profiling, `bytehound`) |

The goroutine/thread dump is the fastest path from "the service is hung" to "here's the line every worker is blocked on." Group the dump by stack signature: if 10,000 goroutines share one stack parked on `chan receive`, you've found a leak whose producer died. (Deep treatment in [`../01-debugging/senior.md`](../01-debugging/senior.md).)

> **Caution, foreshadowing `professional.md`:** a heap dump on a 16 GB heap writes a 16 GB file and can pause/OOM the process. `/actuator/heapdump` on a memory-pressured pod can *be* the thing that kills it. On-demand dumps are powerful and not free.

---

## Wiring Kubernetes Probes

The endpoints are useless until the orchestrator calls them with sane parameters. The three probe types map to the three questions:

```yaml
# deployment.yaml (container spec)
ports:
  - name: http
    containerPort: 8080      # public app traffic
  - name: admin
    containerPort: 9090      # diagnostics — NOT exposed via a public Service

# STARTUP: gate everything until the app booted. Protects slow starters.
startupProbe:
  httpGet:   { path: /healthz, port: 8080 }
  periodSeconds: 5
  failureThreshold: 30       # 30 × 5s = up to 150s to boot before giving up

# LIVENESS: restart if wedged. Cheap endpoint, generous timeout (survive GC pauses).
livenessProbe:
  httpGet:   { path: /healthz, port: 8080 }
  periodSeconds: 10
  timeoutSeconds: 3          # MUST exceed your worst-case GC/STW pause
  failureThreshold: 3        # 3 misses (~30s) before restart — not 1

# READINESS: deregister if not ready. Can be slightly "deeper".
readinessProbe:
  httpGet:   { path: /readyz, port: 8080 }
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 3
```

The rules that prevent self-inflicted outages:

1. **Startup probe exists for slow boots.** Without it, liveness fires during boot and you crash-loop forever. The startup probe *suspends* liveness/readiness until it first succeeds.
2. **Liveness `timeout` > worst-case pause.** If a 2-second GC stop-the-world exceeds a 1-second liveness timeout, healthy pods get restarted mid-GC. Size the timeout above your p99 pause.
3. **`failureThreshold` ≥ 3 for liveness.** Restarting on a single blip is how one slow probe becomes a restart storm.
4. **Liveness and readiness usually share the cheap endpoint or use distinct ones — never the same *logic* that includes dependencies in liveness.**
5. **Probes hit the app port or the admin port — pick deliberately.** Many teams probe the app port for simplicity; just ensure the path is dependency-correct.

(The *why these rules exist* — probe storms, cascading restarts — is the heart of [`senior.md`](senior.md).)

---

## Code Examples

### Go — a complete admin server on a separate port

```go
func startAdminServer(rd *Readiness, addr string) {
	mux := http.NewServeMux()                 // a PRIVATE mux, not DefaultServeMux
	mux.HandleFunc("/healthz", liveness)
	mux.HandleFunc("/readyz", rd.handler)
	mux.HandleFunc("/version", versionHandler)
	mux.HandleFunc("/admin/loglevel", setLogLevel)
	mux.Handle("/metrics", promhttp.Handler())

	// Mount pprof explicitly on THIS mux so it isn't on the public one.
	mux.HandleFunc("/debug/pprof/", pprof.Index)
	mux.HandleFunc("/debug/pprof/profile", pprof.Profile)
	mux.HandleFunc("/debug/pprof/heap", pprof.Handler("heap").ServeHTTP)
	mux.HandleFunc("/debug/pprof/goroutine", pprof.Handler("goroutine").ServeHTTP)

	// expvar on the admin mux too:
	mux.Handle("/debug/vars", expvar.Handler())

	log.Printf("admin server on %s (private)", addr)
	log.Fatal(http.ListenAndServe(addr, mux)) // e.g. "127.0.0.1:9090"
}

// public app server uses a DIFFERENT mux with only business routes.
```

The key move: a **private mux** so `pprof` and `expvar` don't ride along on `DefaultServeMux` to your public port.

### Python — FastAPI with a cached dependency check

```python
import asyncio, time
from fastapi import FastAPI, Response

app = FastAPI()
_state = {"started": False, "db_ok": False, "db_checked": 0.0}

async def poll_db():
    while True:
        try:
            await asyncio.wait_for(db.ping(), timeout=2.0)
            _state["db_ok"] = True
        except Exception:
            _state["db_ok"] = False
        _state["db_checked"] = time.time()
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup():
    asyncio.create_task(poll_db())
    await warm_caches()
    _state["started"] = True

@app.get("/healthz")                          # liveness — trivial
async def healthz():
    return Response("ok", 200)

@app.get("/readyz")                           # readiness — reads cached state
async def readyz():
    if not _state["started"]:
        return Response("starting", 503)
    if not _state["db_ok"]:
        return Response("db down", 503)
    return Response("ready", 200)
```

### Node — runtime log toggle with pino + drain

```js
const pino = require("pino");
const logger = pino({ level: process.env.LOG_LEVEL || "info" });

// POST /admin/loglevel  { "level": "debug" }
adminApp.post("/admin/loglevel", express.json(), (req, res) => {
  const valid = ["trace", "debug", "info", "warn", "error"];
  if (!valid.includes(req.body.level)) return res.status(400).send("bad level");
  logger.level = req.body.level;            // takes effect immediately
  // auto-revert so a forgotten DEBUG doesn't flood forever:
  setTimeout(() => { logger.level = "info"; }, 15 * 60 * 1000);
  res.send("ok");
});

let ready = true;
process.on("SIGTERM", () => {
  ready = false;                            // /readyz now 503 → LB drains
  setTimeout(() => server.close(() => process.exit(0)), 5000);
});
```

---

## Coding Patterns

### Pattern: cached dependency state, polled off the hot path

```go
// Background poller writes; probe reads. Probe never does I/O.
go rd.pollDB(db)
mux.HandleFunc("/readyz", rd.handler)
```

### Pattern: private mux for diagnostics

```go
adminMux := http.NewServeMux()       // pprof/expvar/metrics go here
go http.ListenAndServe("127.0.0.1:9090", adminMux)
```

### Pattern: self-reverting log toggle

```go
logLevel.Set(slog.LevelDebug)
time.AfterFunc(15*time.Minute, func() { logLevel.Set(slog.LevelInfo) })
```

### Pattern: readiness as the drain switch

```go
// shutdown: flip readiness false, wait a probe cycle, then Shutdown().
rd.started.Store(false)
time.Sleep(2 * probePeriod)
srv.Shutdown(ctx)
```

---

## Clean Code

- Liveness handler is a one-liner. Resist enriching it.
- Readiness reads *cached* dependency state; the actual ping lives in a background poller with its own timeout.
- Diagnostics (pprof, expvar, dumps, toggles, metrics) live on a **private mux / separate port**, never `DefaultServeMux` reachable from public.
- Every runtime toggle (log level, debug mode) is **guarded** (auth and/or admin port) and ideally **self-reverting**.
- Suppress access logs for probe paths so they don't bury real logs. (See [`../02-logging/middle.md`](../02-logging/middle.md).)
- Wire real build info into `/version` at compile time (`-ldflags`, git-commit-id plugin), not a hardcoded constant you'll forget to bump.

---

## Best Practices

1. **No I/O in probe handlers.** Poll dependencies on a timer; have probes read cached atomics.
2. **Liveness depends on nothing but the process.** Readiness may *cautiously* include strictly-required dependencies.
3. **Tune the probe, not just the endpoint.** `timeout` > worst-case pause; `failureThreshold` ≥ 3 for liveness; startup probe for slow boots.
4. **Mount pprof/expvar/dumps on the admin port.** Never let them ride `DefaultServeMux` to the public listener.
5. **Ship a runtime log-level toggle** in every service; prefer self-reverting.
6. **Drain on shutdown**: flip readiness false → wait a probe cycle → `Shutdown`.
7. **Treat heap dumps as heavy and sensitive.** Know they can pause/OOM; never trigger casually under memory pressure.
8. **Mask secrets** in any config-exposing endpoint (`/actuator/env`, custom `/admin/config`).

---

## Edge Cases & Pitfalls

- **`net/http/pprof`'s blank import registers on `DefaultServeMux`.** If your public server uses `DefaultServeMux`, you just exposed pprof to the internet. Use an explicit private mux.
- **Liveness timeout shorter than a GC pause** → healthy pods restarted during collection → throughput collapses under load (exactly when GC is busiest).
- **Readiness ping with no timeout** → a hung DB hangs the probe → k8s times out the probe → instance flaps in and out of rotation.
- **Startup probe missing** → liveness kills the pod mid-boot → `CrashLoopBackOff` that looks like an app crash but is a probe misconfig.
- **`/actuator/heapdump` exposed and reachable** → anyone can both DoS you (giant dump) and exfiltrate memory contents (secrets, PII).
- **Log toggle with no auth** → an attacker flips you to DEBUG and floods/expensive-ifies your logging pipeline.
- **`successThreshold` > 1 on liveness** is invalid in k8s (must be 1) — a copy-paste from readiness that silently misbehaves.
- **Probing the *app* port while the app port is saturated** → readiness fails *because* you're busy → you get deregistered → remaining pods overload → cascade.

---

## Common Mistakes

1. **Putting a DB ping directly in the probe handler.** Under load it times out and ejects healthy instances.
2. **One endpoint serving both liveness and readiness with dependency logic in it.** A dependency blip now restarts pods.
3. **Exposing pprof/actuator on the public port** via `DefaultServeMux` or a permissive `exposure.include=*`.
4. **No startup probe for a slow-booting app** → permanent crash-loop on deploy.
5. **Liveness `failureThreshold: 1` with a tight timeout** → restart storm on the first transient blip.
6. **Forgetting to drain.** No readiness-false on `SIGTERM` → errors on every rolling deploy.
7. **Leaving a DEBUG log toggle on** → log pipeline flooded, costs spike, signal drowned.
8. **Triggering a heap dump on a memory-pressured pod** → the dump OOM-kills the very process you were investigating.

---

## Tricky Points

- **A passing readiness check during startup is a *bug*, not a feature** — it means you're routing to a cold instance. Readiness should default closed.
- **pprof endpoints have prerequisites**: `mutex` and `block` profiles return nothing until you call `runtime.SetMutexProfileFraction` / `SetBlockProfileRate`. Empty profile ≠ no contention; it may mean "not enabled."
- **Actuator `health` returns aggregate UP/DOWN by default but hides detail** unless `show-details` is set — and showing detail is itself a disclosure decision.
- **`/debug/vars` evaluates `expvar.Func` values on every request** — an expensive published function turns each scrape into work. Keep them cheap.
- **k8s liveness and readiness use independent counters.** A pod can be `Running` (liveness OK) but `0/1 READY` (readiness failing) indefinitely — that's a draining or warming pod, not a bug.
- **A profile request competes with your app for CPU.** A 30-second CPU profile on a hot service is observable in latency; on a tiny service it's noise. Know which you have.
- **Spring's `LivenessState.BROKEN` actually causes a restart** via the probe — publish it only for genuinely unrecoverable state, or you've built a self-destruct button.

---

## Apply it

1. Find a real component where **Diagnostic Endpoints** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Diagnostic Endpoints?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
