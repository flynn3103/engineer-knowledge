# Why Async — Senior

<!-- level-focus -->
At senior level, focus on this question:

> When does async provide no benefit over threads, and could even be the
> wrong choice?

Prerequisite: [`middle.md`](middle.md).

---

## Low connection count: threads are simpler and just as fast

```mermaid
flowchart LR
    LowCount["A service handling\n50 concurrent\nconnections"] --> ThreadsFine["50 threads is a TRIVIAL\nresource cost - async's\ncomplexity buys almost\nNOTHING here"]
```

If your actual concurrent connection count is in the dozens or low
hundreds, thread-per-connection overhead is simply not a real problem —
async programming's added complexity (callback/coroutine-based control
flow, the cooperative-scheduling pitfalls from the Async/Await
concurrency-model page) isn't justified when the C10K-scale problem
doesn't actually apply to your workload.

## CPU-bound work: async provides zero speedup (recap)

```mermaid
flowchart LR
    CPUBound["CPU-bound work\n(the exact anti-pattern\nfrom Async/Await senior.md)"] --> NoHelp["Async gives NO speedup -\nit's a concurrency\nmechanism for WAITING,\nnot a parallelism\nmechanism for COMPUTING"]
```

This is the exact restatement of the Async/Await concurrency-model
page's senior-level point: if your workload is genuinely CPU-bound, not
I/O-bound, async provides no benefit whatsoever — you need the
parallel-programming track's tools (multiple processes/cores) instead.

## Mixed workloads: the worst of both worlds if handled naively

> 🎯 **Senior takeaway:** the decision to adopt async should be driven by
> a specific, measured requirement — high concurrent I/O-bound connection
> count, genuinely in the thousands-plus range — not adopted by default
> for "modern" appeal. For workloads with low connection counts, or that
> are genuinely CPU-bound, threads (or even a synchronous model) are
> simpler and equally or more performant; reach for async specifically
> when you've confirmed the C10K-scale I/O-concurrency problem actually
> applies.

## Test yourself

1. Why would adopting async for a service with only 50 concurrent
   connections likely add complexity without meaningful benefit?
2. Why does async provide zero benefit for genuinely CPU-bound work, even
   at very high "concurrency" (many pending CPU-heavy tasks)?
3. What specific, measurable signal would you look for before deciding a
   service genuinely needs to adopt async programming?

Continue to [`professional.md`](professional.md) to see the real thread
vs. async cost numbers that justify this trade-off at scale.
