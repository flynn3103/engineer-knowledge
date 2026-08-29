# Latency and Throughput — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Latency and Throughput** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Performance](../README.md) → Latency and Throughput
> *"It's fast" is not a measurement. There are two numbers hiding behind that word — how long one request takes, and how many requests you can handle per second — and they are not the same number, do not move together, and trade off against each other in ways that surprise people for years.*

---

## Core Concept 1 — Latency vs Throughput: Two Different Numbers

The cleanest way to feel the difference is a highway.

```
LATENCY    = how long it takes ONE car to drive from A to B   (e.g. 30 minutes)
THROUGHPUT = how many cars pass a point per hour               (e.g. 2,000 cars/hour)
```

These describe the same road but answer different questions. A single sports car on an empty road has *fantastic* latency (it gets there fast) and *terrible* throughput (only one car went by). A jam-packed eight-lane freeway crawling at 10mph has *awful* latency for each driver but possibly *huge* throughput — thousands of cars pass per hour because there are so many lanes, even though each individual driver is miserable.

Now translate to an HTTP service:

```
LATENCY    = how long ONE request takes              "this request took 45ms"
THROUGHPUT = how many requests finish per second      "we're serving 8,000 req/s"
```

You can have low latency and low throughput (one fast request, but the server can only do one at a time). You can have high latency and high throughput (every request is slow, but you run thousands in parallel). They are genuinely independent dials.

Here is the trap that makes people conflate them. They write a tiny benchmark:

```go
start := time.Now()
resp := callService()          // one request
elapsed := time.Since(start)   // 45ms
fmt.Println(elapsed)           // "45ms — nice and fast!"
```

That measured **latency** — one request's duration. It said *nothing* about throughput. Maybe the server handles 10,000 of these per second; maybe it handles 3 before it falls over. A single-request timer cannot tell you. To measure throughput you have to send *many* requests, ideally concurrently, and count how many complete per second.

> **Key insight:** Latency is "how long does *one* take?" Throughput is "how many can I do *per second*?" A stopwatch on a single operation measures latency and reveals nothing about throughput. A counter of completed operations over time measures throughput and reveals nothing about any individual operation's wait. You need both numbers, and you must measure them differently.

---

## Core Concept 2 — They Trade Off: The Batching Example

The surprising part is not that latency and throughput differ. It's that *improving one often hurts the other*. The classic example is **batching**.

Imagine a service that writes records to a database. The naive version writes each record as it arrives — one network round-trip per record:

```go
// One write per record. Lowest latency per record, lowest throughput.
func handle(record Record) error {
    return db.Insert(record)   // ~2ms round-trip, returns immediately
}
```

Each record is handled the instant it arrives, so the *latency* for any one record is small (~2ms). But the *throughput* is capped: every record pays a full round-trip, and round-trips are expensive.

Now batch: wait until you've collected 100 records, then write them all in one trip.

```go
// Collect 100, then write together. Higher throughput, higher latency.
var buffer []Record
func handle(record Record) {
    buffer = append(buffer, record)
    if len(buffer) == 100 {
        db.InsertBatch(buffer)   // one round-trip writes all 100
        buffer = nil
    }
}
```

One round-trip now carries 100 records instead of 1. Throughput goes *way* up — you've amortised the round-trip cost across 100 records. But look what happened to the *first* record in the batch: it arrived, then sat in the buffer **waiting for 99 friends** before anything was written. Its latency went from 2ms to however long it took to fill the batch — maybe 50ms, maybe more. You traded latency for throughput.

```
NO BATCHING:   record → write immediately      low latency, low throughput
BATCHING:      record → wait for batch → write  HIGH throughput, HIGHER latency
```

Neither is "better" in the abstract. It depends on what you're building:

- A **payment confirmation** the user is staring at? Latency matters — don't make them wait for a batch.
- A **background analytics pipeline** ingesting billions of events? Throughput matters — batch aggressively; nobody is watching any single event.

This same trade-off shows up everywhere: buffering, connection pooling, Nagle's algorithm in TCP, GPU batch inference, log flushing. Whenever you "group work to be efficient," you are almost always buying throughput with latency.

> **Key insight:** Latency and throughput frequently *trade off*. Batching, buffering, and queueing raise throughput by making individual operations wait. The right choice is not "maximise both" (often impossible) but "know which one your users actually feel, and optimise *that* one." Optimising the wrong one is wasted effort at best and a regression at worst.

---

## Core Concept 3 — Latency Is a Distribution, Not a Number

Here is the single most important idea on this page, and the one most likely to be missing from a junior's mental model.

