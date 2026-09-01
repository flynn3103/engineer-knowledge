# Dynamic Instrumentation & eBPF — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Dynamic Instrumentation & eBPF** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Dynamic Instrumentation & eBPF Roadmap](README.md)
> **Focus:** How eBPF actually works — the VM, the verifier, maps, and ring/perf buffers. Reading and writing real bpftrace programs (not just one-liners) and BCC tools. Capturing function arguments and return values. USDT in the JVM and Python. The entry/return latency pattern, per-process scoping, and tracing your own service in production without making it worse.

---

## Core Concepts

### 1. Your program is verified *before* it ever runs

Unlike a kernel module — which the kernel trusts blindly and which can panic the box — an eBPF program must *prove* its safety to the verifier first. This is the central bargain: you accept real constraints (bounded loops, limited stack, no arbitrary memory access) in exchange for being allowed to run code in the kernel of a production machine.

### 2. Aggregating in-kernel is cheap; streaming to user-space is not

Every design decision flows from this. `count()`/`hist()`/`sum()` update a kernel map and never leave the kernel until you stop. `printf`/per-event records traverse a ring or perf buffer into user-space — orders of magnitude more work per event. On a hot path, that difference is the whole ballgame.

### 3. Arguments and return values are where the *insight* lives

"`do_sys_openat2` was called 4,000 times" is a number. "`do_sys_openat2` was called with `/etc/shadow` and returned `-EACCES`" is an *answer*. Capturing `args`/`arg0`/`retval` is the step from counting to understanding.

### 4. Match entry to return by thread, and clean up

Latency = `return_time − entry_time`. Store the entry timestamp keyed by **`tid`** (threads of one process can be in the same function simultaneously), read it on return, then **`delete()`** it. Forgetting the delete leaks map entries; forgetting that a function might *not* return leaves stale entries forever.

### 5. Stable hooks are an engineering decision, not a preference

A kprobe on an internal function is a tool you accept will break on the next kernel. A tracepoint or USDT probe is a *contract*. For a one-off incident, the kprobe is fine. For a tool you'll ship and rely on, choose the stable hook or use **CO-RE** (senior level) so it survives upgrades.

---

## How eBPF Runs Your Code

The pipeline, end to end:

```
  bpftrace text / C source
        │  compile
        ▼
  eBPF bytecode  ──▶  [ VERIFIER ]  ──reject──▶  error, nothing runs
        │  accept
        ▼
     [ JIT ]  ──▶  native machine code
        │  attach to probe(s)
        ▼
  EVENT FIRES ──▶ your code runs in kernel context ──▶ writes to MAPS
                                                          │
                          user-space reads maps / drains ring buffer
```

Three things to internalize:

1. **The verifier runs once, at load time** — not per event. Its cost is paid up front; the attached program then runs at native speed.
2. **The program runs in restricted kernel context** — it can't sleep arbitrarily, can't call most kernel functions, and has a tiny (512-byte) stack. That's why state lives in maps, not local variables.
3. **The probe is the trigger, the program is the payload, the map is the result.** Everything you do is some arrangement of those three.

---

## The Verifier, Concretely

The verifier is the feature that makes production eBPF possible. It walks every possible path through your program and rejects anything it can't prove safe. The constraints you'll actually hit:

- **No unbounded loops.** Early eBPF banned loops entirely; modern kernels allow *bounded* loops the verifier can prove terminate. An infinite loop = rejection (it would hang the kernel).
- **Every memory access must be provably in-bounds.** Reading a map value or a packet requires a NULL/bounds check the verifier can see. This is why BCC code is littered with `if (val == NULL) return 0;`.
- **Pointer arithmetic is tracked.** You can't fabricate a pointer to arbitrary kernel memory; the verifier knows the provenance of every pointer.
- **Instruction budget.** Programs over the complexity limit are rejected — the verifier must finish analyzing in finite time.

A typical rejection, paraphrased from a real BCC error:

```
; val = bpf_map_lookup_elem(&counts, &key);
invalid mem access 'map_value_or_null'
```

Translation: *you looked up a map entry and used the result without checking it for NULL.* The lookup can return NULL (key absent), and dereferencing NULL in the kernel is a panic, so the verifier refuses. The fix is the check the verifier is demanding:

```c
u64 *val = bpf_map_lookup_elem(&counts, &key);
if (!val) return 0;       // <-- the verifier wanted this proof
(*val)++;
```

> **Mental reframe:** the verifier is not in your way; it found a path where your code *could* have crashed a production kernel and is making you handle it. Every rejection is a bug you didn't ship.

---

## Maps and Buffers — The Data Plane

eBPF programs are stateless between firings *except* for maps. Maps are how state survives across events and how data crosses into user-space.

**Common map types you'll meet:**

| Type | Use |
|---|---|
| `HASH` | General key→value, e.g. `@start[tid]`. |
| `PERCPU_HASH/ARRAY` | High-frequency counters with no lock contention; summed on read. |
| `LRU_HASH` | Bounded hash that evicts oldest entries — caps memory automatically. |
| `STACK_TRACE` | Stores stacks for flame-graph-style aggregation. |

