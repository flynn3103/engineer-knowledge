# Dynamic Instrumentation & eBPF — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Dynamic Instrumentation & eBPF** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Dynamic Instrumentation & eBPF Roadmap](README.md)
> **Focus:** Master the eBPF programming model end to end — program types and attach points, maps as the data plane, CO-RE/BTF portability, the verifier as a hard safety net, and the judgment to drop a production-safe bpftrace one-liner into a live incident when the failure is an unknown-unknown you never pre-instrumented.

---

## Core Concepts

### 1. A program is bytecode the kernel proves safe before it runs

You never hand the kernel native code. You hand it BPF bytecode plus relocations. The verifier walks every reachable path, tracks the type and bounds of every register, and rejects anything it can't prove safe. Acceptance is a *proof*, not a heuristic — this is the foundation of running it in production.

### 2. Maps are the only state and the only channel

A BPF program has no malloc, no globals beyond maps, and no syscalls. All persistent state and all communication with user space goes through maps: hashes, arrays, per-CPU variants, ring buffers, stack-trace maps, LRU hashes. Designing a tool is mostly designing its maps.

### 3. The attach point determines what you can see

A tracepoint gives you a stable, documented argument struct. A kprobe gives you raw registers at an arbitrary instruction. An fentry gives you typed function arguments via a trampoline. The same question ("how long does `vfs_read` take?") has different fidelity and cost depending on the hook.

### 4. Aggregate in the kernel, ship summaries

The performance win is doing the reduction (count, histogram, stack-ID aggregation) in kernel space and emitting only the result. Per-event streaming to user space is the expensive path; reserve it for events rare enough to afford it.

### 5. Portability is a load-time concern, not a compile-time one

CO-RE means the *same* compiled object runs on many kernels because field offsets and existence are patched at load time from the target's BTF. This is what makes a single binary shippable across a fleet.

### 6. Privilege is now granular

Pre-5.8, tracing meant root. With `CAP_BPF` + `CAP_PERFMON` you grant exactly the tracing capability and nothing else — material for least-privilege agents.

## The eBPF Programming Model

Three pieces compose every tool:

**Program types** (`BPF_PROG_TYPE_*`) define the execution context and the helper allowlist. `BPF_PROG_TYPE_KPROBE` gets a `pt_regs *`; `BPF_PROG_TYPE_TRACING` (fentry/fexit) gets typed args; `BPF_PROG_TYPE_PERF_EVENT` fires on counter overflow (the basis of profiling); `BPF_PROG_TYPE_RAW_TRACEPOINT` is a low-overhead tracepoint. In libbpf you rarely name the enum — the `SEC("...")` annotation selects it.

**Attach points** are where the program binds. Tracepoints (`tp/...`, `tp_btf/...`) are stable kernel ABI. kprobes attach to any kernel symbol but offer no ABI stability. fentry/fexit attach to function entry/return via a BTF trampoline. perf events attach to hardware/software counters or `perf_event_open`-style sampling.

**Maps are the data plane.** The program writes; user space reads (or vice versa). Choosing the map *is* the design: a histogram is a `PERCPU_ARRAY` of log2 buckets; a "who called this most" tally is a `HASH` keyed by comm or PID; a per-flow table is a `LRU_HASH` so it self-bounds; an event stream is a `RINGBUF`.

## fentry/fexit vs kprobe/kretprobe

kprobes work everywhere (4.x kernels) but pay a cost: they trap via a breakpoint/INT3 mechanism, hand you raw `pt_regs`, and offer zero type safety — you decode arguments by ABI calling convention and pray the signature didn't change. kretprobes also consume a limited pool of return-probe slots and add entry+exit overhead.

fentry/fexit (5.5+, needs BTF) attach a **trampoline** directly at function entry/return. They are faster (no breakpoint trap), type-safe (real argument types from BTF), and `fexit` can read *both* arguments and the return value in one probe — kretprobe cannot see the original arguments without a paired kretprobe juggling a map.

```bash
# fentry: typed, fast, modern
bpftrace -e 'fentry:vfs_read { @[comm] = count(); }'

# equivalent kprobe: works on older kernels, raw, slower
bpftrace -e 'kprobe:vfs_read { @[comm] = count(); }'

# fexit sees args AND retval together:
bpftrace -e 'fexit:vfs_read { @bytes = hist(retval); }'
```

