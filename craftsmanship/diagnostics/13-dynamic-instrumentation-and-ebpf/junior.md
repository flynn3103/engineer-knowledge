# Dynamic Instrumentation & eBPF — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Dynamic Instrumentation & eBPF** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Dynamic Instrumentation & eBPF Roadmap](README.md)
> **Focus:** What "attach a probe to a running program" actually means, and why it's different from logging. The four probe families — kprobe, uprobe, tracepoint, USDT. Your first real bpftrace one-liners and BCC tools, run against a live system. When dynamic tracing is the right tool and when it absolutely is not.

---

## Core Concepts

### 1. You attach the question *after* the program is already running

This is the whole shift. A log line exists because someone wrote it months ago. A probe exists because *you* attached it thirty seconds ago to a process you didn't write and can't restart. The program has no idea it's being watched.

### 2. A probe is "an event + code that runs when the event fires"

Every bpftrace line has two parts: a **probe specification** (which event — `tracepoint:syscalls:sys_enter_openat`) and an **action** in `{ }` (what to do when it fires — `@[comm] = count()`). That's the entire mental model. The kernel runs your action each time the event happens.

### 3. eBPF runs your code *inside* the kernel, safely

Your action doesn't run in your shell — it's compiled to eBPF bytecode, verified, and run in the kernel at the moment the event fires. That's why it's fast (no copying every event out to user-space) and why it needs the verifier (kernel code that misbehaves takes the whole machine down).

### 4. Prefer the stable hook over the clever one

You can kprobe almost any kernel function, but kernel functions get renamed between versions. **Tracepoints** and **USDT** probes are *contracts* the maintainers promise to keep. When a tracepoint exists for what you want, use it — your one-liner will still work after the next kernel upgrade.

### 5. This is a complement to logs/metrics/traces, not a replacement

Dynamic tracing is for **ad-hoc, unforeseen questions** during investigation. You would never replace your request counter with a uprobe — the probe is expensive to keep running forever and disappears on reboot. Static instrumentation is your always-on dashboard; dynamic instrumentation is the flashlight you grab when the dashboard isn't enough.

---

## Dynamic vs Static Instrumentation

| | **Dynamic (probes / eBPF)** | **Static (logs / metrics / traces)** |
|---|---|---|
| **Decided when?** | At investigation time, on a live system | Ahead of time, in source code |
| **Needs redeploy?** | No | Yes, to add anything new |
| **Answers unforeseen questions?** | Yes — its entire purpose | No — only what you pre-instrumented |
| **Lifetime** | Seconds to minutes, then detach | Always on, shipped with the build |
| **Sees kernel internals?** | Yes (kprobes, tracepoints) | Almost never |
| **Survives a reboot?** | No | Yes |
| **Cost model** | Per-event overhead while attached | Paid continuously, by design |

The one-line rule: **static tells you what you knew to ask; dynamic lets you ask something new of a system you can't touch.**

---

## The Four Probe Families

These are the four kinds of hook you'll attach to. Knowing *which* to reach for is most of the skill.

### kprobe / kretprobe — kernel functions

Attach to (almost) **any function in the kernel**, by name, at *entry* (`kprobe`) or *return* (`kretprobe`). Enormously powerful — you can watch internal kernel functions no one designed to be observable. The catch: those function names are *not* a stable API. `vfs_read` might be renamed or inlined away in a future kernel, and your probe silently stops matching.

```
kprobe:vfs_read      // fires when the kernel enters vfs_read()
kretprobe:vfs_read   // fires when vfs_read() returns (you get retval)
```

### uprobe / uretprobe — user-space functions

The same idea, but for functions in a **normal user-space binary or shared library** — your own program, `libc`, `libssl`. You point at the file on disk and the function name (or symbol address).

```
uprobe:/bin/bash:readline          // someone in any bash typed a line
uretprobe:/lib/libc.so.6:malloc    // a malloc() call returned
```

### tracepoint — stable kernel hooks

