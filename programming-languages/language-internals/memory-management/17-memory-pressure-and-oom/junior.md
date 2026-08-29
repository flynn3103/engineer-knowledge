# Memory Pressure & OOM — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Memory Pressure & OOM** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Allocating is not using

When you call `malloc(1_000_000_000)`, the C library asks the kernel for a billion bytes of *address space*. The kernel says "sure" and returns a pointer — but it has not reserved a single byte of physical RAM. It has just drawn a region on a map. Physical pages get attached only when you write to them.

This behavior is called **lazy allocation** (or demand paging). The consequence is profound and surprising:

> `malloc` almost never fails, even when you ask for more than exists. The failure happens *later*, when you touch the memory, and that failure is not a returned error — it's the OOM killer.

So the classic defensive code `if (malloc(...) == NULL) { handle_error(); }` rarely triggers on Linux. The death comes from a different direction entirely.

### 2. RSS is the number that matters

Two numbers describe your process's memory:

- **VSZ (virtual size):** everything you reserved. A program can have a 20 GB VSZ and use 200 MB of real RAM.
- **RSS (resident set size):** the physical pages actually backing your process. This is what counts against the machine's RAM.

When people say "this process is using 3 GB," they mean RSS. When the machine runs low and the kernel needs a victim, it looks at who is consuming real pages — RSS — not who reserved the most address space.

### 3. The kernel runs out, then kills

When every process's combined RSS plus everything else (the OS, caches it can't free) approaches physical RAM, the kernel tries to make room: it drops cached file data, it may move pages to swap. If those efforts fail and a process still needs a page that cannot be provided, the kernel invokes the **OOM killer**. The OOM killer chooses one process and sends it `SIGKILL`.

Three things make this brutal for beginners:

1. **It's instant and uncatchable.** `SIGKILL` cannot be caught, blocked, or handled. No `finally`, no destructors, no graceful shutdown. The process is simply gone.
2. **The victim is often innocent.** The kernel picks the process that frees the most memory, which is frequently the *biggest* process — not the one whose runaway loop caused the crisis. Your well-behaved database can be killed because a buggy script next to it exhausted RAM.
3. **The only evidence is in the kernel log.** Your application logs show nothing — they just stop. The story is in `dmesg` / the system journal.

### 4. Pressure comes before death

Before the kill, the system shows strain. It slows down because the kernel spends CPU reclaiming memory, and disk activity spikes if swap is involved. These symptoms — a service mysteriously getting slow under load, then disappearing — are the signature of memory pressure building to OOM. Learning to see the slowdown as a *warning* rather than a separate, unrelated problem is a key skill.

## Code Examples

### Allocation succeeds, touching kills

```c
// overcommit.c — demonstrates allocate-vs-touch on Linux
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    size_t gb = 1UL << 30;          // 1 GiB
    char *p = malloc(50 * gb);      // ask for 50 GiB

    if (p == NULL) {
        printf("malloc failed\n");  // rarely prints on Linux
        return 1;
    }
    printf("malloc of 50 GiB succeeded (no RAM used yet)\n");

    // Now actually touch the memory, page by page.
    // RSS climbs here. On a small machine, the OOM killer
    // ends the process partway through this loop.
    for (size_t i = 0; i < 50 * gb; i += 4096) {
        p[i] = 1;                   // first write to each page commits RAM
    }

    printf("touched all of it (you have a big machine)\n");
    return 0;
}
```

Run it on a 4 GB machine and you'll typically see "malloc … succeeded" print, then the program vanishes mid-loop with no message — killed. Check the kernel log:

```bash
dmesg | tail -n 20
# ... Out of memory: Killed process 1234 (overcommit) ...
```

### Watching RSS climb in Python

```python
# climb.py — watch resident memory grow
import os, time

def rss_mb():
    # statm reports pages; field 2 (index 1) is resident pages
    with open(f"/proc/{os.getpid()}/statm") as f:
        resident_pages = int(f.read().split()[1])
    return resident_pages * 4096 / (1024 * 1024)

chunks = []
while True:
    chunks.append(bytearray(50 * 1024 * 1024))  # 50 MB, and we touch it
    print(f"RSS = {rss_mb():.0f} MB")
    time.sleep(0.3)
```

`bytearray(n)` zero-fills, so it *touches* every page immediately — RSS climbs in real time. Watch the numbers grow until the process is killed.

### Reading the evidence after a kill

```bash
# Was my process OOM-killed? The kernel log is the source of truth.
dmesg -T | grep -i -A1 "killed process"

# Example output:
# [Tue Jun 24 10:02:11 2026] Out of memory: Killed process 4821 (python3)
#   total-vm:8421000kB, anon-rss:3980000kB, file-rss:0kB
```

`anon-rss` is the real RAM the victim was holding — the number the kernel cared about.

## Best Practices

- **Look at RSS, not VSZ.** Use `ps -o pid,rss,vsz,comm` or `top` (the `RES` column). RSS is reality.
- **Assume any process can be killed at any instant.** Make work resumable: checkpoint long jobs, use durable queues so a killed worker's task is retried.
- **Don't rely on `malloc`/`new` returning an error.** On Linux it usually won't. Defensive null-checks are still correct C, but they are not your OOM safety net.
- **Set bounds on memory-hungry structures.** Cap cache sizes, batch sizes, and queue depths so growth is bounded rather than open-ended.
- **Check the kernel log first when a process disappears.** `dmesg -T | grep -i "killed process"` answers "was this OOM?" in seconds.
- **Reproduce with a small limit.** You don't need a huge dataset to test OOM behavior; run your program under a tight memory limit locally (later tiers show how with cgroups/`ulimit`).

## Edge Cases & Pitfalls

- **"My `malloc` succeeded so I have the memory."** No — you have an address-space promise. The check that matters is whether you can touch all of it.
- **Blaming the killed process.** The victim is frequently chosen for being *large*, not for being *guilty*. Investigate who *grew*, not only who *died*.
- **Watching the wrong number.** A 30 GB VSZ on a 16 GB machine is not necessarily a problem; a 15 GB RSS is. Beginners panic at VSZ and miss the real signal.
- **Expecting cleanup on death.** No destructors, `finally` blocks, atexit handlers, or buffered writes survive a `SIGKILL`. Files mid-write can be left truncated.
- **Confusing "slow" with "fine."** A system thrashing under memory pressure is seconds away from an OOM kill, not in a stable degraded state. Slowness is a fire alarm.
- **Trusting that calloc/zeroed memory is "already used."** `calloc` can still be lazy: the kernel can hand out a shared zero page and only commit real RAM on first write. Zeroing isn't always touching.

---

## Apply it

1. Choose one small, known input for **Memory Pressure & OOM**.
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

- What problem does Memory Pressure & OOM solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