Rule of thumb: prefer fentry/fexit when BTF is present (5.5+); fall back to kprobe for portability or for symbols without a stable BTF function entry.

## CO-RE and BTF — Compile Once, Run Everywhere

The portability problem: kernel struct layouts change between versions. `task_struct->pid` lives at a different byte offset on 5.4 vs 6.6. The old BCC approach embedded a Clang compiler and compiled the program *on the target* against its headers — heavyweight, fragile, and impossible on a stripped box.

CO-RE solves it with **BTF relocations**. You compile once against `vmlinux.h` (the full kernel type universe dumped from BTF). When you access `task->pid`, the compiler emits a *relocation* rather than a fixed offset. At load time, libbpf reads the **target kernel's** BTF from `/sys/kernel/btf/vmlinux` and rewrites the offset to match. The same `.o` runs across the fleet.

`BPF_CORE_READ()` is the CO-RE-aware accessor: it issues `bpf_probe_read_kernel` with relocatable offsets and chases pointers safely:

```c
// reads task->mm->owner->comm with per-hop relocations + safe kernel reads
char comm[16];
BPF_CORE_READ_INTO(&comm, task, comm);
struct mm_struct *mm = BPF_CORE_READ(task, mm);
```

Generate `vmlinux.h` once: `bpftool btf dump file /sys/kernel/btf/vmlinux format c > vmlinux.h`. This is why CO-RE tools ship as a single small binary with no kernel headers attached.

## The Verifier as Your Safety Net

The verifier is what lets you point this at production. It rejects the program *before* it runs unless it can prove safety along every path:

- **Bounded loops only.** Pre-5.3 no loops at all (you unrolled with `#pragma unroll`). 5.3+ allows loops the verifier can prove terminate; `bpf_loop()` (5.17+) gives a clean bounded-iteration helper.
- **1 million instruction complexity limit.** The verifier explores paths; total complexity (not source lines) is capped. Deep nesting or unbounded pointer walks blow the budget. Tail calls split work across programs to stay under it.
- **512-byte stack.** No large on-stack buffers. Big scratch space goes in a per-CPU array map.
- **Helper allowlist per program type.** You can only call the helpers permitted for your program type. No arbitrary kernel calls (kfuncs are the typed, sanctioned exception).
- **No uninitialized reads, no out-of-bounds, no unchecked pointer deref.** Every memory access must be provably in bounds; every kernel pointer must be read through `bpf_probe_read_kernel`/`BPF_CORE_READ`.

Why this beats a kernel module: a buggy module panics the box. A buggy BPF program is *rejected at load* with a verifier log pointing at the offending instruction. The cost of that safety is a restricted language — and learning to read `bpftool prog load` verifier output is a core senior skill.

## Ring Buffers vs Perf Buffers

Both stream variable-length events to user space. Prefer the **ring buffer** on 5.8+.

| | Perf buffer (`PERF_EVENT_ARRAY`) | Ring buffer (`RINGBUF`) |
|---|---|---|
| Topology | Per-CPU buffers | Single shared MPSC buffer |
| Ordering | Per-CPU only | Global event ordering |
| Memory | N × per-CPU (often over-provisioned) | One sized buffer (power of two pages) |
| Overhead | Higher; copy + per-CPU wakeups | Lower; reserve/commit, fewer wakeups |
| API | `bpf_perf_event_output` | `bpf_ringbuf_reserve` + `bpf_ringbuf_submit` |

The ring buffer's `reserve`/`submit` is also nicer: you reserve space, fill it in place (no double copy), then submit. If a downstream consumer is slow, you can `bpf_ringbuf_discard` instead of submit and drop the event cleanly rather than corrupting the stream.

## A Minimal libbpf CO-RE Tool

Two files: the kernel program (`.bpf.c`) and the user-space loader. Annotated.

**`openat.bpf.c`** — kernel side:

```c
#include "vmlinux.h"            // all kernel types, from BTF — no kernel headers needed
#include <bpf/bpf_helpers.h>
#include <bpf/bpf_core_read.h>

char LICENSE[] SEC("license") = "GPL";

struct event {                  // what we ship to user space
    __u32 pid;
    char  comm[16];
    char  fname[128];
};

struct {                        // the data plane: a 256 KiB ring buffer
    __uint(type, BPF_MAP_TYPE_RINGBUF);
    __uint(max_entries, 256 * 1024);
} rb SEC(".maps");

SEC("tp/syscalls/sys_enter_openat")          // stable tracepoint = stable ABI
int handle_openat(struct trace_event_raw_sys_enter *ctx)
{
    struct event *e = bpf_ringbuf_reserve(&rb, sizeof(*e), 0);
    if (!e)                                   // verifier forces the NULL check
        return 0;

    e->pid = bpf_get_current_pid_tgid() >> 32;
    bpf_get_current_comm(&e->comm, sizeof(e->comm));
    // args[1] is the const char *filename for openat
    bpf_probe_read_user_str(&e->fname, sizeof(e->fname),
                            (const char *)ctx->args[1]);

    bpf_ringbuf_submit(e, 0);                 // or bpf_ringbuf_discard(e, 0)
    return 0;
}
```

**User-space loader** (sketch), using the generated skeleton `openat.skel.h`:

```c
#include "openat.skel.h"
#include <bpf/libbpf.h>

static int on_event(void *ctx, void *data, size_t len) {
    struct event *e = data;
    printf("%-6d %-16s %s\n", e->pid, e->comm, e->fname);
    return 0;
}

int main(void) {
    struct openat_bpf *skel = openat_bpf__open_and_load(); // CO-RE relocs happen here
    openat_bpf__attach(skel);                              // attach the tracepoint

    struct ring_buffer *rb =
        ring_buffer__new(bpf_map__fd(skel->maps.rb), on_event, NULL, NULL);

    while (ring_buffer__poll(rb, 100 /*ms*/) >= 0) { }     // drain events

    ring_buffer__free(rb);
    openat_bpf__destroy(skel);
}
```

`open_and_load` is where CO-RE earns its name: libbpf reads the target's BTF and patches every relocatable field access. You ship one `.o` (embedded in the skeleton) and it runs on any 5.8+ kernel with BTF — no per-kernel headers, no on-target Clang.

## Production-Safe Dynamic Tracing

The discipline that makes this acceptable on a customer's box:

- **Reason about overhead before attaching.** Cost ≈ (event rate) × (per-probe work). A probe on `tcp_retransmit_skb` fires rarely — essentially free. A probe on `sys_enter_read` at 300k/s is *not* free; scope it or aggregate hard.
- **Scope by target.** Filter by PID, cgroup, comm, or device in the probe body so you only pay for the events you care about: `kprobe:vfs_read /pid == 4242/ { ... }`.
- **Time-box it.** Never leave an ad-hoc probe attached. Use a `timeout`, `interval` with `exit()`, or a wrapping `timeout 30 bpftrace ...`.
- **Privileges:** prefer `CAP_BPF` + `CAP_PERFMON` (5.8+) over root. Grant the tracing agent exactly these caps; it can load and trace but cannot, say, load network-attached XDP that reroutes traffic (`CAP_NET_ADMIN` is separate).
- **Locked-down kernels block you.** Secure Boot / kernel **lockdown mode** (`integrity`/`confidentiality`) disables kprobes and `bpf_probe_read` on many fields; missing `CONFIG_DEBUG_INFO_BTF` kills CO-RE and fentry. Know this *before* the incident.
- **Prefer aggregation over streaming** in prod; a histogram is cheap, a per-event ring buffer at high rate is not.

## When to Reach for bpftrace in an Incident

Pre-instrumentation (metrics, spans, logs) answers questions you anticipated. The incidents that page you at 3am are, by selection, the ones you *didn't* anticipate — the unknown-unknown. bpftrace is the tool for those, because you can ask a brand-new question of a running, unmodified process or kernel in seconds.

A realistic walk-through. Symptom: p99 request latency jumped 10×, but CPU is flat, all app spans look normal, and there's no error log. The app spans being normal is the tell — the time is being spent *outside* what the app instrumented. So you go below the app:

```bash
# 1. Is the process off-CPU (blocked), not on-CPU (busy)?
sudo bpftrace -e '
  kprobe:finish_task_switch {
    $prev = (struct task_struct *)arg0;
    @off[$prev->comm] = sum(nsecs - @start[$prev->pid]);
  }
  tracepoint:sched:sched_switch { @start[args->prev_pid] = nsecs; }
  interval:s:10 { exit(); }'
```