When you say "the latency is 50ms," you're implying every request takes 50ms. That is *never* true. Run the same request a thousand times and you get a thousand *different* numbers — a spread, a **distribution**. Most cluster around some typical value, but a handful are dramatically slower because of a GC pause, a cache miss, a slow disk, a noisy neighbour on the same machine, a lock someone else was holding, a network hiccup.

Picture 1,000 requests sorted from fastest to slowest:

```
Most requests fast...                    ...a few are MUCH slower (the "tail")
|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||   |   |    |     |
20ms  25ms  30ms ........................ 50ms ......... 120ms  300ms  600ms  900ms
                                                          ^^^^^^^^^^^^^^^^^^^^^^^^
                                                          the tail — rare but real
```

That long thin tail on the right is **tail latency**, and it's where real users get hurt. The distribution is almost always *skewed*: a big lump of fast requests and a long tail of slow ones. It is not a neat bell curve. This shape is exactly why the **average** misleads you.

Suppose 99 requests take 20ms and one request takes 2,000ms (two seconds — a GC pause, say). The average is:

```
(99 × 20ms + 1 × 2000ms) / 100 = (1980 + 2000) / 100 = 39.8ms
```

"Average latency: ~40ms — looks healthy!" But no single request actually took 40ms. 99 of them were great (20ms) and one was a disaster (2s). The average *invented* a number that describes nobody and *hides* the one user who had a terrible time. One slow outlier dragged the mean up; on a real service, a flood of fast requests can drag it *down* and hide a tail that's quietly ruining things for thousands of people.

> **Key insight:** Latency is a *distribution*, not a single value, and that distribution is *skewed* (a fast lump plus a slow tail). The **average flattens the tail into a single misleading number** — it can be pulled around by outliers and it describes a request that may not exist. To talk honestly about latency you must talk about the *shape*: the typical case *and* the tail.

---

## Core Concept 4 — Percentiles: p50, p95, p99

So if the average lies, what do you use instead? **Percentiles.** They describe the distribution honestly by reporting specific points along it.

Take all your measurements and sort them from fastest to slowest. A percentile **pN** is the value below which N% of requests fall:

- **p50** (the **median**): half of requests are faster than this, half are slower. This is your *typical* user. Much more honest than the average because outliers can't drag it around — one 2-second request can't move the middle of a sorted line.
- **p95**: 95% of requests are at or below this; the slowest 5% are above it.
- **p99**: 99% of requests are at or below this; the slowest **1 in 100** are worse.

The intuition to burn into your brain:

> **p99 = 800ms means: 1 in every 100 requests takes 800ms *or worse*.**

Read that again. It is not "the worst request was 800ms." It's "*at least* one percent of requests are this slow or slower." On a service doing 10,000 requests per second, **1% is 100 requests every second** experiencing 800ms+. That's not a rounding error — that's a crowd of unhappy users, continuously.

Here's how the same 1,000-request dataset reads through different lenses:

```
1000 requests, sorted fastest → slowest

p50  =  22ms    "typical user — half are faster than this"
p95  =  60ms    "the slowest 5% start here"
p99  = 480ms    "1 in 100 waits at least this long"
p99.9= 1200ms   "1 in 1000 — your unluckiest power users"
avg  =  41ms    "describes nobody; quietly hides the tail above"
```

Notice how p50 (22ms) and the average (41ms) are *both* far below p99 (480ms). If you only watched the average, you'd swear the service was healthy at 41ms — while 1% of your traffic, every second, waited half a second or more.

A small but critical subtlety: **percentiles do not average.** You cannot compute a service's overall p99 by averaging the p99 of each server, and you cannot get last hour's p99 by averaging each minute's p99. Percentiles must be computed over the *combined* raw data. Tools like histograms (e.g. HDR histograms, Prometheus histograms) exist precisely to merge distributions correctly — a detail you'll meet in [middle.md](middle.md), but know now that "averaging percentiles" is a real and common bug.

> **Key insight:** Report **p50 (typical), p95, and p99 (tail)** — never just the average. "p99 = X" means *1 in 100 requests is at least that slow*, which on a busy service is a large, constant number of real users. And remember: you can't average percentiles together; they must come from the combined raw measurements.

---

## Core Concept 5 — Measuring Latency Without Lying to Yourself

You can't improve what you measure wrong. Here's how to take an honest latency measurement, starting from the simplest correct approach.

**The unit of measurement is one operation, timed end to end:**

```go
start := time.Now()
doRequest()                    // the operation you care about
elapsed := time.Since(start)   // ONE latency sample
```

