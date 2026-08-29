# Manual Memory Management — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Manual Memory Management** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Why these bugs are catastrophic (and exploitable)

A use-after-free or overflow is not just a crash. It is an **attacker primitive**. The canonical chain:

1. **Overflow or UAF** lets an attacker write where they shouldn't.
2. **Heap grooming / spraying** arranges the heap so the corrupted bytes land on something valuable — a function pointer, a vtable, allocator metadata.
3. **Control-flow hijack** redirects execution to attacker code (ROP/JOP).

This is the mechanism behind Heartbleed (an over-read), countless browser zero-days, and kernel privilege escalations. A single missed bounds check becomes remote code execution. That is why the industry treats memory-safety bugs as security-critical by default, not as ordinary bugs.

### The economics of "find it early"

The cost of a memory bug scales by orders of magnitude with how late it's caught: a compiler warning is free, an ASan failure in CI costs minutes, a fuzzing crash costs an engineer-hour, a production crash costs an incident, and a CVE costs a disclosure cycle plus reputation. The entire professional discipline is **shifting detection left** — pushing bugs from "discovered by an attacker" to "discovered by a tool in CI."

---

## Tooling: The Sanitizer & Analyzer Stack

### AddressSanitizer (ASan) — your first line of defense

ASan instruments your binary at compile time (`-fsanitize=address`). It maintains **shadow memory** marking each byte as addressable or poisoned, wraps every allocation in poisoned **redzones**, and routes freed memory through a **quarantine** so it isn't reused immediately. Then every load/store is checked.

It catches: heap/stack/global buffer overflows, use-after-free, use-after-return/scope, double-free, and invalid free — **with a stack trace at the moment of the violation**, not a mystery crash later.

```bash
clang -fsanitize=address -fno-omit-frame-pointer -g -O1 app.c -o app
./app    # aborts with a precise report on first violation
```

Cost: ~2× slowdown and ~3× memory. That's affordable for tests/CI/fuzzing, **not** for production. Pair with LeakSanitizer (`-fsanitize=address` includes it on Linux) for leaks.

### The rest of the suite

| Tool | Finds | When to run |
|------|-------|-------------|
| **LeakSanitizer** | Leaks (unreachable allocations at exit) | CI, bundled with ASan |
| **MemorySanitizer** | Uninitialized reads | Separate build (incompatible with ASan) |
| **ThreadSanitizer** | Data races | Concurrency tests (incompatible with ASan) |
| **UBSan** | Misalignment, integer overflow, invalid casts | Cheap; combine with ASan |
| **Valgrind/memcheck** | UAF, leaks, uninit reads — **no recompile needed** | Local debugging, third-party binaries |

**ASan vs Valgrind**: ASan is far faster (~2× vs ~20–50× for Valgrind) and catches stack/global overflows Valgrind misses, but requires recompilation. Valgrind needs no source/rebuild and runs on release binaries — invaluable when you can't recompile. Use ASan in CI; reach for Valgrind for ad-hoc and third-party debugging.

### Fuzzing — finding the inputs that trigger the bugs

Sanitizers detect bugs; **fuzzing finds the inputs that reach them**. libFuzzer/AFL++ generate inputs to maximize code coverage, run them under ASan/UBSan/MSan, and report any crash. Google's **OSS-Fuzz** runs this continuously on thousands of open-source projects and has found tens of thousands of bugs. Coverage-guided fuzzing + sanitizers is the single highest-leverage practice in memory-unsafe code.

### Static analysis

`clang-tidy`, the Clang Static Analyzer, GCC's `-fanalyzer`, and Coverity reason about code paths *without running it*, flagging likely leaks, null derefs, and double-frees. They produce false positives and miss path-sensitive bugs sanitizers catch, so they complement — not replace — dynamic tools. Run them as a fast pre-merge gate.

### Allocator hardening in production

Where sanitizers are too costly to ship, hardened allocators raise the exploitation bar: glibc tcache/safe-linking, **GWP-ASan** (sampling ASan-lite cheap enough for production), Chrome's PartitionAlloc, and `scudo` (Android). They don't eliminate bugs but turn many silent corruptions into clean crashes and frustrate exploits.