Hooks the **kernel maintainers placed and promised to keep**. They have stable names and a documented set of fields. Categories include `syscalls:`, `sched:` (scheduler), `block:` (block I/O), `net:`. **Prefer these over kprobes whenever one exists** — they survive kernel upgrades.

```
tracepoint:syscalls:sys_enter_openat   // any process called openat()
tracepoint:sched:sched_switch          // the CPU switched to another task
```

### USDT — probes baked into the app

*User Statically-Defined Tracing* probes are placed by the **application author** as dtrace-style markers. The JVM, CPython, Node.js, Postgres, and MySQL ship them. They're stable, semantically meaningful ("a GC pause started"), and zero-cost when not attached.

```
usdt:/usr/lib/jvm/.../libjvm.so:hotspot:gc__begin   // JVM GC started
usdt:/usr/bin/python3:python:function__entry        // a Python function was entered
```

> **The cheat-sheet rule:** kernel function → tracepoint if it exists, else kprobe. App function → USDT if it exists, else uprobe.

---

## Your First Probes — Code Examples

All of these need root (`sudo`) and a Linux box with bpftrace and bcc-tools installed (`apt install bpftrace bpfcc-tools` on Debian/Ubuntu).

### 1. The "hello world" of eBPF

```bash
sudo bpftrace -e 'BEGIN { printf("tracing started, hit Ctrl-C to stop\n"); }'
```

`BEGIN` is a special probe that fires once when the program starts. Nothing kernel-y yet — but you've run an eBPF program.

### 2. Count syscalls by process — the classic one-liner

```bash
sudo bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); }'
```

Every time *any* process makes *any* syscall, increment the map `@` keyed by the process name. Hit Ctrl-C and bpftrace prints a sorted table: which programs are the syscall-heavy ones, right now, on this box.

### 3. Who is opening which files?

```bash
sudo bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s -> %s\n", comm, str(args->filename)); }'
```

`args->filename` is a field of the tracepoint. `str()` reads the string from user-space memory. You now have a live feed of every file open on the system, with the process that did it.

### 4. The same answer, but with a ready-made BCC tool

You don't always need to write the one-liner — BCC ships polished tools:

```bash
sudo execsnoop-bpfcc      # every new process that gets exec()'d, live
sudo opensnoop-bpfcc      # every file open, with the result code
sudo tcpconnect-bpfcc     # every outbound TCP connection
sudo biolatency-bpfcc     # disk I/O latency as a histogram
```

Run `execsnoop-bpfcc` and then open a new terminal — you'll see your shell and every command it spawns appear instantly. This is often the fastest way to answer "what is this machine actually *doing*?"

### 5. A latency histogram — the thing that makes people gasp

```bash
sudo bpftrace -e '
kprobe:vfs_read { @start[tid] = nsecs; }
kretprobe:vfs_read /@start[tid]/ {
    @ns = hist(nsecs - @start[tid]);
    delete(@start[tid]);
}'
```

On *entry*, stash the start time in a map keyed by thread ID. On *return*, if we have a start time (`/@start[tid]/` is a filter), record the elapsed nanoseconds into a **power-of-two histogram**. Ctrl-C and bpftrace draws an ASCII histogram of read latencies — instantly visible long tail and all. This pattern — *timestamp on entry, measure on return* — is the single most useful thing in this whole page.

### 6. Trace a function in your *own* program (uprobe)

Suppose you compiled `./myapp` in Go or C with a function `handleRequest`:

```bash
sudo bpftrace -e 'uprobe:./myapp:handleRequest { @calls = count(); }'
```

No recompile, no print statements added — you're counting calls to *your* function in a *running* binary you point at on disk.

---

## What a Probe Costs

Probes are cheap, but **not free**, and the cost depends on how often the event fires.

- **A kprobe firing once per request:** negligible — nanoseconds per hit.
- **A tracepoint on `raw_syscalls:sys_enter`:** fires *constantly* (every syscall, every process). Counting is fine; doing expensive work in that action can measurably slow the box.
- **Printing per-event** (`printf`) is far more expensive than **aggregating** (`count()`, `hist()`). Per-event streaming copies data to user-space; aggregation stays in a kernel map and is summarized once at the end.

