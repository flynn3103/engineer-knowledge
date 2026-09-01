# Debugging — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Debugging** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Debugging Roadmap](README.md)
> **Focus:** Stop single-stepping. Use the debugger like a power tool — conditional breaks, logpoints, watchpoints, remote attach, core dumps, race detectors, and the discipline of reducing a bug to a minimum repro.

---

## Core Concepts

### 1. Predict, then verify

A junior sets a breakpoint and *looks*. A middle-level engineer **predicts** what the state should be, sets a breakpoint, and **checks**. If the prediction matches reality, the bug is *not* there — eliminate that region and move on. If it doesn't match, you've found a hypothesis to chase.

### 2. The debugger is a query engine

Stop thinking of the debugger as a play/pause button on your code. Think of it as a database you can query: *"stop when this counter reaches 1000," "log every call to this function with its args," "alert me the next time this field is overwritten."* Conditional breakpoints, logpoints, and watchpoints are the SQL of that database.

### 3. Reduce, then reason

A 200,000-line codebase reproducing the bug is not a thing you can reason about. A 50-line repro is. Most of middle-level debugging is **reducing**: bisecting commits, bisecting input data, disabling half the features, deleting code that turns out to be irrelevant. The smaller the repro, the closer you are to the answer.

### 4. Production is a different planet

Your laptop has the same code as production. It does not have the same data, the same OS, the same locale, the same load, the same race conditions, or the same concurrency. A bug that "doesn't reproduce locally" is almost always one of: data, locale, time zone, concurrency, or load. Knowing which of those five to suspect first is half the job.

### 5. Crashes are gifts

A loud crash with a stack trace is *easy*. The hard bugs are the ones that silently corrupt data, return wrong-but-plausible results, or hang. When something crashes hard — a panic, a segfault, a core dump — be grateful. Read the stack. The bug is almost always closer than you think.

---

## Advanced Debugger Features

### Conditional breakpoints

```text
(gdb) break process_order if order_id == 0xDEADBEEF
(dlv) break main.go:142 cond i > 1000 && x == nil
(pdb) b orders.py:42, i > 1000 and x is None
```

The cost of evaluating the condition is paid every time the line executes, so don't put a network call in there. But for *"only stop when the bug actually happens"* — say, on iteration 4,973 of a 5,000-iteration loop — they're transformative.

### Hit-count breakpoints

Break only on the Nth time this point is reached. In IntelliJ this is a checkbox on the breakpoint dialog: **"Pass count: 50"**. In `gdb`, `ignore <bpnum> 49` skips the first 49 hits, then stops on the 50th. Useful when you know the failure happens *late* in a loop and you don't want to mash F5 fifty times.

### Logpoints

A logpoint is a breakpoint that **prints a message and continues** — no stop. This is the killer feature once you discover it. You can add ten logpoints, run once, read the timeline, and you've saved yourself ten edit/compile/rerun cycles.

| IDE | How |
|---|---|
| VS Code | Right-click gutter → "Add Logpoint" → message with `{expr}` interpolation |
| IntelliJ / GoLand | Right-click breakpoint → uncheck "Suspend" → check "Log evaluated expression" |
| GDB | `commands <bpnum>` → `silent` → `printf "n=%d\n", n` → `continue` → `end` |
| Delve | `trace main.go:42` or `on <bp> print n` |

### Watchpoints (data breakpoints)

Stop when a *variable* changes, regardless of which line caused the change. In `gdb`:

```text
(gdb) watch user.balance
Hardware watchpoint 2: user.balance
(gdb) cont
Hardware watchpoint 2: user.balance
Old value = 100
New value = -50    <-- you just caught the culprit
0x000... in apply_refund at billing.c:118
```

In IntelliJ for Java, this is called a **"Field Watchpoint"**. CPUs typically support 4 hardware watchpoints; beyond that they become software watchpoints, which are *much* slower (the debugger single-steps every instruction).

### Function breakpoints

Break on entry to a named function, even when you have no source file open. Critical when the bug is in third-party code:

```text
(gdb) break malloc
(dlv) break runtime.panic
(pdb) b http.client.HTTPConnection.send
```

You don't need to know what line `runtime.panic` lives on — just that you want to be notified when it gets called.

### Reverse debugging