That's *one sample*. One sample tells you almost nothing — it could be a lucky-fast or unlucky-slow request. To learn the *distribution*, you collect **many** samples and look at their spread:

```go
samples := make([]time.Duration, 0, 1000)
for i := 0; i < 1000; i++ {
    start := time.Now()
    doRequest()
    samples = append(samples, time.Since(start))
}

sort.Slice(samples, func(i, j int) bool { return samples[i] < samples[j] })

p50 := samples[len(samples)*50/100]   // median
p95 := samples[len(samples)*95/100]
p99 := samples[len(samples)*99/100]
fmt.Printf("p50=%v  p95=%v  p99=%v\n", p50, p95, p99)
```

Sort the samples, then index in by percentage. `samples[990]` out of 1,000 sorted values *is* your p99. That's all a percentile is mechanically: sort, then pick the element at the right position. (Real tools use histograms so they don't have to store every sample, but the meaning is identical.)

Three rules to keep the measurement honest, even at this level:

1. **Measure throughput separately, and under realistic load.** A latency you measured by sending one request at a time can look beautiful and then collapse the moment real concurrent traffic arrives. Latency *under load* is the number that matters; latency on an idle system is a vanity number.

2. **Don't trust the average — always print percentiles.** If your measurement only spits out a mean, you've thrown away the tail before you even started.

3. **Measure where the user is, not just inside your code.** Your server might log "handler took 5ms," but the user waited 200ms because of network, queuing before your handler, and serialization. The latency that matters is the one the *user experiences*, end to end — sometimes called *client-observed* latency.

> **Key insight:** One timing sample is anecdote; the **distribution of many samples** is data. Collect many, sort them, read off p50/p95/p99 — and always measure latency *under realistic load* and *as close to the user as you can*. An idle, single-request benchmark produces numbers that feel great and predict nothing.

---

## Real-World Examples

**1. The "average looks fine" outage that wasn't an outage.** A team's dashboard showed average response time steady at ~40ms for weeks. Users kept complaining the app "randomly hangs." The average was hiding a p99 of 3 seconds caused by a slow query that fired on ~2% of requests. Nobody saw it because 98% fast requests dragged the mean down. The fix started the day they added a **p99 line to the dashboard** — suddenly the 3-second spikes were visible, traceable, and fixable. The lesson isn't about the query; it's that *the average had been lying the whole time*.

**2. Batching that made the product feel broken.** A notification service was rewritten to batch outgoing messages for efficiency — collect 500, send together. Throughput tripled (great for the cost dashboard). But each notification now waited up to 30 seconds to fill a batch, so users got "your order shipped" emails *long* after the event. Throughput went up; the thing users actually felt — *latency* — got dramatically worse. They split the path: latency-sensitive user-facing notifications sent immediately, bulk marketing emails batched. Right tool, right metric.

**3. "It's fast on my laptop."** A developer benchmarks an endpoint locally: one request at a time, p50 looks like 8ms, ships it. In production under 5,000 req/s, p99 is 1.2 seconds. Nothing was wrong with the code's logic — the *single-request* latency was real but irrelevant. Under concurrent load, contention and queuing produced a tail that an idle, one-at-a-time benchmark could never reveal. Latency must be measured *under load*, or it predicts nothing — a theme that runs straight into [02 — Benchmarking](../02-benchmarking-and-microbenchmarks/junior.md).

---

## Common Mistakes

1. **Saying "it's fast" without saying which number.** Fast latency? High throughput? They're independent. A claim about one is not a claim about the other, and the listener will assume whichever you *didn't* mean.

2. **Measuring one request and calling it the latency.** One sample is an anecdote. Real latency is a distribution; you need many samples and percentiles to describe it.

3. **Trusting the average.** A skewed distribution makes the mean describe a request that doesn't exist and hides the tail entirely. Report p50/p95/p99, not avg.

4. **Confusing p99 = X with "the worst is X."** p99 is the line below which 99% fall — the slowest 1% are *worse* than X. On a busy service that 1% is a crowd, not an edge case.

5. **Optimising throughput when users feel latency (or vice versa).** Batching a payment confirmation to "improve performance" makes the user wait longer. Match the metric you optimise to the one your users actually experience.

6. **Benchmarking on an idle system / your laptop.** Latency without realistic concurrent load is a vanity number. The tail that hurts production only appears under load.

7. **Averaging percentiles together.** You cannot get the overall p99 by averaging per-server or per-minute p99s. Percentiles must be computed over the combined raw data, usually via histograms.

---

## Apply it

1. Choose one small, known input for **Latency and Throughput**.
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

- What problem does Latency and Throughput solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
