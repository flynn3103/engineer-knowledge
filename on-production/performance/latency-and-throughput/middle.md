# Latency and Throughput — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Latency and Throughput** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Latency and Throughput
> *The junior page defined the words. This page gives you the math that binds them: Little's Law, the queue that explains why a half-idle server still has a slow tail, and the curve that explains why "add 10% more traffic" can turn a healthy service into a smoking one.*

---

## Little's Law — the Identity That Ties It All Together

- Little's Law is the single most useful equation in performance work, and it's almost embarrassingly simple:

```
L = λ × W
```

- **L** = the average number of requests *in the system* at any instant (concurrency in flight).
- **λ** (lambda) = the average arrival rate, i.e. **throughput** (requests per second).
- **W** = the average time a request *spends in the system* (response time / latency).

- It holds for *any* stable system — any queue, any service, any subsystem — regardless of arrival distribution, service-time distribution, or scheduling discipline. The only requirement is that the system is in steady state (what comes in eventually goes out; the queue isn't growing without bound). That generality is what makes it a law and not a model.

- Rearranged, it gives you the form you'll actually use most:

```
concurrency  =  throughput  ×  latency
        L     =      λ       ×    W
```

> **Key insight:** Throughput and latency are not independent dials you can set separately. They are joined at the hip by the concurrency you can sustain. If your latency goes up and your concurrency limit stays fixed, your throughput **must** fall. This is why "the service got slower" and "the service handles less traffic" are usually the *same event* viewed from two sides.

- A concrete read: API handles **λ = 2,000 req/s**, each request takes **W = 50 ms = 0.05 s**.
  - Average concurrency: `L = 2,000 × 0.05 = 100`.
  - You need roughly 100 units of concurrency — threads, goroutines, connection slots — in flight to sustain that rate.
  - Size your thread pool or connection pool below that and you cap throughput *before* the CPU is the bottleneck.

```go
// Little's Law as a sizing check, not an afterthought.
// Target: 2000 req/s, measured mean latency 50ms.
const targetRPS = 2000.0
const meanLatencySec = 0.050

inFlight := targetRPS * meanLatencySec // = 100
// => a worker pool / DB connection pool of ~100 is the floor.
// Provision below this and throughput is capped by queueing, not by CPU.
fmt.Printf("need ~%.0f concurrent slots\n", inFlight)
```

- The law also works as a *diagnostic*. Measure any two terms and the third is forced.
  - Observe 100 in-flight requests and 2,000 req/s → mean latency is *necessarily* 50 ms. If your latency dashboard disagrees, one of your instruments is wrong.
  - Engineers waste days debugging "impossible" numbers that Little's Law would have flagged in thirty seconds.

---

## Service Time vs Wait Time vs Response Time

- Before the curve makes sense, three terms have to stop being synonyms. They are not.

| Term | What it measures | Where it lives |
|---|---|---|
| **Service time** (S) | Time actually *doing the work* once started | CPU, I/O — the useful part |
| **Wait time** (Wq) | Time spent *queued*, waiting for a free server | The queue, doing nothing |
| **Response time** (W) | What the user feels: `W = Wq + S` | The sum of both |

- A request that takes 50 ms might be 5 ms of real work and 45 ms sitting in a queue behind other requests.
- The CPU profile (see [02 — Benchmarking](../benchmarking-and-microbenchmarks/middle.md)) will only ever show you the 5 ms of *service* time — it is blind to the 45 ms of *wait*. This is the single most common reason a profiler says "the code is fast" while users say "the service is slow."

> **Key insight:** Profilers measure **service time**; users experience **response time**. The gap between them is **wait time**, and wait time is invisible to almost every code-level tool. When the profile looks clean but the latency is bad, stop profiling the code and start measuring the queue.

- This is why "optimize the slow function" so often fails to move the dashboard: if 90% of your response time is queueing, halving your service time barely dents `W`. You don't have a code problem; you have a *capacity* problem — the next two sections are about exactly that.

---

## The Latency–Load Curve and the Knee

- Plot response time (y-axis) against load (x-axis, requests per second or utilization) and you get one of the most important shapes in systems engineering:

```
response
 time W │                                        ╱  ← latency explodes
        │                                       ╱
        │                                     ╱
        │                                  ╱    ← the "knee" / hockey stick
        │  ____________________________╱
        │ /  flat: latency ≈ service time
        └─────────────────────────────────────────► load (λ or utilization)
          low                  ~70-80%          ~100%
```

- For most of the range, latency is **flat** — it sits near the bare service time because requests rarely wait.
- Somewhere past 70–80% utilization, the curve bends sharply upward (the **knee**, or **hockey stick**) and latency climbs toward infinity as utilization approaches 100%. It does not climb gently — it *explodes*.

- The brutal practical consequence: the difference between a healthy service and a melting one is often a *tiny* increase in load that happens to push you over the knee.
  - A system at 65% utilization that absorbs a 20% traffic bump moves to ~78% — and its p99 can double or triple while its *median* barely moves.
  - Your median dashboard says "fine." Your users are timing out.
  - This is why capacity planning targets a utilization *well below* 100% — you're not leaving the headroom idle out of waste, you're leaving it so you stay on the flat part of the curve.

> **Key insight:** Latency does not degrade linearly with load. It stays flat, then detonates at the knee. "We have 30% headroom" is a dangerous statement if that 30% is on the far side of the knee — past it, headroom is measured in latency, not in spare capacity.

---

## Queueing Intuition — Why 80% Utilization Already Hurts

- Where does the knee come from? Queueing theory gives the answer in one formula. For a simple single-server queue with random arrivals (an M/M/1 model), the average time a request waits *relative to its service time* is:

```
                    ρ
wait factor  =  ─────────       where ρ (rho) = utilization (0 to 1)
                  1 − ρ
```

- Plug in numbers and the shape jumps out:

| Utilization ρ | Wait ÷ service time |
|---|---|
| 50% | 1.0× (wait equals the work itself) |
| 70% | 2.3× |
| 80% | 4.0× |
| 90% | 9.0× |
| 95% | 19.0× |
| 99% | 99.0× |

- At 50% utilization a request already waits about as long as it takes to serve. At 80%, it waits *four times* the service time. At 99%, it waits a hundred times.
- The denominator `(1 − ρ)` is the villain: as ρ approaches 1, it approaches 0, and the ratio blows up. That `1/(1−ρ)` term **is** the hockey stick.

> **Key insight:** Utilization is not a "how busy" number — it's a *latency amplifier*. The cost of the next percent of utilization is not constant; it's governed by `1/(1−ρ)`, which is cheap at 50% and ruinous at 95%. This is the mathematical reason mature teams run hot paths at 60–70%, not 95%, and treat "high utilization" as a *risk*, not an *efficiency win*.

- Two refinements that matter in real systems:
  1. **Variability makes it worse.** The clean formula assumes random (Poisson) arrivals and exponential service times. Real traffic is *burstier* and real service times are *more variable* (some requests hit cache, some hit disk). More variability shifts the knee *left* — you hit the wall earlier. The Kingman approximation captures this: wait time scales with `(C²a + C²s)/2`, the average of arrival and service-time variability. Cut variability and you buy back headroom for free.
  2. **More servers help super-linearly near the knee.** An M/M/c queue (c parallel servers) flattens the curve dramatically compared to one big server of equivalent total capacity, because a free server can pick up a queued request instead of it waiting behind a busy one. This is the quantitative argument for horizontal scaling and for shared work queues over per-worker queues.

---

## Percentiles Done Right

- Averages lie about latency because latency distributions are heavy-tailed: a few very slow requests pull the mean around while most users see something much faster. So we report **percentiles** — p50 (median), p99, p99.9. But percentiles are easy to compute *wrong*, and wrong percentiles are worse than no percentiles because they look authoritative.

- **How a percentile is actually computed.** Sort all latencies; pX is the value below which X% of samples fall. The naive way — store every sample and sort — is correct but uses unbounded memory at scale. So real systems use **bounded-error data structures**:
  - **HdrHistogram** (High Dynamic Range Histogram): pre-allocated buckets across a configured value range, with *guaranteed* relative error (e.g. ±0.1%). It records billions of values in fixed memory and computes any percentile in O(buckets). This is the gold standard for latency.
  - **Prometheus histograms**: fixed, *manually chosen* buckets (`le="0.005"`, `le="0.01"`, …). Percentiles are *interpolated* between bucket boundaries — so your p99 is only as accurate as your bucket layout. Put no buckets between 100 ms and 1 s and your p99 in that range is a guess.
  - **Prometheus summaries**: compute percentiles *client-side* per instance over a sliding window. Cheap to read, but — critically — **you cannot aggregate them across instances**.

> **Key insight:** **You cannot average percentiles.** The mean of host A's p99 and host B's p99 is *not* the fleet p99 — there is no arithmetic that recovers it from the two numbers, because a percentile is a property of a *distribution*, not a value you can average. To get a real fleet-wide p99 you must merge the underlying *histograms* (add the bucket counts) and recompute. This is the entire reason Prometheus histograms beat summaries for distributed systems: histograms are mergeable; summaries are not.

```go
import "github.com/HdrHistogram/hdrhistogram-go"

// Range 1µs..60s, 3 significant digits of precision.
h := hdrhistogram.New(1, 60_000_000, 3) // values in microseconds

for _, latency := range observed {
    h.RecordValue(latency.Microseconds())
}

fmt.Printf("p50  = %d µs\n", h.ValueAtQuantile(50))
fmt.Printf("p99  = %d µs\n", h.ValueAtQuantile(99))
fmt.Printf("p99.9= %d µs\n", h.ValueAtQuantile(99.9))

// Two hosts? Merge histograms, THEN read the percentile — never average p99s.
fleet := hdrhistogram.New(1, 60_000_000, 3)
fleet.Merge(hostA)
fleet.Merge(hostB)
fmt.Printf("fleet p99 = %d µs\n", fleet.ValueAtQuantile(99))
```

```java
// Java: HdrHistogram (Gil Tene's reference implementation).
Histogram h = new Histogram(60_000_000_000L, 3); // 1ns..60s range, 3 sig digits
for (long nanos : observed) h.recordValue(nanos);
System.out.printf("p99   = %d ns%n", h.getValueAtPercentile(99.0));
System.out.printf("p99.9 = %d ns%n", h.getValueAtPercentile(99.9));
```

- One more trap, named by the same author: **coordinated omission**.
  - If your load generator sends a request, waits for the (slow) response, and only *then* sends the next, it never measures the latency that the *backlogged* requests would have seen — it accidentally stops sending during the slow period.
  - The result wildly understates the tail.
  - `wrk2` exists specifically to fix this: it sends at a *fixed schedule* regardless of when responses arrive, and attributes the full intended-vs-actual delay to each request. Use `wrk2`, not `wrk`, for any latency claim.

---

## Moving the Curve — Batching, Pipelining, Concurrency

- The whole point of understanding the curve is to *move* it. Three levers do most of the work, and each trades latency and throughput differently.

- **Batching** amortizes per-operation fixed cost across many items — one round trip, one syscall, one transaction for N items.
  - Raises throughput, but adds latency to the items that wait for the batch to fill.
  - A 10 ms batch window can 5× your throughput while adding up to 10 ms to each request.
  - Good when throughput is the goal (ingestion, logging, bulk writes); bad on an interactive path.

```go
// Batching: trade a little latency for a lot of throughput.
batch := make([]Item, 0, 100)
ticker := time.NewTicker(10 * time.Millisecond) // max latency added
for {
    select {
    case item := <-in:
        batch = append(batch, item)
        if len(batch) == cap(batch) {
            flush(batch); batch = batch[:0]
        }
    case <-ticker.C:
        if len(batch) > 0 { flush(batch); batch = batch[:0] }
    }
}
```

- **Pipelining** overlaps the stages of independent requests so a stage isn't idle waiting for the previous request to finish all stages.
  - Raises throughput *without* the latency penalty of batching — request latency stays roughly constant while throughput rises toward the slowest stage's rate.
  - HTTP/2 multiplexing and Redis pipelining are the canonical examples.

- **Concurrency** is the Little's Law lever: raise `L` (more workers/connections) and you raise the throughput `λ` you can sustain at a given latency `W`.
  - Only up to the point where a *shared resource* saturates — then adding concurrency just lengthens the queue and `W` climbs (see [06 — Concurrency and Contention](../concurrency-and-contention/middle.md)).
  - There's an optimal concurrency: at it, throughput peaks; past it, throughput is flat or falling while latency keeps rising. Finding that point empirically (a load sweep) beats guessing.

> **Key insight:** Batching trades latency *for* throughput. Pipelining and concurrency try to buy throughput *without* paying latency — until a shared resource saturates, after which more concurrency buys only longer queues. Know which lever you're pulling and what it costs on the *other* axis.

---

## Worked Example — A Capacity Calculation with Little's Law

- You're sizing a payment service. Requirements and measurements:
  - Target throughput: **λ = 5,000 req/s** at peak.
  - Measured mean response time at low load: **W = 40 ms = 0.04 s** (service time ≈ 30 ms, network ≈ 10 ms).
  - Each request holds one database connection for its full duration.
  - Your DB connection pool is currently **80** connections.

- **Step 1 — How much concurrency does the target demand?**

```
L = λ × W = 5,000 × 0.04 = 200 in-flight requests
```

  - You need ~200 requests in flight on average. With each holding a connection, you need ~200 connections — but you have 80.

- **Step 2 — What happens with only 80 connections?** The pool caps concurrency at `L = 80`. Rearranging Little's Law, the *maximum* throughput the pool can sustain at 40 ms latency is:

```
λ_max = L / W = 80 / 0.04 = 2,000 req/s
```

  - The pool throttles you to 2,000 req/s — **40% of target** — purely from connection starvation, long before the database CPU is stressed.
  - The remaining 3,000 req/s queue *waiting for a connection*, so their response time balloons (wait time, not service time). Your DB looks healthy; your service is dying.

- **Step 3 — Right-size, with headroom.** To hit 5,000 req/s at 40 ms you need `L = 200`. But you don't size for the *average* — bursts and variance push instantaneous concurrency higher, and you want to stay on the flat part of the curve. Add ~30–50% headroom:

```
pool size ≈ 200 × 1.4 ≈ 280 connections
```

- **Step 4 — Sanity-check the *other* side.** 280 connections × the DB's per-connection memory and the DB's own connection limit must both be affordable. If the database can't handle 280 connections, the bottleneck moves *into* the DB and you need a different fix — connection multiplexing (PgBouncer), read replicas, or cutting `W` so each connection frees up faster. Little's Law doesn't tell you *which* fix; it tells you *how big the gap is* and where to look.

- The discipline here is the lesson: **measure two terms, solve for the third, then check the constraint on every resource the third term touches.** That turns "the service feels slow under load" into "the pool caps us at 2,000 req/s; we need 280 connections or a 16 ms latency."

---

## Common Mistakes

1. **Reporting the average latency.** The mean is dominated by neither the typical user (median) nor the suffering ones (tail). It describes nobody. Report p50/p99/p99.9, always.

2. **Averaging percentiles across hosts or time windows.** There is no arithmetic that recovers a fleet p99 from per-host p99s. Merge histograms and recompute, or use a mergeable representation (Prometheus histograms) from the start.

3. **Sizing pools for average concurrency with no headroom.** `L = λ × W` gives the *average*; bursts and variance run hotter. Size above the average so you stay on the flat part of the curve, not on the knee.

4. **Load-testing with a closed-loop generator (`wrk`, naive `ab` loops).** Coordinated omission hides the tail. Use `wrk2` or any fixed-rate (open-loop) generator for latency numbers.

5. **Targeting high utilization as an efficiency win.** Running a latency-sensitive service at 90% looks "efficient" and behaves like a time bomb — `1/(1−ρ)` says latency is already ~9× service time and the next burst is the cliff. Plan for 60–70% on hot paths.

6. **Optimizing service time when the cost is wait time.** If 80% of `W` is queueing, halving the code's runtime barely moves the dashboard. Decompose `W` into wait + service *before* deciding what to optimize.

7. **Trusting Prometheus histogram percentiles with bad buckets.** Interpolation is only as good as your bucket boundaries. If your real latency lives in a range with no buckets, the computed percentile is fiction. Set buckets to straddle your SLO.

---

## Apply it

1. Find a real component where **Latency and Throughput** affects an interface or dependency.
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

- Which boundary is most affected by Latency and Throughput?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
- Can you average two servers' p99 latencies to get the cluster p99? Why or why not?
- Histograms vs summaries for latency metrics — which do you pick and why?
- wrk vs wrk2 — why does the "2" matter for latency numbers?
- Given a throughput target, how do you size capacity, and how much headroom do you add?
- Your connection pool is capped at 50 with a 20ms average query time — what's the max throughput, and what happens above it?