**Two ways to get *individual events* out to user-space:**

- **Perf buffer** — the classic mechanism; one buffer per CPU, can drop and reorder under load.
- **Ring buffer** (`BPF_MAP_TYPE_RINGBUF`, kernel 5.8+) — one shared buffer, preserves ordering, lower overhead, simpler API. **Prefer it** when available.

The decision that matters: **do you need every event, or a summary?** If a summary (counts, histograms, top-N), keep it in a map and never use a buffer — far cheaper. Use a ring buffer only when you genuinely need each event's detail in user-space.

---

## Probe Selection in Practice

The junior rule was "stable if it exists." Mid-level, you weigh it deliberately:

| Question | Choice |
|---|---|
| Kernel behavior, stable hook exists? | **tracepoint** (`bpftrace -l 'tracepoint:*'` to find it) |
| Kernel function, no tracepoint? | **kprobe/kretprobe** — accept it may break on upgrade |
| App behavior, author shipped a marker? | **USDT** (`bpftrace -l 'usdt:/path/to/bin'`) |
| Your own function, no USDT? | **uprobe/uretprobe** by symbol name |
| Need a periodic sample, not an event? | **`profile:hz:99`** or `interval:s:1` |

A subtlety: **syscall tracepoints come in `sys_enter_X` / `sys_exit_X` pairs.** Arguments live on `sys_enter`; the return code lives on `sys_exit`. To capture both you attach to both and join by `tid`.

---

## Capturing Arguments and Return Values

This is the mid-level superpower. The accessors:

- **Tracepoints:** named fields via `args->field` (discover them with `bpftrace -lv 'tracepoint:...'`).
- **kprobes/uprobes:** positional `arg0`, `arg1`, … (from registers; you must know the function's signature).
- **kretprobes/uretprobes:** `retval`.

```bash
# openat() arguments AND result, joined by thread id
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_openat { @fn[tid] = str(args->filename); }
tracepoint:syscalls:sys_exit_openat /@fn[tid]/ {
    printf("%-16s open(%s) = %d\n", comm, @fn[tid], args->ret);
    delete(@fn[tid]);
}'
```

This shows *which file* each process tried to open *and whether it succeeded* (`= -13` is `-EACCES`). That single line answers "who is failing to open what, and why" — a question no pre-shipped log would have anticipated.

---

## USDT in the JVM and Python

USDT probes are author-placed markers that survive upgrades and carry meaning. Two big runtimes ship them.

**JVM** (built/run with USDT enabled — `-XX:+ExtendedDTraceProbes` or a probe-enabled build):

```bash
# List the HotSpot probes a running JVM exposes
sudo bpftrace -l 'usdt:/usr/lib/jvm/java-17-openjdk/lib/server/libjvm.so:*'

# Count GC pauses by trigger
sudo bpftrace -e 'usdt:/.../libjvm.so:hotspot:gc__begin { @gc = count(); }'
```

**CPython** (built `--with-dtrace`):

```bash
# Trace Python function entries with module + function name
sudo bpftrace -e '
usdt:/usr/bin/python3:python:function__entry {
    printf("%s:%s\n", str(arg1), str(arg2));
}'
```

USDT gives you semantically meaningful events ("a GC started," "a Python function was entered") that a raw uprobe on `libjvm` internals never could — and they don't break when the runtime is patched.

---

## Code Examples

### 1. Syscall latency by syscall name (top offenders)

```bash
sudo bpftrace -e '
tracepoint:raw_syscalls:sys_enter { @start[tid] = nsecs; }
tracepoint:raw_syscalls:sys_exit /@start[tid]/ {
    @ns[probe] = sum(nsecs - @start[tid]);
    delete(@start[tid]);
}'
```

### 2. Per-process read-latency histogram (your service)

```bash
sudo bpftrace -e '
kprobe:vfs_read /comm == "myservice"/ { @s[tid] = nsecs; }
kretprobe:vfs_read /@s[tid]/ {
    @us = hist((nsecs - @s[tid]) / 1000);   // microseconds
    delete(@s[tid]);
}'
```

### 3. uprobe with arguments on your own binary

```bash
# Suppose handleRequest(int routeId, char *path)
sudo bpftrace -e '
uprobe:./myapp:handleRequest { printf("route=%d path=%s\n", arg0, str(arg1)); }'
```

### 4. Capture user + kernel stack on slow reads

```bash
sudo bpftrace -e '
kretprobe:vfs_read /(nsecs - @s[tid]) > 10000000/ {
    @slow[ustack, kstack] = count();
}'
```

### 5. A minimal BCC program (Python front-end, C kernel side)

```python
from bcc import BPF

prog = r"""
BPF_HASH(counts, u32);            // a map keyed by PID

TRACEPOINT_PROBE(syscalls, sys_enter_openat) {
    u32 pid = bpf_get_current_pid_tgid() >> 32;
    u64 zero = 0, *val;
    val = counts.lookup_or_try_init(&pid, &zero);
    if (val) (*val)++;            // verifier-mandated NULL check
    return 0;
}
"""

b = BPF(text=prog)
print("Tracing openat()... Ctrl-C to end.")
try:
    b.trace_print()              # not used; we read the map below
except KeyboardInterrupt:
    pass
for k, v in sorted(b["counts"].items(), key=lambda kv: kv[1].value):
    print(f"pid={k.value:6d}  opens={v.value}")
```

Note the `if (val)` guard — that's the verifier's NULL-check requirement, in real code.

### 6. Find what's exec'ing (the readable, scoped version)

```bash
sudo bpftrace -e '
tracepoint:syscalls:sys_enter_execve {
    printf("%-8d %-16s %s\n", pid, comm, str(args->filename));
}'
```

---

## bpftrace vs BCC vs libbpf

| | **bpftrace** | **BCC** | **libbpf + CO-RE** |
|---|---|---|---|
| Form | one-liners / short scripts | Python (or C++) + C kernel code | C, compiled to a portable object |
| Best for | ad-hoc investigation | custom tools, prototyping | production-grade, shippable tools |
| Compiles on target? | yes (needs headers/BTF) | yes (ships LLVM/Clang) | **no** — compile once, run everywhere |
| Startup cost | seconds | seconds (compiles at runtime) | instant (already compiled) |
| Where you'll meet it | incidents | bcc-tools (`execsnoop` etc.) | distributed agents (senior level) |

The progression mirrors maturity: **bpftrace to find the answer, BCC to prototype a tool, libbpf+CO-RE to ship it.** The senior level covers CO-RE in depth.

---

## Coding Patterns

- **Enter/exit join by `tid`** for any "what happened across a call" question; always `delete()`.
- **Per-CPU maps for hot counters** to avoid lock contention; bpftrace's built-in aggregations already do this.
- **Predicate early** (`/comm == "x"/`, `/pid == $1/`) so expensive work only runs for your target.
- **Aggregate by stack** (`@[ustack] = count()`) to turn raw events into a ranked culprit list.
- **Use `lookup_or_try_init` in BCC** and check the result — it satisfies the verifier and avoids races.

---

## Clean Usage

- **Pass the PID as an argument** (`bpftrace script.bt 1234`, read with `$1`) instead of hardcoding.
- **Name maps for their contents and units** — `@read_us`, not `@`.
- **Keep one-liners as files once they grow past a line** — `.bt` files are readable and reusable.
- **Comment the function signature** above any `arg0`/`arg1` use, so the next person knows what the positions mean.

---

## Best Practices

- **Estimate event frequency before attaching.** A probe on `sys_enter` (every syscall) needs a cheap action; a probe on your once-per-request handler can afford more.
- **Aggregate in-kernel; reach for a ring buffer only for genuine per-event needs.**
- **Prefer the ring buffer over the perf buffer** on 5.8+ kernels.
- **Confirm the symbol/probe exists** with `bpftrace -l` before relying on a kprobe/uprobe.
- **Trace in production with a target filter and a time limit**, and watch the box's own load while you do.

---

## Edge Cases & Pitfalls

- **`sys_enter`/`sys_exit` argument mismatch** — arguments are on enter, return code on exit; people attach to the wrong one and get nulls.
- **uprobe on an inlined/optimized function** — the symbol may not exist or may fire at unexpected times; `-O2` can inline your target away.
- **Dropped events under load** — perf buffers drop; if counts look low, you may be losing events, not seeing fewer.
- **USDT not present** because the runtime wasn't built with it (`--with-dtrace`, JVM probe build) — the probe simply won't list.
- **`str()` length limits** — bpftrace truncates strings at a fixed size; long paths get cut.

---

## Common Mistakes

- **Doing `printf` per event on a hot probe** and slowing the box you're trying to diagnose.
- **Keying enter/exit maps by `pid`** and corrupting timing when threads overlap — use `tid`.
- **Not NULL-checking a BCC map lookup** and getting a verifier rejection (or worse, on old kernels, a crash).
- **Assuming a kprobe is portable** — shipping a tool built on kprobes that breaks on the customer's kernel.
- **Forgetting `delete()`** and slowly leaking map entries on a long-running trace.

---

## Tricky Points

- **`profile:hz:99` vs an event probe.** Profiling samples at a fixed rate regardless of events — great for "where is CPU going," useless for "what happened on this syscall."
- **A kretprobe sees `retval`, but not the args** — the arguments are gone by return time. Stash them on entry if you need both.
- **Per-CPU map reads are summed**, so a single key can appear to "jump" as different CPUs are aggregated — expected, not a bug.
- **USDT probe arguments are positional and typed by the author** — read the runtime's probe documentation; `arg1`/`arg2` meaning varies per probe.

---

## Apply it

1. Find a real component where **Dynamic Instrumentation & eBPF** affects an interface or dependency.
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

- Which boundary is most affected by Dynamic Instrumentation & eBPF?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
