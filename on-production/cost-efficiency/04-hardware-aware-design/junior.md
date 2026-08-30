# Hardware-Aware Design — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given one service's resource-usage signals, can you tell whether it is CPU-bound, memory-bound, or I/O-bound, and pick an instance type whose vCPU-to-memory ratio actually matches?

Use the smallest realistic scenario that exposes the decision and its failure behavior.

*A slow service isn't automatically "needs more CPU." Matching hardware to a workload starts with knowing which resource is actually the bottleneck — guess wrong and you pay for capacity that never gets touched.*

---

## Core Concept 1 — What "Hardware-Aware" Means

Hardware-aware design is the discipline of choosing compute (instance family, CPU architecture, memory size, disk type) to match what a workload actually consumes, instead of picking a default size and hoping it's close enough. It sits downstream of profiling and upstream of the bill: you can't match hardware to a workload you haven't measured, and the instance choice is what turns that measurement into either efficient spend or waste.

Three resource profiles cover most services:

| Profile | Bottleneck | Typical symptom |
|---|---|---|
| **CPU-bound** | Compute cycles | High CPU utilization, throughput scales with clock speed and core count |
| **Memory-bound** | RAM capacity or bandwidth | Frequent paging/swapping, or CPU sits idle waiting on memory access |
| **I/O-bound** | Disk or network throughput | CPU looks idle (high `%wa`/iowait) while requests still queue up |

This topic is specifically about matching *this* workload to *this* hardware. It doesn't cover how to model the dollar cost of that hardware (Cost Modeling), how to forecast how much of it you'll need (Capacity Planning), or which billing lever pays for it (Cloud Cost Optimization) — those are separate topics. Here, the only question is: what shape of machine does this workload need?

## Core Concept 2 — Reading the Signals with Standard Tools

You don't need exotic tooling to classify a workload. Three commands, in order of how often you'll reach for them:

- **`top`** (or `htop`) — a live snapshot. Look at `%us` (user CPU), `%sy` (system CPU), `%wa` (I/O wait), and `%id` (idle). High `%us` + `%sy` with low `%wa` points to CPU-bound. High `%wa` with CPU otherwise idle points to I/O-bound.
- **`vmstat 1`** — a rolling view over time (one line per second). The `si`/`so` columns show swap activity — nonzero and sustained means you're memory-bound and the OS is paging. The `b` column (processes blocked on I/O) confirms I/O-bound if it's consistently above zero.
- **`iostat -x 1`** — disk-specific detail. `%util` near 100 with high `await` (average wait time per I/O request) confirms the disk itself, not just "I/O in general," is the bottleneck.

For a first pass, that's enough. (`perf stat` gives you cycle-level detail like cache misses and instructions-per-cycle, but that's a middle-level tool — save it until you actually need to distinguish "CPU-bound because busy" from "CPU-bound because stalled on memory.")

## Core Concept 3 — A Repeatable Method

1. **Generate a representative load** — run the service under something close to real traffic, not an idle process. A profile taken at idle tells you nothing.
2. **Capture all three signals** — `top`/`vmstat` for CPU and memory, `iostat` for disk — over the same window, at least 60 seconds, so a brief spike doesn't get mistaken for the steady state.
3. **Classify the bottleneck** using the table in Concept 1: which resource is consistently near its ceiling while the others have headroom?
4. **Match an instance family to that classification** — compute-optimized for CPU-bound, memory-optimized for memory-bound, and for I/O-bound, prioritize disk/network throughput over raw vCPU count (see Concept 5).
5. **Re-measure after switching** — confirm the new instance actually removed the bottleneck rather than just moving it somewhere else.

## Core Concept 4 — Worked Example: an Image-Resizing Worker

A background worker pulls jobs off a queue, downloads an image, resizes it, and re-uploads it. It's currently running on a general-purpose instance with 2 vCPUs and 8 GiB RAM. Throughput is lower than expected, and the team's first instinct is "add more vCPUs."

Running the method under a realistic batch of resize jobs for 90 seconds produces this snapshot (illustrative numbers, not a real benchmark):

```
$ vmstat 1 5
procs -----------memory---------- ---swap-- -----io---- --cpu--
 r  b   swpd   free   buff  cache   si   so    bi    bo  us sy id wa
 4  0      0  612344  20112 512300    0    0   180   240  22  6 10 62
 5  1      0  598120  20112 511980    0    0   210   260  20  7  9 64
 4  0      0  601884  20112 512040    0    0   195   250  21  6 11 62
```