---

## Code Examples

### A CI build matrix that earns its keep

```bash
# Job 1: ASan + UBSan + LSan — overflows, UAF, leaks, UB
clang -fsanitize=address,undefined -fno-omit-frame-pointer -g -O1 ...

# Job 2: MSan — uninitialized reads (separate; incompatible with ASan)
clang -fsanitize=memory -fno-omit-frame-pointer -g -O1 ...

# Job 3: TSan — data races (separate; incompatible with ASan)
clang -fsanitize=thread -g -O1 ...

# Job 4: libFuzzer harness under ASan, time-boxed per PR
clang -fsanitize=address,fuzzer -g -O1 fuzz_target.c -o fuzzer && ./fuzzer -max_total_time=120
```

Each runs the test suite; any sanitizer abort fails the build. This is the modern minimum bar for shipping C/C++.

### Reading an ASan report

```
==1234==ERROR: AddressSanitizer: heap-use-after-free on address 0x602000000050
READ of size 4 at 0x602000000050 thread T0
    #0 0x... in process_record record.c:88      <- the offending read
freed by thread T0 here:
    #1 0x... in cleanup record.c:71              <- where it was freed
previously allocated by thread T0 here:
    #2 0x... in load_record record.c:42          <- where it was born
```

Three stack traces — **use site, free site, allocation site** — turn a "random" crash into a five-minute fix. This is the payoff for the 2× slowdown.

---

## Coding Patterns

- **Ship a sanitizer build in CI from day one.** Retrofitting ASan onto a mature codebase surfaces a backlog; doing it early keeps the codebase clean continuously.
- **Fuzz every parser and every trust boundary.** Anything consuming untrusted bytes (network, files, IPC) gets a libFuzzer/AFL harness under sanitizers.
- **Heap-profile long-running services.** `jemalloc`/`tcmalloc` profiling or `valgrind --tool=massif` on soak tests catches slow leaks before production does.
- **Wrap unsafe at the boundary.** In Rust, keep `unsafe` in tiny audited modules with a safe public API and `// SAFETY:` justifications. In C++, hide raw allocation behind RAII wrappers so no caller touches `new`/`delete`.
- **Adopt hardened allocators + GWP-ASan** for production crash diagnosis at near-zero overhead.

---

## Best Practices

1. **Make a sanitizer build a required CI gate** (ASan+UBSan+LSan at minimum). No green sanitizer, no merge.
2. **Continuously fuzz every untrusted-input parser** under sanitizers; integrate OSS-Fuzz if open source.
3. **Run LeakSanitizer/heap profilers on long soak tests**, not just unit tests — leaks need time.
4. **Read the three stack traces** in an ASan report; they pinpoint allocation, free, and misuse.
5. **Layer static analysis as a fast pre-merge gate** to catch what's cheap to catch early.
6. **In production, ship hardened allocators + sampling diagnostics** (GWP-ASan), never full sanitizers.
7. **For new memory-unsafe code in security-sensitive domains, seriously evaluate Rust** — the 70% statistic is the business case.

---

## Edge Cases & Pitfalls

- **ASan can't catch what tests don't execute.** Coverage gaps = blind spots; this is why fuzzing is non-negotiable.
- **MSan/TSan/ASan are mutually incompatible** — separate builds. Forgetting this means you think you're covered when you're not.
- **Sanitizers slow code ~2–50×** — don't put them on the latency-critical production path; teams have shipped ASan to prod and regretted it.
- **Custom allocators blind the tools.** Pool/arena allocators bypass `malloc`, so ASan won't see overflows inside them unless you add manual poisoning (`ASAN_POISON_MEMORY_REGION`).
- **`shared_ptr`/`Rc` cycle leaks are invisible to LSan** at exit if still "reachable" through the cycle — they look live. Audit ownership graphs.
- **Hardening is not safety.** GWP-ASan samples; PartitionAlloc raises cost. Determined attackers and unsampled paths still get through. Don't mistake "harder to exploit" for "safe."

---

## Apply it

1. Define the user or business outcome that **Manual Memory Management** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Manual Memory Management?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
