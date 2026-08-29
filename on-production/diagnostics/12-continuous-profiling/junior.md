# Continuous Profiling — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Continuous Profiling** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Continuous Profiling Roadmap](README.md)
> **Focus:** What continuous profiling is, and why "always-on in production" beats "once on my laptop." The profile types (CPU, heap, off-CPU, goroutine, mutex). How to read a flame graph correctly. Running `go tool pprof` on a real service. How sampling profilers stay cheap.

---

## Core Concepts

### 1. A profile is statistical, not exact

The profiler does not measure your program. It *samples* it — hundreds of times a second it freezes the process, writes down the call stack, and unfreezes it. After enough samples, the proportions converge on the truth: a function in 30% of samples used ~30% of the resource. This means profiles have **noise** — a function that runs once for 2 ms might not appear at all if no sample landed on it. The fix is more samples (longer collection) or a higher sample rate, not a different tool. Internalising "this is a statistical estimate" stops you from over-trusting a single thin box.

### 2. On-CPU and off-CPU are different questions

A **CPU profile** shows where the program was *running*. But a request can be slow while the CPU is nearly idle — it's *waiting* on a database, a lock, a network call, a channel. A CPU profile is blind to waiting; it will look empty or healthy. To debug that, you need an **off-CPU / wall-clock profile**, which captures where the program was *blocked*. The junior reflex "it's slow, show me the CPU profile" is right half the time. The other half, the CPU profile is flat and the answer is in the off-CPU profile.

### 3. Continuous beats occasional because the bug lives in production

The reason to run the profiler always-on is that **the slow path is the one your tests never hit**. Production has the real data distribution, the real concurrency, the real cache state, the real noisy neighbours. A laptop profile of synthetic input profiles a different program. Continuous profiling means when the incident happens, the evidence already exists — you query history instead of trying (and usually failing) to reproduce.

### 4. The flame graph's width is samples, not time

This is the rule everyone gets wrong first. In a flame graph, the **x-axis is not time and the left-to-right order means nothing.** Width encodes *how many samples a frame appeared in* — i.e. how much of the resource it used. Frames are sorted alphabetically, not chronologically. You read a flame graph by finding the **widest towers**, especially the wide boxes at the *top* (the leaf functions actually consuming the resource). A wide box low down just means "a lot happened underneath me."

### 5. Sampling is what makes it cheap enough to leave on

Because the profiler only acts a few hundred times a second — not on every instruction — its cost is roughly proportional to the sample rate, not to how much work your program does. That's why it lands around 1–2% overhead and why "profile everything, always, in production" is a sane default rather than a luxury. An *instrumenting* profiler that timestamped every function call would be 10–100× slower and could never run in prod.

---

## Profiling vs the Other Three Signals

Continuous profiling is the **fourth signal of observability.** It doesn't replace the other three; it answers a question they can't.

| | **Metric** | **Trace** | **Log** | **Profile** |
|---|---|---|---|---|
| **Answers** | "Is something slow?" | "Which span was slow?" | "What happened to this request?" | "Which *line of code* burned the resource?" |
| **Granularity** | Aggregate number | One request's path | One event | Function/line, aggregated over a window |
| **Typical use** | Alert fires: latency up | Find the slow service | Read the error message | Find the hot function inside that service |
| **Cost model** | Constant | Sampled (~1%) | Scales with volume | Sampled (~1–2% CPU) |

The chain in practice: a **metric** alerts you that p99 latency rose. A **trace** shows the time is spent inside `checkout-service`. The **profile** for that service, at that timestamp, shows the time is in `json.Marshal` called from `serializeCart` — the actual line to fix. Metrics and traces tell you *where* to look; the profile tells you *what the code was doing.*

---

## The Profile Types