`us` (user CPU) sits around 20%, well under saturation. `wa` (I/O wait) is consistently over 60% — the CPU is mostly idle, waiting. Cross-checking with `iostat -x 1` confirms `%util` near 90% on the disk device the worker writes temp files to. This is an **I/O-bound** workload, not a CPU-bound one — adding vCPUs would not have helped, because the bottleneck was never compute.

The actual fix: mount the temp directory on faster local storage (or skip disk entirely and resize in memory for images under a size threshold), not upgrading to a compute-optimized instance. Re-running the same test afterward should show `wa` drop and throughput rise, with `us` still comfortably below saturation.

## Core Concept 5 — Matching a Profile to an Instance Family

Cloud providers group instance types into families built around different vCPU-to-memory ratios and storage/network characteristics. The exact names vary by provider, but the shape is consistent:

| Family type | vCPU : Memory ratio (typical) | Best fit | Poor fit |
|---|---|---|---|
| **General purpose** (e.g. AWS `m`-series) | ~1 : 4 (GiB per vCPU) | Mixed workloads, unclear profile, default starting point | Workloads with a clear, extreme profile — you're paying for balance you don't need |
| **Compute-optimized** (e.g. `c`-series) | ~1 : 2 | CPU-bound: encoding, batch compute, high-throughput APIs with little state | Memory-heavy caches, large datasets in RAM |
| **Memory-optimized** (e.g. `r`-series) | ~1 : 8 | Memory-bound: in-memory caches, large working sets, analytics over big datasets | CPU-heavy compute with a small dataset |
| **Storage/IO-optimized** (e.g. `i`-series, or attaching high-IOPS volumes) | Varies | I/O-bound: high local disk throughput, databases with heavy local write load | Anything that doesn't touch local disk hard |

For the image-resizing worker above, once the fix moves the bottleneck away from disk, re-profiling might reveal it's now genuinely CPU-bound (resizing large images is compute-heavy) — at that point, a compute-optimized instance is the right move, but only *after* the I/O bottleneck is gone. Changing the instance family before fixing the actual bottleneck would have wasted a migration.

## Common Mistakes

- **Upgrading the instance without profiling first.** "It's slow, give it more CPU" is a guess. If the real bottleneck is I/O or memory, more CPU changes the bill without changing performance.
- **Confusing high CPU utilization with CPU-bound.** A CPU spinning on a busy-wait loop while waiting for a lock, or a process stuck in `%sy` handling excessive syscalls, can look "CPU-bound" in a shallow glance without actually being compute work worth buying more cores for.
- **Measuring at idle or under synthetic load that doesn't resemble production traffic.** A profile taken while nothing is happening, or under a trivial test script, tells you nothing about the real bottleneck.
- **Picking an instance family from habit rather than the profile.** Defaulting to general-purpose every time, regardless of what profiling shows, gives up the efficiency this topic is about.
- **Not re-measuring after the change.** Switching instance types without confirming the bottleneck actually moved leaves you unsure whether the change helped or just changed which resource is now underused.

## Apply it

1. Pick one service you can generate realistic load against — a background worker, a small API, or a batch job.
2. Run `top` (or `vmstat 1`) and `iostat -x 1` side by side for at least 60 seconds while the service is under representative load.
3. Classify the workload as CPU-bound, memory-bound, or I/O-bound using the table in Core Concept 1, citing the specific column and value that led you there.
4. Using the family table in Core Concept 5, name the instance family that matches your classification, and say specifically why the current one is or isn't a match.
5. If you can safely test it, move the workload to the matching instance family (or a comparable local resource limit) and re-run the same measurement to confirm the bottleneck moved or shrank.

## Verify your work

- You can point to a specific number (a `%wa` value, a `si`/`so` rate, a `%util` figure) that justifies your classification — not a general impression of "it feels slow."
- The instance family you chose is justified by the vCPU-to-memory ratio it offers, not by "it's the next size up."
- A second measurement, taken after any change, shows the previously-saturated resource with more headroom.
- You can explain in one sentence why a *different* instance family would have been the wrong choice for this workload.

## Review questions

- What is the difference between a workload being CPU-bound and a workload merely showing high CPU utilization?
- Which `vmstat` or `iostat` column would you check first to confirm a workload is I/O-bound, and what value would confirm it?
- Why would adding more vCPUs fail to fix a workload that is actually memory-bound?
- Why does re-measuring after switching instance types matter, rather than trusting the switch worked?
