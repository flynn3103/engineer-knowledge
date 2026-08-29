# Performance & Load Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Performance & Load Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Performance & Load Testing

*A passing unit test says your code is correct. It says nothing about whether it survives a thousand users at once. Load testing answers a different question: how does the system behave under pressure?*

---

## Core Concept 1 — Why correctness tests are not enough

Imagine a `/report` endpoint that builds a PDF. Your test sends one request, gets a valid PDF, asserts the bytes look right. Green tick. Ship it.

In production, 50 users hit `/report` at once. Each PDF build holds a database connection and 200 MB of memory for two seconds. Your connection pool has 20 slots. Requests 21 through 50 queue, time out, and retry — which *adds* load. Memory spikes, the process is killed by the OOM reaper, and the service restarts mid-request for everyone. Your correctness test never saw any of this, because it never created **contention**: many requests fighting over the same finite resources.

Load testing exists to manufacture that contention on purpose, in a controlled place, so you observe the failure with a dashboard in front of you instead of a pager going off at 2 a.m.

A useful mental split:

- **Functional tests** vary the *input* and check the *output*.
- **Load tests** vary the *concurrency and duration* and check the *latency, throughput, and error rate.*

They are orthogonal. You need both.

---

## Core Concept 2 — The family of load tests

"Load testing" is an umbrella. Underneath it are several distinct test *types*, each answering a different question. They are **not interchangeable** — choosing the wrong one gives you a confident answer to a question you did not ask.

| Test type | The question it answers | Shape of the traffic |
|-----------|------------------------|----------------------|
| **Load test** | At our expected peak, do we still meet our SLOs? | Hold at realistic peak for a while. |
| **Stress test** | Where exactly does it break, and *how*? | Keep increasing load past peak until it fails. |
| **Spike test** | What happens on a sudden surge (flash sale, viral post)? | Jump from low to very high almost instantly. |
| **Soak / endurance test** | Does it degrade over hours? (memory leaks, log disk filling) | Moderate load held for hours. |
| **Scalability test** | Does adding capacity actually help? | Same load, more servers — does it improve? |
| **Capacity test** | How many users until an SLO breaks? | Slowly ramp and find the user count at breach. |

The three you will use first:

- **Load test** — the everyday one. "We expect 300 concurrent users at lunch. Can we serve them under 300 ms p99?"
- **Stress test** — "I want to know our ceiling and what failure looks like." Crucial because a graceful failure (shed load, return 503) is very different from an ugly one (crash, corrupt data).
- **Soak test** — "Run it overnight." Catches the slow killers: a memory leak that takes four hours to OOM, a cache that grows unbounded, a log file that fills the disk. A 60-second test will *never* find these.

---

## Core Concept 3 — Your first k6 test

[k6](https://k6.io/) is a modern, free load-testing tool. You write the test in JavaScript; it runs a fast Go engine underneath. No GUI, no XML — just a script you can keep in git next to your code.

```javascript
// smoke.js — the smallest useful load test
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,            // 10 virtual users...
  duration: '30s',    // ...hammering for 30 seconds
};

export default function () {
  const res = http.get('https://test-api.example.com/products');

  check(res, {
    'status is 200':        (r) => r.status === 200,
    'responded under 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1); // think time: each VU waits 1s before its next request
}
```

Run it:

```bash
k6 run smoke.js
```

The output you care about:

```
http_req_duration..: avg=92ms  min=41ms  med=78ms  max=1.2s  p(90)=140ms  p(95)=210ms
http_req_failed....: 0.40%  ✓ 12   ✗ 2988
checks.............: 99.93% ✓ 5996 ✗ 4
iterations.........: 3000
```

Read it like this: 3000 requests went out; 0.4% failed; the **median** was 78 ms but the **95th percentile** was 210 ms and the **worst** request took 1.2 seconds. That spread is the whole story — keep reading.

---

## Core Concept 4 — Percentiles, and why the average lies

This is the single most important idea in this topic, so go slowly.

Suppose 10 requests come back with these latencies (ms):

```
50, 52, 55, 51, 53, 54, 50, 52, 51, 2000
```

- **Average (mean):** (50+52+55+51+53+54+50+52+51+2000)/10 = **246.8 ms**
- **Median (p50):** ~52 ms
- **p90 (9th slowest):** 55 ms
- **p100 (max):** 2000 ms

The average says "247 ms" — but **nobody** experienced 247 ms. Nine users had a snappy ~52 ms; one user waited a full **2 seconds**. The average is a blend of two realities that exists for no actual user. Averages *hide* the slow tail by drowning it in fast requests.

Percentiles describe the tail directly:

- **p50** — the typical experience.
- **p95** — 1 in 20 requests is at least this slow. On a page that makes 20 backend calls, *one of them* hits p95 — so p95 is roughly "the slowest part of a typical page."
- **p99** — 1 in 100. Your power users, who click a lot, hit this constantly.
- **p99.9** — the edge. Matters enormously at scale: at a million requests, that is a thousand furious users.

**Rule of thumb:** state SLOs as percentiles, never averages. "p99 < 300 ms" is a real promise. "avg < 300 ms" can be true while a quarter of your users suffer.

---

## Core Concept 5 — Reading a result and the four golden signals

When you read any load-test result, scan four numbers — the same four the `monitoring-alerting` skill calls the golden signals:

1. **Throughput** — requests/sec actually completed. If you sent more than this, the system could not keep up.
2. **Latency distribution** — p50 / p95 / p99, *not* the average.
3. **Error rate** — the percentage of failed requests. A test where latency stayed low *because half the requests errored out instantly* is a disaster wearing a smile.
4. **Saturation** — CPU, memory, connection-pool, disk on the system under test. You need this from the *server's* monitoring, not the load tool. Latency that creeps up as concurrency rises usually means a resource is filling.

The error rate is the classic junior trap. A "great" p99 means nothing if `http_req_failed` is 30%. **Always read latency and error rate together.** Fast failures are still failures.

---

## Real-World Examples

- **The lunchtime spike.** An internal HR tool is fine all morning, then crawls at 12:00 when everyone submits timesheets at once. A *spike test* (jump from 5 to 200 VUs instantly) reproduces it on demand instead of waiting for noon.
- **The overnight leak.** A service passes every load test but pages on-call every third night around 3 a.m. A *soak test* (50 VUs for 6 hours) reveals memory climbing 2% per hour — a leak that only a long run exposes.
- **The retry storm.** A stress test pushed past capacity shows latency climbing, then clients timing out and *retrying*, which doubles the load and accelerates collapse. The fix lives elsewhere (the `retry-pattern` and `circuit-breaker-pattern` skills), but the load test is what made the failure mode visible.

---

## Common Mistakes

- **Quoting the average.** "Avg 90 ms!" while p99 is 1.4 s. Report percentiles.
- **Ignoring the error rate.** Low latency with 20% errors is a failing test, not a passing one.
- **No think time.** Real users pause; a tight loop with no `sleep()` models a bot, not humans, and gives unrealistically pessimistic numbers.
- **Testing on your laptop.** A dev box with one user and no real data tells you nothing about production. (Environment parity is a senior-level deep dive.)
- **A 30-second soak test.** Leaks and disk-fills need *hours*. Match the duration to the question.
- **Running one test type and calling it "load tested."** A load test is not a stress test is not a soak test.

---

## Apply it

1. Choose one small, known input for **Performance & Load Testing**.
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

- What problem does Performance & Load Testing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
