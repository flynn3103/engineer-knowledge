# GC Tuning in Production — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **GC Tuning in Production** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Why the GC pauses at all

To safely reclaim memory, the collector needs a consistent view of which objects are alive. The simplest way to get that is to freeze the application for a moment so nothing moves while the GC looks. That freeze is the **stop-the-world (STW) pause**.

Modern collectors do most of their work *concurrently* — alongside your running program — and only freeze for tiny windows. But "tiny" is relative, and the freeze never fully disappears.

### The GC tuning triangle (the one diagram to remember)

There are three things a GC trades against each other:

```
                 LATENCY
                (short pauses)
                    /\
                   /  \
                  /    \
                 /      \
                /        \
   THROUGHPUT  /__________\  MEMORY FOOTPRINT
 (less GC CPU)             (small heap)
```

You can usually get **two** of these, not all three:

- Want **short pauses** *and* **high throughput**? You will need a **bigger heap** (more memory).
- Want **short pauses** *and* **a small heap**? The GC has to work harder and more often — **throughput drops**.
- Want **high throughput** *and* **a small heap**? You accept **longer/occasional pauses**.

Every tuning decision is a move inside this triangle. There is no setting that wins all three.

### The "bigger heap = better GC" surprise

This is counterintuitive for beginners. Giving the GC *more* memory often makes it run *less* and feel smoother. Why?

Think of the heap as a room and garbage as trash. If the room is tiny, it fills up constantly and you must take out the trash every few minutes. If the room is large, trash accumulates slowly and you take it out rarely. Each trip costs the same, but you make far fewer trips.

A bigger heap means more *headroom* between collections, which means **lower GC frequency**. Fewer collections, fewer pauses.

### The allocation-rate lever (the one you control in code)

The GC's workload is driven by how much garbage you create. If you allocate less, the GC has less to do. This is the lever that lives entirely in *your* code, not in flags:

- Reuse buffers instead of allocating a new one per request.
- Avoid creating millions of tiny temporary objects in a hot loop.
- Don't build a huge intermediate list just to throw it away.

**Reducing allocation is almost always the first and best tuning move**, because it shrinks the problem rather than rearranging who pays for it.

### Why the average pause is a lie

Suppose your service handles 10,000 requests and 9,990 of them respond in 5 ms, but 10 of them hit a GC pause and take 200 ms. The *average* looks fine (~5.2 ms). But 1 in 1,000 of your users waited 40× longer.

The numbers that matter are **percentiles**: p99 ("99th percentile" — the slowest 1%) and p999 (slowest 0.1%). GC pauses live in the tail. Averages hide them. This is why people say *"latency is a tail problem"* — and the tail is where the GC shows up.

## Code Examples

You rarely "call" the GC in production code, but two things are worth seeing.

**High vs. low allocation (the lever you own).** This Java snippet allocates a fresh array on every iteration — a classic allocation storm:

```java
// High allocation: a new buffer every call -> lots of garbage
public int sumLines(List<String> lines) {
    int total = 0;
    for (String line : lines) {
        byte[] buf = new byte[1024];   // allocated, used briefly, thrown away
        total += process(line, buf);
    }
    return total;
}
```

Reusing the buffer turns thousands of allocations into one:

```java
// Low allocation: reuse one buffer
public int sumLines(List<String> lines) {
    int total = 0;
    byte[] buf = new byte[1024];        // allocated once
    for (String line : lines) {
        total += process(line, buf);
    }
    return total;
}
```

**Asking the runtime to print what the GC is doing.** You don't tune blind. In Go, one environment variable makes the runtime narrate every collection:

```bash
GODEBUG=gctrace=1 ./myserver
```

In the JVM, a logging flag does the same:

```bash
java -Xlog:gc ./MyApp.jar
```

At this tier you are not expected to decode every field — just to know these switches exist and that **the first step of tuning is turning on visibility.**

## Best Practices

- **Measure before you tune.** Turn on GC logging first. Never change a flag based on a blog post alone.
- **Reduce allocation first.** It is the cheapest, most durable win and the only lever fully in your control.
- **Change one thing at a time.** GC behavior is interacting and subtle; batched changes are un-diagnosable.
- **Think in percentiles.** Track p99/p999 latency, not just the average.
- **Right-size the heap before reaching for exotic collectors.** Often "give it more memory" is the whole fix.

## Edge Cases & Pitfalls

- **Confusing a memory leak with a GC problem.** If memory only ever climbs and the GC can't reclaim it, you have a leak — the objects are still reachable. No GC flag fixes a leak. (Senior tier covers this.)
- **Cargo-culting flags.** Copying a stranger's JVM flag set "because it's fast" usually makes things worse; their workload isn't yours.
- **Tuning the average away while the tail gets worse.** Some changes lower mean latency but increase the worst pauses. Watch p999.
- **Forgetting the container limit.** Inside Kubernetes, your process can think it has the whole machine's RAM while the container limit is far lower — leading to the orchestrator killing it (OOMKilled). This is a top-3 production GC failure and the higher tiers dig into it.

---

## Apply it

1. Choose one small, known input for **GC Tuning in Production**.
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

- What problem does GC Tuning in Production solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
