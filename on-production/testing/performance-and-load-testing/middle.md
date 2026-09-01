# Performance & Load Testing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Performance & Load Testing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Performance & Load Testing

*A load test is only as honest as its workload model. Get the concurrency model, the metrics, and the realism right, and the numbers mean something. Get them wrong and you produce confident fiction.*

---

## Core Concept 1 — The metrics that matter, precisely

Four metric families. Sloppy use of any one produces a misleading verdict.

**1. Throughput (RPS).** Requests *completed* per second, not requests *sent*. The gap matters: if you inject 1000 req/s and the system completes 600, you are not "running a 1000 RPS test" — you are running an overloaded test and 400 req/s are queueing or failing. Report **completed** throughput.

**2. Latency distribution.** p50, p95, p99, p99.9 — and the **max**. Never the average; never standard deviation alone (latency is not normally distributed — it is heavy-tailed and right-skewed). A good summary line:

```
p50=45ms  p95=180ms  p99=420ms  p99.9=1.8s  max=4.2s
```

The *spread* between p50 and p99 is your most diagnostic number. A tight spread (p99 ≈ 2×p50) means consistent behaviour. A wide spread (p99 = 10×p50) means something — GC, lock contention, a cold cache path — punishes a minority of requests hard.

**3. Error rate.** Break it down by *kind*: 4xx (client/validation), 5xx (server), timeouts, connection refused/reset. A rising rate of connection-refused under load means you have hit a connection limit; rising 503s mean the system is shedding load (often *good* — it is protecting itself). Categorising errors tells you the failure *mode*.

**4. Saturation.** CPU %, memory, connection-pool usage, thread-pool queue depth, disk I/O, network. This comes from the server's own telemetry (Prometheus, the `monitoring-alerting` skill), not the load generator. Saturation is the *cause*; latency and errors are the *symptom*. The whole skill of interpretation is connecting symptom to cause.

---

## Core Concept 2 — Closed vs. open workload models

This is the concept that separates a load test you can trust from one you cannot. It is subtle, so read it twice.

**Closed model.** There are *N* virtual users. Each VU is a loop: send a request, *wait for the response*, (think time), send the next. The number of in-flight requests can never exceed *N*. The system **throttles itself** — if responses get slow, VUs send fewer requests, because they are blocked waiting. This is what `vus: 100` in k6 means by default.

```
Closed (100 VUs):
  VU is busy ──send──▶ [wait for response] ──▶ send next
  If server slows down, VUs naturally send LESS. Load is capped at 100 in-flight.
```

**Open model.** Requests arrive at a fixed *rate* — say 500 new requests per second — **regardless** of whether previous ones have come back. There is no fixed pool; if the server slows, new arrivals keep coming and pile up. This models the real world: actual users do not politely wait for your server to recover before clicking again — new users keep showing up at roughly the same rate.

```
Open (500 req/s):
  arrivals ──▶──▶──▶──▶──▶  (500/s, fixed)
  If server slows down, requests PILE UP. Queue grows. You see collapse.
```

**Why it matters.** A closed test *hides* overload, because it self-throttles. An open test *exposes* queue collapse — the nonlinear blow-up where a small load increase past capacity sends latency to the moon. Capacity planning and SLO validation should use an **open** model (fixed arrival rate), because that is how production traffic actually behaves.

In k6 this is the difference between the `constant-vus` executor (closed) and the `constant-arrival-rate` executor (open). Gatling is open-model by design; that is its defining feature.

---

## Core Concept 3 — Designing a sound load test

A trustworthy test has structure, not just "100 VUs for 30s."

1. **Define the question and the pass criteria first.** "At 500 req/s sustained, p99 < 300 ms and error rate < 0.1%." Without a pass criterion (an SLO — see `../../engineering-metrics-and-dora/`), a result is just numbers with no verdict.
2. **Model a realistic workload:**
   - **Request mix** — production proportions. If real traffic is 85% browse, 10% search, 5% checkout, your test must be too. A 100%-checkout test measures a workload that does not exist.
   - **Think time** — insert pauses between actions so VUs behave like humans, not benchmark bots.
   - **Data variety** — vary IDs, search terms, users. Hitting the *same* product 10,000 times measures your cache, not your system (see `../test-data-management/`).
3. **Shape the load over time:**
   - **Warm-up / ramp-up** — let JIT compile, caches fill, pools open. *Exclude this from measurement.*
   - **Steady state** — hold the target load long enough to be representative (minutes, not seconds). Measure here.
   - **Ramp-down** — optional, observe recovery.
4. **Isolate the variable.** Change one thing per run. Comparing two runs where you changed the code *and* the data *and* the VU count tells you nothing.
5. **Run on a prod-like environment.** Same instance sizes, same database with realistic data volume, same network topology. (Environment parity is a senior deep-dive — but know now that laptop numbers are fiction.)

---

## Core Concept 4 — A realistic k6 scenario

This goes well beyond the smoke test: an **open-model** arrival rate, a ramp, a realistic mix, think time, data variety, and SLOs as `thresholds` (k6 fails the run if they are breached — perfect for CI).