> **Rule of thumb for juniors:** prefer `count()` / `hist()` over `printf` on high-frequency probes. Aggregate in the kernel, print the summary. And never leave a heavy probe attached after you've got your answer.

---

## Coding Patterns

- **Timestamp-on-entry, measure-on-return.** Store `nsecs` in `@start[tid]` on a `kprobe`, subtract on the `kretprobe`. The basis of every latency histogram.
- **Key maps by `tid`, not `pid`,** when matching entry to return — two threads of the same process can be inside the function at once.
- **Filter with `/predicate/`** between the probe and the `{}` to scope to one PID or one condition: `tracepoint:syscalls:sys_enter_openat /pid == 1234/ { ... }`.
- **Aggregate, then print.** `@[key] = count()` or `= hist(x)`, let bpftrace print on exit.

---

## Clean Usage

- **Scope to a target.** Add `/pid == $1/` or `-p <pid>` so you trace the one process you care about, not the whole machine.
- **Name your maps for what they hold.** `@read_latency_ns` reads better in the output than `@`.
- **Always `delete()` per-thread scratch maps** after you use them, so they don't grow unbounded.
- **Detach when done.** Ctrl-C. A forgotten high-frequency probe is a tiny, permanent tax on the box.

---

## Best Practices

- **Reach for an existing BCC tool first.** `execsnoop`, `opensnoop`, `biolatency` already do the right thing safely. Write a one-liner only when no tool fits.
- **Prefer tracepoints/USDT over kprobes/uprobes** — they're stable across versions.
- **Aggregate in-kernel; stream to user-space only when you must.**
- **Check your kernel version first** (`uname -r`); some tools need newer kernels or BTF.
- **Get the right privilege** — historically root; modern kernels allow the finer-grained `CAP_BPF`. Don't run as root if `CAP_BPF` will do.

---

## Edge Cases & Pitfalls

- **kprobe silently matches nothing** because the function was inlined or renamed in your kernel. No error, no data — check with `bpftrace -l 'kprobe:vfs_*'`.
- **`str()` on a NULL or unmapped pointer** can read garbage or fail — guard with a predicate where possible.
- **Per-thread scratch you never delete** leaks map entries on long runs.
- **Tracing a syscall on a busy box without a filter** floods you and adds real overhead. Scope it.
- **Symbols stripped from a binary** mean a uprobe by name can't resolve — you may need the address or a debug-symbol package.

---

## Common Mistakes

- **Using `printf` on `raw_syscalls:sys_enter`** and wondering why the terminal melts and the box slows. Aggregate instead.
- **Keying entry/return maps by `pid`** and getting nonsense when threads overlap. Use `tid`.
- **Expecting it to work on macOS/Windows out of the box.** This is Linux. (DTrace is the macOS cousin, different syntax.)
- **Treating a probe like a permanent metric.** It vanishes on reboot and costs overhead — that's not what it's for.
- **Forgetting `sudo`.** Most probes need elevated privilege; without it you get a permissions error, not data.

---

## Tricky Points

- **A `kretprobe` only fires if the function actually returns.** If it never returns (e.g. the task is killed mid-call), your `@start[tid]` lingers — hence the `delete()`.
- **`comm` is only 16 characters.** Long process names get truncated; don't be surprised by `some-very-long-` in the output.
- **Tracepoint fields differ per tracepoint.** `args->filename` exists on `sys_enter_openat`; another tracepoint has different `args`. List them with `bpftrace -lv 'tracepoint:syscalls:sys_enter_openat'`.
- **Two probes can race.** Counting `sys_enter` without the matching `sys_exit` can overcount if you only care about completed calls.

---

## Apply it

1. Choose one small, known input for **Dynamic Instrumentation & eBPF**.
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

- What problem does Dynamic Instrumentation & eBPF solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