Off-CPU time for the app process dominates — it's *waiting*, not computing. Now: waiting on what? Aggregate the off-CPU stacks to see where it blocks:

```bash
sudo bpftrace -e '
  kprobe:finish_task_switch /comm == "api-server"/ {
    @[kstack] = sum(nsecs - @s[tid]); delete(@s[tid]);
  }
  tracepoint:sched:sched_switch /args->prev_comm == "api-server"/ {
    @s[args->prev_pid] = nsecs;
  }
  interval:s:30 { exit(); }'
```

The top stack points into TCP retransmit / `tcp_write_xmit`. Confirm with a retransmit tracer and you have your answer — packet loss to a downstream is stalling sends. None of this was pre-instrumented; you discovered it live.

## Code Examples

```bash
# 1. fentry one-liner: count vfs_read callers by command (typed, fast)
sudo bpftrace -e 'fentry:vfs_read { @[comm] = count(); }'

# 2. Off-CPU time by stack (where is the app blocking?)
sudo bpftrace -e '
  tracepoint:sched:sched_switch { @start[args->prev_pid] = nsecs; }
  kprobe:finish_task_switch /@start[tid]/ {
    @offcpu_ns[kstack] = sum(nsecs - @start[tid]); delete(@start[tid]);
  }'

# 3. Flame-graph-friendly on-CPU stack aggregation (folded output)
sudo bpftrace -e 'profile:hz:99 { @[kstack, ustack, comm] = count(); }' \
  | ./stackcollapse-bpftrace.pl | ./flamegraph.pl > cpu.svg

# 4. TCP retransmits, two ways
sudo tcpretrans-bpfcc                                   # BCC tool, ready-made
sudo bpftrace -e 'kprobe:tcp_retransmit_skb {
    @retrans[comm] = count(); printf("retrans %s\n", comm); }'

# 5. Syscall latency histogram via fexit (args + retval in one probe)
sudo bpftrace -e '
  fentry:do_sys_openat2 { @ts[tid] = nsecs; }
  fexit:do_sys_openat2 /@ts[tid]/ {
    @us = hist((nsecs - @ts[tid]) / 1000); delete(@ts[tid]); }'
```

```c
// 6. libbpf CO-RE snippet: read task fields portably with BPF_CORE_READ
struct task_struct *task = (struct task_struct *)bpf_get_current_task();
pid_t ppid = BPF_CORE_READ(task, real_parent, tgid);   // relocatable offsets
__u64 start = BPF_CORE_READ(task, start_time);          // patched at load time
```

## Worked Example — Catching an Unforeseen Bug Live

Production, payments service, SEV-2. Symptom: ~1% of requests time out at 5s. Dashboards: CPU normal, GC normal, DB query metrics normal, app traces show the *handler* finishing in 4ms — yet the client sees 5s. The trace ends; the wall clock doesn't. The gap is between "handler returns the response object" and "bytes leave the box."

Step 1 — confirm the process is blocked, not busy:

```bash
sudo bpftrace -e '
  kprobe:finish_task_switch /comm == "pay-svc"/ {
    @off[ustack] = sum(nsecs - @s[tid]); delete(@s[tid]); }
  tracepoint:sched:sched_switch /args->prev_comm == "pay-svc"/ {
    @s[args->prev_pid] = nsecs; }
  interval:s:20 { exit(); }'
```

Dominant off-CPU stack: blocked in `futex` inside the connection-pool's lock. The handler finishes fast, but the *response writer* contends on a pool mutex held by a slow path.

Step 2 — who holds it that long? Trace lock hold time:

```bash
sudo bpftrace -e '
  uprobe:/app/pay-svc:pool_lock   { @h[tid] = nsecs; }
  uprobe:/app/pay-svc:pool_unlock /@h[tid]/ {
    @hold_ms = hist((nsecs - @h[tid]) / 1000000); delete(@h[tid]); }'
```

A long tail at 5000ms. The lock holder is doing a *synchronous DNS resolve* (the rare cache-miss path) **inside** the critical section — invisible to app metrics because DNS wasn't instrumented and the median path never blocked.