| Type | Resource it maps | Answers | When you reach for it |
|------|------------------|---------|------------------------|
| **CPU (on-CPU)** | CPU time / cycles | "What's burning the processor?" | High CPU, compute-bound latency |
| **Heap / allocation** | Bytes allocated (or live) | "What's allocating / eating RAM / churning GC?" | High memory, frequent GC, OOMs |
| **Off-CPU / wall-clock** | Time spent *blocked* | "Why is it slow while CPU is idle?" | Latency with low CPU — I/O, locks, waits |
| **Goroutine / thread** | Count & state of goroutines/threads | "Are goroutines leaking? What are they all stuck on?" | Goroutine/thread leak, stuck workers |
| **Mutex / block (lock contention)** | Time waiting on locks | "Which lock is serialising my concurrency?" | Throughput plateau under load, contention |

Two distinctions a junior must keep straight:

- **CPU vs off-CPU.** CPU = running. Off-CPU = waiting. A latency problem can live in either. Check CPU first; if it's flat, the answer is off-CPU.
- **Allocated vs in-use heap.** The heap profile has two flavours: *alloc* (everything ever allocated — good for finding GC pressure) and *inuse* (what's live right now — good for finding leaks). Pick the right one or you'll chase the wrong bytes.

---

## How a Sampling Profiler Works

A CPU sampling profiler works like this:

1. A timer (or a hardware **perf event** like "every N CPU cycles") fires, say, 100 times per second.
2. On each tick, the profiler **interrupts** the running thread and **walks its call stack** — reading the chain of return addresses to reconstruct `main → handler → query → scan`.
3. It records that stack as one **sample** and lets the program continue.
4. After collection ends, all the samples are **aggregated**: identical stacks are counted together, so `... → scan` appearing in 3,000 of 10,000 samples means `scan` (and its callers) used ~30% of the CPU.
5. Raw addresses are **symbolized** into function names using the binary's debug info.

Because it only acts on the timer tick — not on every function call — the cost is bounded by the sample rate, giving the ~1–2% overhead that makes always-on viable. This is **statistical sampling**, and its accuracy improves with more samples. Contrast with an **instrumenting profiler**, which inserts a timer around every function entry and exit: exact call counts, but it can slow the program by an order of magnitude — fine for a microbenchmark, impossible in production.

An **off-CPU** profiler works inversely: instead of sampling who's *on* the CPU, it records stacks at the moments a thread goes to *sleep* (blocks on a syscall, lock, or channel) and how long it stayed asleep — mapping where the program *waited*.

---

## Reading a Flame Graph

This is the one skill to actually master. A flame graph (Brendan Gregg's invention) renders a profile as stacked boxes:

```text
   ┌──────────────────────────────────────────────────────────┐
   │                          main                            │  ← root, full width
   ├───────────────────────────┬──────────────────────────────┤
   │        handleRequest       │        backgroundJob         │
   ├──────────────┬─────────────┼───────────────┬──────────────┤
   │  parseJSON   │  queryDB     │  compress     │   sleep      │
   ├──────────────┤             ┌┴────────┐      │              │
   │ json.Unmarshal│            │ scanRows │      │             │  ← widest LEAF = the hot line
   └──────────────┘             └─────────┘      └──────────────┘
        ▲                            ▲
   23% of samples              41% of samples  ←  optimise THIS first
```

The rules:

1. **Each box is a function.** A box sits on top of the function that called it. The stack grows upward (flame) or downward (icicle — same data, flipped).
2. **Width = number of samples containing that frame = share of the resource.** A box twice as wide used twice the CPU/bytes/time.
3. **The x-axis is NOT time.** Left-to-right order is *not* execution order — frames are sorted alphabetically. Do not read a flame graph like a timeline. (If you want a timeline, you want a *trace*, not a profile.)
4. **Look at the top.** The topmost boxes are the *leaf* functions — the code actually on the CPU when sampled. A wide box at the bottom (`main`) is meaningless; a wide box at the *top* (`json.Unmarshal`, `scanRows`) is your target.
5. **Find the widest tower, optimise from the top down.** In the sketch, `scanRows` at 41% is the single biggest win.

**Flame vs icicle:** a *flame* graph grows up from the root (`main` at the bottom); an *icicle* graph hangs down from the root (`main` at the top). Identical information, just orientation. Pyroscope defaults to icicle; classic Brendan-Gregg SVGs are flame. Don't let the flip confuse you.

---

## Your First Profile — Code Examples

### Go — the gold standard, built into the language

Go's profiler is built in and is the reference implementation everyone else imitates. Add one import and you get live CPU/heap/goroutine/mutex/block profiles over HTTP:

```go
package main

import (
    "net/http"
    _ "net/http/pprof" // registers /debug/pprof/* handlers as a side effect
)

func main() {
    go func() {
        // expose profiling endpoints on a side port
        http.ListenAndServe("localhost:6060", nil)
    }()

    // ... your real server ...
    select {}
}
```

Now, while the program runs, collect a 30-second CPU profile and open the interactive flame graph in a browser:

```bash
# Collect 30s of CPU profile and open the web UI (flame graph + top + source)
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/profile?seconds=30

# Heap (memory) profile
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/heap

# Goroutine profile — great for finding leaks/stuck goroutines
go tool pprof -http=:8080 http://localhost:6060/debug/pprof/goroutine
```

In the text REPL instead of the browser:

```bash
go tool pprof http://localhost:6060/debug/pprof/profile?seconds=30
(pprof) top         # top functions by self CPU
(pprof) top -cum    # top by cumulative (function + callees)
(pprof) list scanRows   # annotated source, line-by-line cost
(pprof) web         # render an SVG call graph
```

> ⚠️ **Don't expose `net/http/pprof` on a public port.** Those endpoints leak internals and let anyone trigger a profile (a small DoS). Bind it to localhost or an internal admin port behind auth.

### Python — py-spy, no code changes, profile a running process

`py-spy` attaches to an *already-running* Python process by PID — no `import`, no restart:

```bash
pip install py-spy

# Live top-like view of where CPU goes
py-spy top --pid 12345

# Record 30s and write an interactive flame graph SVG
py-spy record --pid 12345 --duration 30 --output profile.svg
```

### JVM — async-profiler, the production standard

```bash
# Attach to a running JVM by PID, profile CPU for 30s, emit a flame graph HTML
./asprof -d 30 -e cpu -f flame.html <pid>

# Allocation profiling instead of CPU
./asprof -d 30 -e alloc -f alloc.html <pid>
```

Java also ships **JFR (Java Flight Recorder)**, a built-in low-overhead recorder you can run continuously (covered in [`middle.md`](middle.md)).

### Node.js — built-in and tooling

```bash
# Built-in V8 profiler; produces isolate-*.log, then process it
node --prof app.js
node --prof-process isolate-*.log > processed.txt

# Friendlier: 0x produces an interactive flame graph in one command
npx 0x app.js
```

The whole point of `py-spy` and async-profiler attaching by PID is that you can profile production *without redeploying* — the seed of continuous profiling.

---

## What Profiling Costs

| Profiler kind | Typical overhead | Safe in prod? |
|---------------|------------------|---------------|
| CPU sampling (~100 Hz) | ~1–2% CPU | ✅ Yes — leave it on |
| Heap sampling (Go default) | Negligible (samples every ~512 KB allocated) | ✅ Yes |
| Off-CPU / wall-clock | Low–moderate (depends on block-event rate) | ✅ Usually |
| Mutex/block profiling | Low, but set a *rate* (Go: `SetMutexProfileFraction`) | ✅ With a sane fraction |
| **Instrumenting** profiler | 10–100× slowdown possible | ❌ Microbenchmarks only |

The lesson: **sampling profilers are cheap because they're statistical.** Their cost scales with the sample *rate*, not your workload, which is exactly why "always on" is affordable.

---

## Coding Patterns

```go
// PATTERN: gate profiling endpoints behind an internal-only mux, never the public one.
func startAdminServer() {
    mux := http.NewServeMux()
    mux.HandleFunc("/debug/pprof/", pprof.Index)
    mux.HandleFunc("/debug/pprof/profile", pprof.Profile)
    http.ListenAndServe("127.0.0.1:6060", mux) // localhost only
}
```

```go
// PATTERN: enable mutex/block profiling with a sampling fraction (off by default in Go).
import "runtime"

func init() {
    runtime.SetMutexProfileFraction(5) // sample ~1/5 of contention events
    runtime.SetBlockProfileRate(10000) // sample blocking ~1 per 10µs blocked
}
```

```python
# PATTERN: profile a running prod process without redeploying — py-spy by PID.
# py-spy dump --pid <pid>   # one-shot: what is every thread doing right now?
```

---

## Best Practices

- **Profile before you optimise. Always.** The number-one rule. Optimise the widest box, not the one you suspect.
- **Match the profile type to the symptom.** Hot CPU → CPU profile. Slow but idle → off-CPU. Growing RAM → `inuse` heap. Leaking goroutines → goroutine profile.
- **Collect long enough.** A 1-second CPU profile is noise. 30 seconds is a reasonable default; longer for rare paths.
- **Read flame graphs top-down, widest-first.** The leaf is the line to fix.
- **Keep pprof endpoints internal.** Localhost or an authenticated admin port — never public.
- **Use the language's built-in path when it exists.** Go's `net/http/pprof` and the JVM's JFR are low-overhead and trusted.

---

## Edge Cases & Pitfalls

- **A flat CPU profile doesn't mean "fast."** It means the program wasn't burning CPU — it might have been *waiting*. Switch to off-CPU.
- **Inlining hides functions.** The compiler may inline a small function into its caller, so it never appears as its own frame. Don't conclude "that function isn't called."
- **Stripped binaries can't be symbolized.** Without debug info you get hex addresses, not names. Keep symbols (or upload them) for production binaries.
- **A short-lived process gives a thin profile.** If the process exits in 2 seconds you collected almost no samples. Profile something that runs long enough.
- **Heap `alloc` vs `inuse` answer different questions.** Chasing a leak with `alloc` (which includes freed memory) wastes hours. Use `inuse` for leaks.

---

## Common Mistakes

| Mistake | Why it's wrong | Fix |
|---|---|---|
| Reading the flame graph left-to-right as a timeline | The x-axis is samples, not time | Read widest-first, top-down; use a *trace* for timelines |
| Optimising the leftmost box | Position is alphabetical, not importance | Optimise the *widest* leaf |
| Using a CPU profile for a waiting-bound slowness | CPU profile is blind to blocking | Use off-CPU / wall-clock |
| Exposing `/debug/pprof` publicly | Leaks internals, enables DoS | Bind to localhost / admin port |
| Trusting a 2-second profile | Too few samples; statistical noise | Collect 30s+ |
| Profiling on the laptop to debug a prod-only bug | Different data, concurrency, cache | Profile in production (continuously) |

---

## Tricky Points

- **"Self" vs "total."** A function with huge *total* but tiny *self* isn't the problem — its callees are. Optimise the function with high *self* time (the one doing the work itself).
- **The profiler can lie about rare events.** A function that ran for 5 ms once may not appear if no sample landed on it. Absence in a profile is weak evidence; presence is strong.
- **Allocations and CPU are different graphs.** A line can be cheap on CPU but allocate heavily (driving GC). Check both heap and CPU before concluding.
- **Continuous ≠ a different tool.** It's the *same* sampling profiler, run permanently and stored time-indexed. The novelty is the pipeline, not the profiler.

---

## Apply it

1. Choose one small, known input for **Continuous Profiling**.
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

- What problem does Continuous Profiling solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