`rr` (Mozilla's record-and-replay tool, C/C++ on Linux) lets you record a program once, then play it back arbitrarily many times — *backwards*. You hit a crash, then say `reverse-cont` and the debugger runs backwards to the previous breakpoint. This is the single most powerful debugging trick ever invented; if you do C++ on Linux and don't know `rr`, learn it today.

For Go, `dlv` supports reverse execution under the `--backend=rr` flag (also requires `rr` underneath). Java has JIVE and the (now archived) Chronon. Python has no first-class reverse debugger but PyRR exists for narrow use cases.

### Remote debugging

Your code is running somewhere else — a docker container, a Kubernetes pod, a customer's laptop. You attach over TCP.

```bash
# Python, on the server:
python -m debugpy --listen 0.0.0.0:5678 --wait-for-client app.py

# Go, on the server:
dlv exec ./mybin --headless --listen=:2345 --api-version=2

# Java, on the server (JDWP):
java -agentlib:jdwp=transport=dt_socket,server=y,suspend=n,address=*:5005 -jar app.jar
```

Then from your IDE: "Attach to remote process," point at host:port. The IDE talks to the remote debugger; you set breakpoints as if it were local. The cardinal rule: **the source code on your laptop must match the binary running remotely**, byte-for-byte, or line numbers drift and the experience becomes maddening.

---

## Per-Language Deep Dive

### Python: `pdb`, `ipdb`, `pudb`, `debugpy`, samplers

`pdb` cheat sheet (the parts juniors miss):

| Command | What it does |
|---|---|
| `l` / `ll` | List source around current line / list entire function |
| `n` / `s` / `r` | Next / step in / return from current function |
| `c` | Continue until next breakpoint |
| `b file:line, cond` | Conditional breakpoint |
| `tbreak file:line` | One-shot breakpoint (auto-cleared after first hit) |
| `p expr` / `pp expr` | Print / pretty-print expression |
| `display expr` | Show this expression after every step (auto-watch) |
| `interact` | Drop into a full Python REPL with locals available |
| `up` / `down` / `where` | Move up/down the call stack / show stack |
| `commands <bpnum>` | Attach commands to a breakpoint (turn it into a logpoint) |

Beyond stock `pdb`:

- **`ipdb`** — `pdb` with IPython's tab-completion and syntax highlighting. `pip install ipdb`.
- **`pdb++`** — drop-in upgrade with sticky mode (source view that updates as you step). `pip install pdbpp`.
- **`pudb`** — full-terminal TUI debugger; great when you can't run a GUI but want a real-time variable panel.
- **`debugpy`** — Microsoft's PyCharm/VS Code debugger backend; the way to do remote debugging in Python.
- **`py-spy`** — *sampling* profiler; attaches to a running Python process and shows what it's doing right now, no code changes. Use this when you can't restart the process.
- **`pyinstrument`** — sampling profiler with a beautiful flame-graph HTML output.
- **`tracemalloc`** — built-in memory tracker; `tracemalloc.start()` + `take_snapshot().compare_to(prev, 'lineno')` shows you where allocations are leaking.

Inside a script use `breakpoint()` (Python 3.7+) — it honors `PYTHONBREAKPOINT=ipdb.set_trace` so the IDE and CI can override which debugger fires.

### Go: `dlv` beyond `next/step/print`

Useful `dlv` commands that juniors don't reach for:

| Command | What it does |
|---|---|
| `goroutines` | List every goroutine, its state, and where it's blocked |
| `goroutine N` | Switch to goroutine N's stack (now `bt` shows ITS stack) |
| `goroutine N frame K cmd` | Run `cmd` against the Kth frame of goroutine N |
| `frame N` | Move the focus to stack frame N |
| `args` / `locals` | Show function arguments / local variables in current frame |
| `disassemble` (or `disass`) | Show the machine instructions for the current function |
| `regs` | Show CPU registers |
| `stack -full` | Stack trace including args and locals at each frame |
| `config substitute-path /buildroot/foo /Users/me/foo` | Tell dlv to map remote paths to local paths (essential for remote debugging) |
| `check <expr>` | Evaluate a Go expression in the current scope |
| `trace <regex>` | Tracepoint: log calls to functions matching regex without stopping |
| `dump <file>` | Write a core dump from this paused process |

`dlv attach <pid>` attaches to a running Go process. `dlv core <binary> <corefile>` opens a post-mortem.

### Java: IntelliJ tricks, JDWP, jcmd, jstack

The IntelliJ debugger is genuinely the best Java debugger on Earth — at middle level, learn these features:

- **Evaluate Expression** (`Alt+F8`): run arbitrary Java expressions in the current scope, including method calls. Crucial for "what would this return if I called it now?"
- **Drop Frame**: rewind to the entry of the current method as if it never ran. Combined with re-stepping, this is a poor man's reverse debugger.
- **Mark Object**: tag an object with a label like `_user42`, then refer to it in Evaluate Expression even from other threads.
- **Exception breakpoints**: stop the moment ANY `NullPointerException` is thrown, before it propagates. Game-changing for "where did this NPE actually originate?"
- **Stream debugger**: visualizes intermediate values inside `stream().filter().map().collect()` chains.

For headless servers:

- `jstack <pid>` — print every Java thread's stack trace right now. Use this for "the server is hung; why?"
- `jcmd <pid> Thread.print` — same, via JFR / diagnostic command channel.
- `jcmd <pid> GC.heap_dump /tmp/heap.hprof` — capture a heap dump for memory analysis.
- `jcmd <pid> JFR.start duration=60s filename=/tmp/recording.jfr` — start a low-overhead Java Flight Recorder profile.
- Remote debugging uses JDWP — see flag in the "Remote debugging" section above.

### JavaScript / Node

- **`--inspect-brk` vs `--inspect`**: both expose Chrome DevTools' debugger over a WebSocket. `--inspect-brk` pauses on the *first line* so you can set breakpoints before any code runs. `--inspect` lets the program start; you attach later.
- **Async Stack Traces**: Chrome DevTools can stitch together stacks across `await` boundaries — without this, an error in an async function shows you a stack that ends inside Node's event loop and is useless. Enable in DevTools settings.
- **`process.report.writeReport()`** — Node's built-in diagnostic report; writes a JSON file with all threads, environment, libuv handles, and uncaught error info. Trigger on `SIGUSR2` for production captures without crashing.
- **`node --prof` / `--prof-process`** — built-in CPU profiler.
- **Chrome `Performance` tab** — flame chart of every function call. Works on local Node via `--inspect`.

---

## Debugging Tests

Most middle-level bugs hide in tests. Either the test catches a real bug (great) or the test is itself flaky (the more annoying case). Either way, you debug the test, not the production code.

### Drop into the debugger from a test

```bash
# Python: jump into pdb at the moment the test fails
pytest -x --pdb tests/test_orders.py

# Python: jump into pdb at the *first* failure, anywhere
pytest --pdb

# Go: pass -v and -run to debug one specific test
go test -v -run TestOrderRefund ./billing/...

# Go with dlv:
dlv test ./billing/ -- -test.run TestOrderRefund
```

### Set a breakpoint inside the test code

```python
def test_refund_negative():
    order = build_order(total=100)
    breakpoint()        # <-- pytest --pdb-trace will not even be needed
    refund(order, 150)
    assert order.balance == -50
```

### "Passes locally, fails in CI" — the four usual suspects

When a test is green on your laptop and red in CI, the cause is almost always one of these four:

1. **Time zone.** CI runs in UTC; you're on `Europe/Istanbul`. Tests that hard-code dates ("the order is from yesterday") drift across midnight. **Fix:** freeze time (`freezegun`, `clock.Fake`), never use local time in assertions.
2. **Locale.** CI's `LC_ALL=C` formats `1,000.50` as `1000.50`; your `en_US.UTF-8` formats it as `1,000.50`. **Fix:** pin a locale in tests or stop formatting numbers in tested code.
3. **Randomness.** Your test uses `random.choice` / `uuid.uuid4` / map iteration order. CI runs in a different order and the bug surfaces. **Fix:** seed the RNG; never assert on iteration order of a `dict` / `map` / `set`.
4. **Filesystem case sensitivity.** macOS is case-insensitive by default; Linux CI is not. `foo.json` and `Foo.json` are the same file locally and different in CI. **Fix:** match casing exactly, or run tests on a case-sensitive volume locally.

There's a fifth, less common but worth knowing: **resource limits.** CI containers often have less memory, fewer CPUs, and tighter file-descriptor limits than your laptop. Tests that work locally but OOM in CI usually hit one of these.

---

## Reducing a Bug to a Minimum Repro

> A 50-line repro is the most valuable artifact you can produce. It is what makes a bug fixable instead of "one of those things that happens sometimes."

### Bisect on commits — `git bisect`

You shipped a release; users say the report PDF now has the wrong totals. Last release was fine. There are 287 commits between the two. You bisect.

```bash
$ git bisect start
$ git bisect bad                 # current HEAD is broken
$ git bisect good v2.4.0         # the last known-good release tag
Bisecting: 143 revisions left to test after this (roughly 8 steps)
[abc1234] Refactor report serializer to use new ledger

# build & run a small test that checks totals
$ make && ./bin/report --check
FAIL: totals incorrect

$ git bisect bad
Bisecting: 71 revisions left to test after this (roughly 7 steps)
[def5678] Add multi-currency support

$ make && ./bin/report --check
PASS

$ git bisect good
Bisecting: 35 revisions left to test after this (roughly 6 steps)
[aaa1111] Cache invalidation for report metadata

$ make && ./bin/report --check
FAIL

$ git bisect bad
Bisecting: 17 revisions left to test after this (roughly 5 steps)
...

# after a few more rounds:
$ git bisect bad
bbbbbbb is the first bad commit
commit bbbbbbb
Author: ...
    Replace decimal arithmetic with float in totals (perf)

# We have the culprit. Stop.
$ git bisect reset
```

Twenty rounds of bisecting cover a million commits. You almost never need more than ten. The discipline is to **have a fast, reliable test** — if your "is it bad" check takes 20 minutes, ten rounds is over three hours. Speed up the check first; bisect is bounded by check time.

You can fully automate it:

```bash
$ git bisect start HEAD v2.4.0
$ git bisect run make check-report   # exit 0 = good, non-zero = bad
```

Now `git` builds and tests each candidate commit unattended; you come back to the answer.

### Bisect on input data

A 10 MB JSON payload makes the parser crash. Don't squint at the JSON — bisect it. Delete the second half of the top-level array — does the bug reproduce? If yes, the bug's in the first half; recurse. If no, it's in the second half; restore and delete the first half instead. In 20 rounds you're down to one record.

Tools that automate this: **`creduce`** and **`cvise`** for C/C++ source files, **`delta`** for line-based files. They keep applying random reductions, re-running your check, and keep any reduction that preserves the bug.

### Bisect on features

The app misbehaves with a particular customer. The customer has 47 feature flags enabled. Turn off 24 of them. Does the bug still reproduce? Recurse on whichever half kept the bug. In 6 rounds, you've isolated the one flag.

### Why the 50-line repro matters

Once you have the repro, the bug is *not yours anymore* — it belongs to the codebase. You can attach it to a ticket, share it with a colleague, post it to the upstream project, or feed it to an LLM. A long, contextual, "you have to log in as our staging customer and click these eight things" reproduction is not shareable. A 50-line script is.

---

## Post-Mortem Debugging — First Contact

### Generating a core dump

By default most Linux systems disable core dumps. Enable them in the shell:

```bash
ulimit -c unlimited
# now any crash in this shell writes a core file to the cwd (or wherever the
# kernel pattern in /proc/sys/kernel/core_pattern points)
```

On modern systemd systems, dumps go to `systemd-coredump`'s journal:

```bash
coredumpctl list                       # all recent core dumps
coredumpctl info <pid|exe|match>       # metadata
coredumpctl gdb <pid|exe|match>        # open in gdb directly
coredumpctl dump <match> > core.bin    # extract the raw core file
```

### Opening a core dump

```bash
# C/C++
gdb ./prog ./core
(gdb) bt              # stack at crash point
(gdb) info threads    # all threads
(gdb) thread 5        # switch to thread 5
(gdb) frame 3         # move to frame 3 of its stack
(gdb) print mystruct  # inspect a variable

# Go
dlv core ./prog ./core
(dlv) bt
(dlv) goroutines
(dlv) goroutine 1
(dlv) frame 2
(dlv) print myvar
```

### Reading the stack at the crash point

The top of the stack is the function that was running when the crash happened. Walk *down* (older frames) to find context: who called this, with what arguments. The bug is usually three or four frames below the crash — the crash site is often a victim, not a culprit.

### Symbol files: why stripped binaries are useless

Production binaries are usually stripped — function names, line numbers, and variable names removed to save space and obscure the implementation. Open a stripped binary's core dump and you get this:

```text
#0  0x0000000000401a3f in ?? ()
#1  0x0000000000402b81 in ?? ()
#2  0x00007ffff7a2d09b in ?? ()
```

Useless. You need the **symbol file** that was generated alongside the binary at build time. For Go, build with `-trimpath` but **keep** the unstripped binary in your release archive. For C/C++, build with `-g` and use `objcopy --only-keep-debug` to extract symbols into a `.dbg` file. Then in gdb: `set debug-file-directory /path/to/symbols`. Without symbol files, post-mortem debugging is fingerprinting a ghost.

---

## Memory and Concurrency Debugging — First Taste

### Go's race detector

```bash
go test -race ./...        # run all tests with race detection
go run -race ./cmd/server  # run the server with race detection
go build -race -o myapp .  # ship a race-detecting binary (slow, dev only)
```

The race detector instruments every memory access and tracks which goroutine wrote which address. When two goroutines touch the same address without synchronization, you get a report like:

```text
WARNING: DATA RACE
Read at 0x00c00012e0a8 by goroutine 7:
  main.(*Counter).Get()
      /src/counter.go:18 +0x44

Previous write at 0x00c00012e0a8 by goroutine 6:
  main.(*Counter).Inc()
      /src/counter.go:14 +0x65
```

**Rule:** run *every* test suite with `-race` in CI. The cost is ~5x runtime and ~10x memory, but the bugs it catches will cost weeks to find any other way.

### ThreadSanitizer for C/C++ / Rust's `loom`

For C/C++, **ThreadSanitizer** (`-fsanitize=thread` with clang) plays the same role. Address Sanitizer (`-fsanitize=address`) catches use-after-free, heap-buffer-overflow, double-free. Memory Sanitizer (`-fsanitize=memory`) catches uninitialized reads.

For Rust concurrency tests, **`loom`** systematically explores all possible thread interleavings of a small concurrent test. Where a race detector says "this run had a race," `loom` says "no possible run has a race" — a much stronger guarantee for the unit tests of your lock-free data structure.

### Python concurrency quirks

Python's GIL means data races on Python objects are *rare* (one bytecode instruction runs atomically) but **not impossible**. Multi-instruction sequences are absolutely racy:

```python
counter += 1   # read counter, add 1, store counter — three steps, fully racy
```

Free-threaded Python (PEP 703, opt-in in 3.13+) removes the GIL and exposes a *lot* of latent races. If you're on free-threaded Python, you need locks anywhere you have shared mutable state, full stop.

### The Heisenbug — "I added a print and now it works"

If a bug disappears when you add a print, it's almost always one of:

1. **A race condition.** The print adds enough I/O latency that one thread now reliably wins the race.
2. **Uninitialized memory.** In C/C++, the print happens to overwrite garbage with something benign.
3. **A dead-code optimization difference.** Adding the print prevented the compiler from eliminating a variable, which had a side effect you were depending on.
4. **A buffering effect.** Output flushed at a different time changed the observed order of events on the network.

The right reaction to a heisenbug is *not* to leave the print in. The right reaction is to suspect one of the four above, and use the right tool: race detector, sanitizer, `-O0` build, `tcpdump`.

---

## Logging-Driven Debugging

When the system is in production and you can't attach a debugger, the only knob you have is the log. Middle-level engineers treat this as a first-class technique, not a fallback:

1. **Add structured trace logs** at the points your hypothesis says matter. Deploy. Read the logs. Don't leave them in — once the bug is fixed, remove them or downgrade them to `DEBUG`.
2. **Use spans / OpenTelemetry** rather than free-form logs when you can. `dd_trace.tracer.trace("refund_logic")` or `tracer.StartSpan("refund_logic")` gives you durations, parents, and structured fields for free.
3. **Correlate with a request ID.** A log line with no request ID is a needle. With a request ID, it's a chapter.

This *is* "print debugging" — but in production, with structure, with correlation IDs, and with a plan to remove the prints afterwards. That is what distinguishes it from the [print-debugging antipattern](../02-logging/middle.md): in dev you should be in the debugger; in prod, prints (with structure) are often the only option.

> Don't conflate diagnostic logs with permanent telemetry. Diagnostic logs are scaffolding — they come down. Telemetry is part of the product.

---

## The Five Whys Technique

A defect surfaces. You ask "why?" and answer it. Then you ask why of the answer. Repeat until you reach a cause you can actually change.

> **Example.**
>
> 1. **Why did the report total come out wrong?** Because two line items were summed twice.
> 2. **Why were they summed twice?** Because the deduplication step ran *after* the sum step.
> 3. **Why did dedup run after sum?** Because the pipeline orders steps by registration order, and the dedup module was added last.
> 4. **Why does the pipeline order by registration?** Because nobody set explicit dependencies; the API allows it.
> 5. **Why does the API allow it?** Because the original design assumed authors would only register independent steps.
>
> The change you can make: add explicit `dependsOn:` to the pipeline definition, OR change the API to require it.

The discipline is to **stop at the change you can actually make**. Going deeper than that lands you in philosophy ("why did we choose this architecture?"). Stopping shallower lands you with a fix that doesn't prevent the next instance ("we just put `dedup` first this time"). The right depth is the deepest cause you have agency over.

---

## Code Examples

We use the same buggy program in two languages so the debugger sessions are directly comparable. The bug: a counter is incremented from two goroutines / threads without synchronization, so the final value is wrong.

### Go — `dlv` transcript on a racy counter

```go
// counter.go
package main

import (
	"fmt"
	"sync"
)

type Counter struct {
	n int
}

func (c *Counter) Inc() { c.n++ }
func (c *Counter) Get() int { return c.n }

func main() {
	c := &Counter{}
	var wg sync.WaitGroup
	for i := 0; i < 2; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for j := 0; j < 1000; j++ {
				c.Inc()
			}
		}()
	}
	wg.Wait()
	fmt.Println("final =", c.Get())
}
```

A `dlv` transcript investigating why `final` is sometimes less than 2000:

```text
$ go build -gcflags=all="-N -l" -o counter .   # disable inlining/optim
$ dlv exec ./counter
Type 'help' for list of commands.
(dlv) break counter.go:13         # break inside Inc()
Breakpoint 1 set at 0x49c2a0 for main.(*Counter).Inc() counter.go:13

(dlv) cond 1 c.n == 999          # only stop when n is about to become 1000
(dlv) continue

> [Breakpoint 1] main.(*Counter).Inc() counter.go:13
(dlv) goroutines
* Goroutine 7 - User: counter.go:24 main.main.func1 (0x49c3a0)
  Goroutine 8 - User: counter.go:24 main.main.func1 (0x49c3a0)
  ...

(dlv) goroutine 7
(dlv) bt
0  0x000000000049c2a0 in main.(*Counter).Inc at counter.go:13
1  0x000000000049c3a8 in main.main.func1 at counter.go:24

(dlv) goroutine 8 frame 0 print c.n
1000     # <-- the OTHER goroutine just got here and already incremented

# So we caught two goroutines in Inc() with c.n == 999 / 1000
# simultaneously. That is the race. The second .n++ will not
# see the first's write -> we lose increments.

(dlv) quit
```

Now rerun with the race detector:

```text
$ go run -race counter.go
==================
WARNING: DATA RACE
Write at 0x00c0000180a8 by goroutine 7:
  main.(*Counter).Inc()
      counter.go:13 +0x44
Previous write at 0x00c0000180a8 by goroutine 8:
  main.(*Counter).Inc()
      counter.go:13 +0x44
==================
final = 1873
Found 1 data race(s)
```

The race detector hands you the bug for free — that's why you run it in CI.

### Python — `pdb` transcript on the same bug

```python
# counter.py
import threading

class Counter:
    def __init__(self):
        self.n = 0
    def inc(self):
        self.n += 1
    def get(self):
        return self.n

def worker(c):
    for _ in range(100_000):
        c.inc()

if __name__ == "__main__":
    c = Counter()
    ts = [threading.Thread(target=worker, args=(c,)) for _ in range(2)]
    for t in ts: t.start()
    for t in ts: t.join()
    print("final =", c.get())
```

```text
$ python -m pdb counter.py
> counter.py(1)<module>()
-> import threading
(Pdb) b counter.py:8, self.n > 99990
Breakpoint 1 at counter.py:8
(Pdb) c
> counter.py(8)inc()
-> self.n += 1
(Pdb) p self.n
99991
(Pdb) p threading.current_thread().name
'Thread-1 (worker)'

# walk up the stack to see the loop counter:
(Pdb) up
> counter.py(13)worker()
-> c.inc()
(Pdb) p _              # the underscore loop var in CPython has no name here
*** NameError: name '_' is not defined

# Confirm two threads are alive and both about to write n:
(Pdb) p [t.name for t in threading.enumerate()]
['MainThread', 'Thread-1 (worker)', 'Thread-2 (worker)']
(Pdb) c
```

Sometimes the final value is 200000, sometimes 173842. On CPython the GIL makes the race rare-but-not-impossible because `self.n += 1` is **three** bytecode instructions (`LOAD_ATTR`, `BINARY_ADD`, `STORE_ATTR`) — the GIL can release between them.

### Java — IntelliJ Field Watchpoint sketch

```java
public class Counter {
    int n = 0;
    void inc() { n++; }
    int get() { return n; }

    public static void main(String[] args) throws Exception {
        Counter c = new Counter();
        Thread t1 = new Thread(() -> { for (int i = 0; i < 100000; i++) c.inc(); });
        Thread t2 = new Thread(() -> { for (int i = 0; i < 100000; i++) c.inc(); });
        t1.start(); t2.start();
        t1.join(); t2.join();
        System.out.println("final = " + c.get());
    }
}
```

In IntelliJ: right-click on `int n` → **Add Field Watchpoint** → check both "Access" and "Modification". Run in debug. Every write to `n` stops the program with the offending thread in focus. You will quickly observe two threads both about to write `n = 50001` — caught.

### Rust — `loom` exhaustively proves the race exists

```rust
// Cargo.toml: loom = "0.7"
use loom::sync::atomic::{AtomicUsize, Ordering};
use loom::sync::Arc;
use loom::thread;

#[test]
fn racy_counter_is_actually_racy() {
    loom::model(|| {
        let n = Arc::new(AtomicUsize::new(0));
        let n1 = n.clone();
        let t = thread::spawn(move || {
            // intentionally weak ordering, intentionally non-atomic ops
            let v = n1.load(Ordering::Relaxed);
            n1.store(v + 1, Ordering::Relaxed);
        });
        let v = n.load(Ordering::Relaxed);
        n.store(v + 1, Ordering::Relaxed);
        t.join().unwrap();
        // assert final == 2 — loom will find an interleaving where it's 1
        assert_eq!(n.load(Ordering::Relaxed), 2);
    });
}
```

`loom` enumerates thread interleavings. The assertion will fail for the interleaving where both threads load `0` before either stores. You don't have to *catch* a race — `loom` *proves* one exists.

---

## Coding Patterns

### Pattern: `breakpoint()` in tests, never committed

```python
def test_complex_path():
    setup()
    breakpoint()    # <-- removed before merging
    actual = under_test()
    assert actual == expected
```

Wire a pre-commit hook (`git grep -E '\bbreakpoint\(\)|pdb.set_trace\(\)|dlv\.\.|debugger;' --cached`) that rejects commits containing live debugger calls.

### Pattern: `TRACE` log level for the bug du jour

```python
log.trace("entering refund: order=%s amount=%s", order.id, amount)
```

Add at the start of investigation, set `TRACE` level only in the environment where you're hunting, remove after.

### Pattern: deterministic test setup

```python
import random
random.seed(0)
faker = Faker(); faker.seed_instance(0)
freezegun.freeze_time("2026-05-29T10:00:00Z")
```

Eliminate the four CI-vs-local sources of non-determinism at test-setup time, not when chasing a flake.

---

## Clean Code

- Never check in `breakpoint()` / `pdb.set_trace()` / `debugger;` / `dlv` artifacts.
- Don't leave commented-out `print(x)` lines. Delete or convert to logs.
- Don't write tests that depend on iteration order of unordered collections.
- Don't write tests that depend on the local timezone or locale.
- Symbol files are part of a release. Treat them as build artifacts, store them with the binary.
- Run `-race` (Go) / TSan (C/C++) in CI, every commit, no exceptions.

---

## Best Practices

- **Hypothesis first, then breakpoint.** State out loud (or in a comment) what you expect to see; then look. If reality matches, eliminate that region.
- **Prefer logpoints over breakpoints** when you want a timeline rather than a single state.
- **Always know which version of source matches the binary.** Remote debugging silently lies when they don't match.
- **Use `git bisect` before reading the diff.** It's faster than your eyes for any regression range bigger than ~10 commits.
- **Make `dlv core` / `coredumpctl gdb` a 10-minute drill** so it's not the first time you're doing it during an outage.
- **Run the race detector in CI** — once, forever, on every PR.
- **Reduce before you reason.** A 50-line repro is worth more than an hour of stepping.
- **Stop refactoring while debugging.** Fix the bug, commit, then refactor. Mixing the two doubles every code review.

---

## Edge Cases & Pitfalls

- **Conditional breakpoint condition itself throws.** A condition like `obj.field == 5` will throw `NullPointerException` when `obj` is null; debugger behavior is unspecified (some skip, some break, some loop). Always null-check first: `obj != null && obj.field == 5`.
- **Hit-count breakpoints reset on every debugger session.** If the bug is at iteration 50,000 and you restart the debugger, the counter starts over.
- **Watchpoints survive function returns** — they fire when the watched variable is *destroyed* too, which can look like a spurious hit.
- **Remote debugging through NAT.** The debugger client needs to reach the debugger server; SSH port-forward (`ssh -L 2345:localhost:2345 host`) is the usual workaround.
- **Core dumps on machines with mlockall'd memory** may not contain what you expect — some memory regions are excluded from dumps by design.
- **`go test -race` on cgo-heavy code** can produce false-ish positives if the C side is doing its own synchronization the race detector can't see.
- **JDWP exposed to the public internet is a remote code execution vulnerability.** Bind to `localhost` and SSH-tunnel.

---

## Common Mistakes

1. **Single-stepping a 10,000-iteration loop**, when a conditional breakpoint at `if i == 9_500` would have answered the question in one go.
2. **Adding a `print`, seeing it "fix" the bug, and shipping the print.** That is not a fix — that's a heisenbug you've now memorialized in production code.
3. **Running tests without `-race`**, then being mystified why a flake "only fires in production."
4. **Trying to read a stripped binary's core dump** without symbol files. It's not debuggable; rebuild with symbols and reproduce.
5. **Refactoring while debugging.** You'll either break the test you're using as your repro, or land a refactor that *also* fixes the bug for unrelated reasons, and never learn the cause.
6. **Skipping `git bisect`** because it "feels slow." Twenty minutes of bisect beats two days of reading diffs every time.
7. **Going more than five "whys" deep**, ending up in philosophy and shipping no fix.
8. **Catching the exception to "make it go away"** before understanding what it meant.

---

## Tricky Points

- **Logpoints in hot paths can change timing enough to mask races.** Use sampling (`py-spy`, `perf`) for hot-path investigation instead.
- **`dlv` and `gdb` line numbers can drift** if the binary was built with optimizations. Build with `-gcflags=all="-N -l"` (Go) or `-O0` (gcc/clang) for accurate stepping.
- **Field watchpoints catch only direct field access.** If a field is mutated via reflection (`Unsafe.putInt`) or JNI, the watchpoint may miss it.
- **Reverse debugging is *not* "undo".** Side effects on the world (network, file writes, syscalls) don't reverse — `rr` records and replays the *program's* execution, not external state changes.
- **`dlv attach <pid>` requires `CAP_SYS_PTRACE`** or matching UIDs. On Linux, `ptrace_scope` may block it; `echo 0 | sudo tee /proc/sys/kernel/yama/ptrace_scope`.
- **Core dumps contain memory.** That includes passwords, keys, customer data. Treat them as sensitive data, store them encrypted, delete after use.
- **The race detector reports the *first* race it sees.** Fix it, rerun — there might be three more behind it.

---

## Debugging Mindset Traps

### Trap 1: "This should be impossible"

Whenever your brain says *"that can't happen,"* one of the following is true: an assumption you made is wrong, you're not reading the version of the code that's actually running, or the input is not what you think it is. The bug isn't impossible. *Your model* is impossible. Find the assumption.

### Trap 2: "I'll just add a try/except"

The lazy way to make a stack trace go away is to wrap it in `try: ... except: pass`. Now the bug doesn't crash — it silently corrupts state, and you'll spend a week tracking down a downstream symptom. **Catch only the specific exception you understand, and only at the layer where you can do something meaningful with it.** Anywhere else, let it propagate.

### Trap 3: "Let me refactor while I'm here"

You found the bug. You also notice that the function is 200 lines long, badly named, and has a confusing parameter order. You decide to "clean up while you're at it." Two outcomes: (a) the refactor breaks the test you were using as your repro and you no longer know if the bug is fixed; (b) the refactor lands with the bug fix and the review is so big nobody catches a regression you introduced. **Fix the bug. Commit. Open a separate PR for the refactor.**

### Trap 4: "It works on my machine"

This sentence is never a defense; it's a hypothesis statement. The right follow-up is *"so what's different between my machine and production?"* and then you list every dimension: OS, locale, timezone, data, concurrency, load, dependency versions. The difference is in that list. Always.

---

## Bug Triage

You will never have time to fix every bug. Triage is the art of choosing which to fix first.

| Severity | Frequency | Action |
|---|---|---|
| Crash + data loss | Any | Fix today, hotfix release |
| Crash, no data loss | Frequent | Fix in next release |
| Crash, no data loss | Rare (<0.01%) | Log it, watch the rate; fix if it climbs |
| Wrong result | Common | Fix in next release |
| Wrong result | Rare, edge case | Backlog with repro |
| UI glitch | Any | Backlog |
| Performance regression | Detectable by users | Fix in next release |
| Performance regression | Sub-second, invisible | Backlog |

The "ship it" calculation: **estimated user pain × frequency / cost-to-fix**. A "definite annoyance" affecting 30% of requests beats a "rare crash" affecting 0.001%. A 30-minute fix beats a 3-day fix at the same pain level. Write the math down; don't argue it in meetings.

---

## Apply it

1. Find a real component where **Debugging** affects an interface or dependency.
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

- Which boundary is most affected by Debugging?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