Step 3 — confirm the DNS theory cheaply:

```bash
sudo bpftrace -e 'kprobe:tcp_retransmit_skb { @[comm] = count(); }'   # rule out network
sudo bpftrace -e 'kprobe:__inet_lookup_established { } ; uprobe:/lib/x86_64-linux-gnu/libc.so.6:getaddrinfo { @gai[comm] = count(); }'
```

`getaddrinfo` calls correlate exactly with the slow requests. Fix: move resolution out of the lock and add a resolver cache. The entire diagnosis used probes attached to an unmodified production binary; nothing was redeployed until the fix.

## Coding Patterns

- **Map-per-concept:** one map for in-flight timestamps keyed by tid, one for the aggregated histogram/stack tally.
- **Entry/exit timing:** stash `nsecs` at entry keyed by `tid`, compute delta at exit, `delete()` the entry to bound the map.
- **Stack-ID aggregation:** store stack IDs into a `STACK_TRACE` map and tally by ID; resolve symbols in user space once.
- **LRU for unbounded keyspaces:** use `BPF_MAP_TYPE_LRU_HASH` for per-flow/per-PID tables so a busy box can't exhaust the map.
- **Tail calls for big logic:** split a program exceeding the complexity budget across a prog array.

## Clean Usage

- Always check `bpf_ringbuf_reserve()` for NULL; the verifier requires it and a dropped event is better than a stall.
- `delete()` transient map entries to prevent unbounded growth.
- Filter (`/pred/`) as early as possible to minimize per-event work.
- Resolve symbols and format strings in user space, not in the probe.
- Prefer tracepoints over kprobes for ABI stability; prefer fentry over kprobe for speed where BTF exists.

## Best Practices

- Estimate event rate × cost before attaching anything in prod; scope and time-box.
- Ship libbpf CO-RE tools, not BCC-compile-on-target, for production agents.
- Keep `vmlinux.h` regenerated from the target BTF; never hand-edit kernel types.
- Run agents under `CAP_BPF`+`CAP_PERFMON`, not blanket root.
- Test on the *oldest and newest* kernels in your fleet — CO-RE handles offsets, not removed fields.
- Treat bpftrace as a scalpel for hypotheses, libbpf for the durable tool you keep.

## Edge Cases & Pitfalls

- **Missing BTF:** no CO-RE, no fentry — fall back to kprobes and on-target compilation, or build BTF with the `BTFhub` archive.
- **Lockdown mode** silently blocks `bpf_probe_read` of certain fields; symptom is empty/zero reads, not an error.
- **Inlined functions** have no kprobe/fentry target; the symbol exists in source but not as a callable entry.
- **kretprobe slot exhaustion** under high concurrency drops return events — another reason to prefer fexit.
- **Per-CPU map aggregation** must be summed across CPUs in user space; reading one CPU's value undercounts.
- **High-rate ring buffer** can drop events; check the dropped counter and consider sampling.

## Common Mistakes

- Attaching an unscoped probe to a hot path (`sys_enter_read`) in prod and adding measurable latency.
- Forgetting to `delete()` entry timestamps — the map grows until it's full and silently drops new entries.
- Reading kernel memory with a raw deref instead of `BPF_CORE_READ`/`bpf_probe_read_kernel` (rejected, or worse, non-portable).
- Assuming a one-liner from a blog matches your kernel version's symbol names — `tcp_retransmit_skb` vs `tcp_retransmit_skb` argument shapes vary.
- Treating eBPF as a substitute for application metrics; it sees syscalls and kernel state, not your business logic.
- Leaving a probe attached after the incident.

## Tricky Points

- A program "passing the verifier" means *safe*, not *correct* — your aggregation logic can still be wrong.
- fentry can't attach to a function the compiler inlined; the fix is a different (often parent) hook.
- CO-RE relocates offsets but cannot conjure a field that doesn't exist on the target kernel; guard with `bpf_core_field_exists()`.
- Ring buffer ordering is global, but timestamps from different CPUs need a monotonic clock to compare meaningfully.
- `comm` is 16 bytes including the NUL — long process names are truncated, which can collide in tallies.

---

## Apply it

1. State the system invariant that **Dynamic Instrumentation & eBPF** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Dynamic Instrumentation & eBPF fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