```javascript
// browse_and_buy.js
import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { SharedArray } from 'k6/data';

// Data variety: load many product IDs and pick at random.
const products = new SharedArray('products', () =>
  JSON.parse(open('./product_ids.json'))   // ["p-1", "p-2", ...]
);

export const options = {
  scenarios: {
    realistic_traffic: {
      executor: 'ramping-arrival-rate', // OPEN model: arrivals by rate
      startRate: 50,
      timeUnit: '1s',
      preAllocatedVUs: 200,
      maxVUs: 1000,
      stages: [
        { target: 50,  duration: '1m'  }, // warm-up (excluded mentally)
        { target: 500, duration: '2m'  }, // ramp to peak
        { target: 500, duration: '5m'  }, // STEADY STATE — measure here
        { target: 0,   duration: '1m'  }, // ramp-down
      ],
    },
  },
  thresholds: {
    http_req_duration: ['p(99)<300'],   // SLO → CI pass/fail
    http_req_failed:   ['rate<0.001'],  // < 0.1% errors
  },
};

export default function () {
  group('browse', () => {
    const id = products[Math.floor(Math.random() * products.length)];
    const res = http.get(`https://shop.example.com/products/${id}`);
    check(res, { 'browse 200': (r) => r.status === 200 });
  });
  sleep(Math.random() * 3 + 1); // think time: 1–4s

  // 20% of users go on to checkout — realistic request mix
  if (Math.random() < 0.2) {
    group('checkout', () => {
      const res = http.post('https://shop.example.com/cart/checkout',
        JSON.stringify({ item: 'p-1' }),
        { headers: { 'Content-Type': 'application/json' } });
      check(res, { 'checkout 200': (r) => r.status === 200 });
    });
    sleep(2);
  }
}
```

The `thresholds` block is the key upgrade: the test now has a verdict. k6 exits non-zero if p99 ≥ 300 ms or errors ≥ 0.1% — so it can gate a pipeline.

---

## Core Concept 5 — The same test in Locust

[Locust](https://locust.io/) describes load as Python code, which is pleasant when your test logic is complex or needs your own libraries. Behaviour is modelled with `@task` weights (the request mix) and `wait_time` (think time).

```python
# locustfile.py
import random
from locust import HttpUser, task, between

PRODUCT_IDS = [f"p-{i}" for i in range(1, 5001)]  # data variety

class ShopUser(HttpUser):
    # Think time: each user waits 1–4s between tasks.
    wait_time = between(1, 4)

    @task(8)  # weight 8 → ~80% of actions (request mix)
    def browse(self):
        pid = random.choice(PRODUCT_IDS)
        with self.client.get(f"/products/{pid}",
                             name="/products/[id]",   # group URLs in the report
                             catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"got {r.status_code}")

    @task(2)  # weight 2 → ~20%
    def checkout(self):
        self.client.post("/cart/checkout", json={"item": "p-1"})
```

Run headless (CI-friendly) with an open-ish spawn rate:

```bash
locust -f locustfile.py --host https://shop.example.com \
       --users 500 --spawn-rate 50 --run-time 8m --headless
```

> **Note:** Locust is fundamentally a **closed** model — each simulated user waits for its response. The `--spawn-rate` controls how fast users *arrive*, not the request rate. For a strict open model (fixed RPS that exposes queue collapse), prefer k6's `arrival-rate` executors, Gatling, or wrk2. Know which model your tool gives you by default — it changes what the test can prove.

---

## Core Concept 6 — Correlating latency with concurrency

A single result is a snapshot. The *insight* comes from how latency changes as load rises. Run the same workload at increasing concurrency and plot it:

```
Concurrency │  p50    p99    throughput   notes
     50      │  40ms   90ms    50 r/s      flat, healthy
    200      │  44ms  110ms   200 r/s      still flat — headroom
    500      │  52ms  180ms   500 r/s      slight rise — approaching knee
    800      │  95ms  600ms   780 r/s      ← THE KNEE: latency bends up,
   1000      │ 400ms  3.2s    810 r/s         throughput flattens
   1200      │ 1.1s   9s+     790 r/s      collapse: latency explodes,
                                            throughput DROPS (retries/queues)
```

Two landmarks to find:

- **The knee** — where latency starts bending upward sharply (here ~800). A resource is saturating (Little's Law in action: as utilisation nears 100%, queueing latency goes nonlinear). Your safe operating point is *below* the knee.
- **The cliff** — where throughput *stops rising and then falls* while latency explodes (here ~1000–1200). Past this, the system is in congestion collapse; more load makes it *slower overall*.

Capacity = the user count just before the knee where you still meet the SLO. That is the number capacity planning needs (and what the `system-design-estimation` skill turns into an infrastructure plan).

---

## Real-World Examples

- **Closed-model false confidence.** A team load-tests an API with 200 closed VUs, sees p99 = 250 ms, ships. Production melts during a promo. The closed test self-throttled and never created the arrival pile-up that real traffic does. Re-running with an open `constant-arrival-rate` executor at the real RPS reproduced the meltdown instantly.
- **The cache mirage.** A test hammered the same 5 product IDs and reported a blazing p99. Adding data variety (5000 IDs) sent p99 up 6× — the original test measured the cache, not the database.
- **No warm-up.** A JVM service showed an awful first-30s p99. The numbers were dominated by JIT warm-up. Adding a 1-minute warm-up stage excluded from measurement gave the real steady-state figure.

---

## Common Mistakes

- **Reporting injected RPS instead of completed RPS** when the system is overloaded.
- **Using a closed model for capacity planning** — it self-throttles and under-stresses.
- **No warm-up**, so JIT/cache-fill pollutes the measurement window.
- **One endpoint, one data row** — measuring an unrealistic, cache-friendly slice.
- **Standard deviation / average reporting** for a heavy-tailed distribution.
- **Changing two variables between runs**, making the comparison meaningless.
- **No think time**, turning human-shaped traffic into an unrealistic firehose.

---

## Apply it

1. Find a real component where **Performance & Load Testing** affects an interface or dependency.
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

- Which boundary is most affected by Performance & Load Testing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
