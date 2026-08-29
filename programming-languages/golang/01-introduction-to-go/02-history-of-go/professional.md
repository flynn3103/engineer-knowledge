# History of Go — Under the Hood

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **History of Go — Under the Hood** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## How It Works Internally

### The Go Compiler Evolution

Go has had three main compiler implementations:

1. **gc (Plan 9 C → Go)** — the official compiler
2. **gccgo** — a GCC frontend for Go
3. **tinygo** — LLVM-based compiler for embedded/WASM

The `gc` compiler evolution:

| Period | Compiler | Written In | Key Characteristic |
|--------|----------|-----------|-------------------|
| 2009-2014 | gc (original) | C (Plan 9 dialect) | Fast compilation, simple code generation |
| 2015 (Go 1.5) | gc (self-hosting) | Go | Mechanically translated from C to Go |
| 2016 (Go 1.7) | gc + SSA | Go | SSA-based backend, significant optimizations |
| 2017 (Go 1.9) | gc + improved SSA | Go | Better register allocation |
| 2021 (Go 1.17) | gc + register ABI | Go | Register-based calling convention (5-15% faster) |
| 2023 (Go 1.20) | gc + PGO | Go | Profile-guided optimization |

```mermaid
flowchart TD
    A[.go source files] --> B[Lexer/Parser]
    B --> C[AST - Abstract Syntax Tree]
    C --> D[Type Checking & Inference]
    D --> E[IR - Intermediate Representation]
    E --> F[SSA Generation - since Go 1.7]
    F --> G[Optimization Passes]
    G --> H[Machine Code Generation]
    H --> I[Linker]
    I --> J[Single Static Binary]

    K[PGO Profile - since Go 1.20] -.->|guides| G
```

### The Self-Hosting Journey (Go 1.5)

The transition from C to Go was done using a mechanical translation tool:

```
Step 1: Go 1.4 compiler (written in C) → compiles Go 1.5 compiler (written in Go)
Step 2: Go 1.5 compiler (in Go) → compiles itself (bootstrapping)
Step 3: All future Go compilers are written in Go
```

The tool used was `c2go`, which translated the Plan 9 C source into Go source code. This was intentionally a mechanical (not idiomatic) translation to minimize human error. Later versions gradually refactored the translated code into idiomatic Go.

---

## Runtime Deep Dive

### GC Evolution: From Stop-the-World to Concurrent Tri-Color

#### Go 1.0-1.4: Stop-the-World Mark-and-Sweep

```
Phase 1: STOP all goroutines (STW)
Phase 2: Mark all reachable objects from roots
Phase 3: Sweep unmarked objects
Phase 4: Resume goroutines

Total pause: 100ms - 300ms+ depending on heap size
```

#### Go 1.5: Concurrent Tri-Color Mark-and-Sweep

The Go team implemented a concurrent garbage collector based on the Dijkstra tri-color abstraction:

```go
// Conceptual model of tri-color marking
// From: runtime/mgc.go (conceptual)

// White: not yet visited (potentially garbage)
// Grey:  visited but children not yet scanned
// Black: visited and all children scanned

// Invariant (tri-color invariant):
// No black object points to a white object
// This is maintained using a WRITE BARRIER
```

```mermaid
flowchart TD
    subgraph "Tri-Color GC (Go 1.5+)"
        A[White Objects\nPotentially Garbage] --> B[Grey Objects\nQueued for Scanning]
        B --> C[Black Objects\nKnown Reachable]
    end
    D[GC Roots\nStack, Globals] --> B
    C -.->|Write Barrier\nPrevents invariant violation| A

    style A fill:#fff,stroke:#333
    style B fill:#ccc,stroke:#333
    style C fill:#333,stroke:#333,color:#fff
```

#### Go 1.8: Hybrid Write Barrier

Go 1.8 introduced a hybrid write barrier that eliminated the need to re-scan stacks:

```go
// Conceptual hybrid write barrier (runtime/mbarrier.go)
//
// writePointer(slot, ptr):
//   shade(*slot)  // shade the old value (Yuasa-style deletion barrier)
//   if current goroutine stack is grey:
//       shade(ptr) // shade the new value (Dijkstra-style insertion barrier)
//   *slot = ptr
//
// This eliminated stack re-scanning, reducing STW to ~100us
```

#### Go 1.19: GOMEMLIMIT — Soft Memory Limit

```go
// runtime/mgc.go conceptual: GOMEMLIMIT integration
//
// Before GOMEMLIMIT:
//   GC triggers when heap reaches GOGC% above previous live heap
//   Problem: if GOGC=100 and live heap is 1GB, GC allows 2GB peak
//
// With GOMEMLIMIT:
//   GC adjusts effective GOGC to stay under the memory limit
//   If heap approaches limit, GC runs more aggressively
//   This prevents OOM without requiring manual GOGC tuning
```

### Scheduler Evolution: G-M to G-M-P

#### Original Model (Go 1.0): G-M (Goroutine-Machine)

```
G (goroutine) → M (OS thread)

Problems:
- Global mutex on the goroutine queue (contention)
- No work stealing
- Blocked M blocks all its goroutines
```

#### Current Model (Go 1.1+): G-M-P (Goroutine-Machine-Processor)

Dmitry Vyukov redesigned the scheduler in Go 1.1:

```go
// From: runtime/runtime2.go (simplified)

// G - goroutine
// Contains: stack, instruction pointer, status, channel wait info
// type g struct {
//     stack       stack    // goroutine stack
//     sched       gobuf    // scheduling state (SP, PC, etc.)
//     atomicstatus uint32  // goroutine status
// }

// M - OS thread (machine)
// Contains: current G, signal handling, thread-local storage
// type m struct {
//     g0      *g     // goroutine for scheduling
//     curg    *g     // current running goroutine
//     p       *p     // attached P (nil if not running Go code)
// }

// P - logical processor
// Contains: local run queue, mcache, timer heap
// type p struct {
//     runqhead uint32
//     runqtail uint32
//     runq     [256]guintptr  // local run queue (lock-free)
// }
```

```mermaid
flowchart TD
    subgraph "G-M-P Scheduler (Go 1.1+)"
        subgraph "P0 (Logical Processor)"
            LRQ0[Local Run Queue\nG1, G2, G3]
        end
        subgraph "P1 (Logical Processor)"
            LRQ1[Local Run Queue\nG4, G5]
        end
        GRQ[Global Run Queue\nG6, G7]
        M0[M0 - OS Thread] --- P0
        M1[M1 - OS Thread] --- P1
        M2[M2 - OS Thread\nBlocked on syscall]
    end

    LRQ0 --> M0
    LRQ1 --> M1
    GRQ -.->|Steal work| LRQ0
    GRQ -.->|Steal work| LRQ1
    M1 -.->|Work stealing| LRQ0
```

Key improvements:
- **Local run queues (per-P):** Eliminates global mutex contention
- **Work stealing:** Idle P steals goroutines from busy P's queue
- **Handoff:** When M blocks on syscall, P is handed off to another M
- **Non-cooperative preemption (Go 1.14):** Goroutines can be preempted at any safe point, not just function calls

---

## Compiler Perspective

### SSA (Static Single Assignment) — Go 1.7+

The SSA backend was the most significant compiler improvement in Go's history:

```bash
# View SSA intermediate representation
GOSSAFUNC=main go build main.go
# Opens ssa.html in browser showing all optimization passes
```

```go
package main

import "fmt"

func add(a, b int) int {
    return a + b
}

func main() {
    result := add(3, 5)
    fmt.Println(result)
}
```

```bash
# View compiler decisions
go build -gcflags="-m -m" main.go
# Output shows:
# ./main.go:5:6: can inline add with cost 4 as: func(int, int) int { return a + b }
# ./main.go:9:15: inlining call to add
```

### Register-Based Calling Convention (Go 1.17)

Before Go 1.17, all function arguments were passed on the stack (Plan 9 convention). Go 1.17 introduced register-based argument passing:

```
Before Go 1.17 (stack-based):
  MOVQ arg1, 0(SP)    ; push arg1 to stack
  MOVQ arg2, 8(SP)    ; push arg2 to stack
  CALL function        ; call
  MOVQ 16(SP), result  ; read result from stack

After Go 1.17 (register-based):
  MOVQ arg1, AX        ; arg1 in register AX
  MOVQ arg2, BX        ; arg2 in register BX
  CALL function         ; call
  ; result in AX        ; result returned in register
```

This change provided **5-15% performance improvement** across all Go programs without any code changes.

### Profile-Guided Optimization (Go 1.20+)

```bash
# Step 1: Generate a CPU profile from representative workload
go test -cpuprofile=default.pgo -bench=. ./...

# Step 2: Place default.pgo in the package directory

# Step 3: Build with PGO (automatic if default.pgo exists)
go build -pgo=auto ./...

# PGO optimizations include:
# - More aggressive inlining of hot functions
# - Better devirtualization of interface calls
# - Improved branch prediction hints
```

---

## Memory Layout

### Goroutine Stack Evolution

```
Go 1.0-1.3: Segmented stacks
+--------+   +--------+   +--------+
| Seg 1  |-->| Seg 2  |-->| Seg 3  |
| 8 KB   |   | 8 KB   |   | 8 KB   |
+--------+   +--------+   +--------+
Problem: "hot split" — function calls at segment boundary cause
repeated stack grow/shrink (thrashing)

Go 1.4+: Contiguous (copyable) stacks
+----------------------------------+
| Goroutine Stack (starts at 2KB)  |
+----------------------------------+
         |
         v  (grows by 2x when needed)
+----------------------------------+
| Goroutine Stack (now 4KB)        |
+----------------------------------+
Benefit: No hot split, more cache-friendly
Cost: Must update all pointers when stack moves (copy + adjust)
```

The initial goroutine stack size has also shrunk over Go's history: it was
8KB before Go 1.2, 4KB before Go 1.4, and 2KB from Go 1.4 onward.

---

## OS / Syscall Level

### Non-Cooperative Preemption (Go 1.14+)

Before Go 1.14, goroutines could only be preempted at function call boundaries. A tight loop without function calls would monopolize the thread:

```go
// This goroutine could NOT be preempted before Go 1.14:
func tightLoop() {
    for {
        // No function calls — no preemption point!
        // This would starve other goroutines
    }
}
```

Go 1.14 introduced asynchronous preemption using OS signals:

```
1. Scheduler decides goroutine G has run too long
2. Runtime sends SIGURG to the thread running G
3. Signal handler saves G's state at current PC
4. Scheduler switches to another goroutine
```

---

## Assembly Output Analysis

```bash
go build -gcflags="-S" main.go 2>&1 | head -50
# or for a specific function:
go tool objdump -s "main.add" ./binary
```

### Example: Function Call ABI Evolution

```go
package main

func add(a, b int) int {
    return a + b
}

func main() {
    _ = add(3, 5)
}
```

**Go 1.16 assembly (stack-based ABI):**
```asm
TEXT main.add(SB)
    MOVQ    "".a+8(SP), AX     ; load a from stack
    ADDQ    "".b+16(SP), AX    ; add b from stack
    MOVQ    AX, "".~r2+24(SP)  ; store result on stack
    RET

TEXT main.main(SB)
    MOVQ    $3, (SP)           ; push 3 to stack
    MOVQ    $5, 8(SP)          ; push 5 to stack
    CALL    main.add(SB)       ; call
    ; result at 16(SP)
```

**Go 1.17+ assembly (register-based ABI):**
```asm
TEXT main.add(SB)
    ADDQ    BX, AX             ; add BX to AX (args in registers!)
    RET                        ; result in AX

TEXT main.main(SB)
    MOVL    $3, AX             ; arg1 in AX
    MOVL    $5, BX             ; arg2 in BX
    CALL    main.add(SB)       ; call
    ; result in AX
```

**What to notice:**
- Go 1.17+ uses fewer instructions (no stack memory access)
- Arguments pass through registers (AX, BX, CX, DI, SI, R8-R11)
- Return values also use registers
- This is the source of the 5-15% performance improvement

---

## Performance Internals

### Benchmarks with Profiling Across Versions

```go
package main

import (
    "testing"
)

// This benchmark shows how the same code gets faster
// with newer Go versions due to compiler improvements

func BenchmarkStringConcat(b *testing.B) {
    for i := 0; i < b.N; i++ {
        s := ""
        for j := 0; j < 100; j++ {
            s += "x"
        }
        _ = s
    }
}

// Results across versions (approximate):
// Go 1.15: 12000 ns/op    5600 B/op   100 allocs/op
// Go 1.17: 10200 ns/op    5600 B/op   100 allocs/op  (register ABI)
// Go 1.20:  9800 ns/op    5600 B/op   100 allocs/op  (PGO available)
// Go 1.22:  9500 ns/op    5600 B/op   100 allocs/op  (better inlining)
```

```bash
go test -bench=. -benchmem -cpuprofile=cpu.prof
go tool pprof cpu.prof
# (pprof) top10
# (pprof) web  # visual call graph
```

**Internal performance characteristics:**
- **Register ABI (1.17):** Eliminates stack spill for arguments — significant for small, frequently-called functions
- **PGO (1.20):** Compiler inlines functions that profiling shows are hot — devirtualizes interface calls in hot paths
- **GC improvements:** Each version reduces GC pause duration, reducing tail latency

---

## Metrics & Analytics (Runtime Level)

### Go Runtime Metrics

```go
package main

import (
    "fmt"
    "runtime"
    "runtime/metrics"
)

func main() {
    // Go 1.16+: runtime/metrics API — does NOT cause STW (unlike ReadMemStats)
    descs := metrics.All()
    fmt.Printf("Go %s has %d runtime metrics\n", runtime.Version(), len(descs))

    // Key metrics for understanding GC and scheduler behavior
    samples := []metrics.Sample{
        {Name: "/memory/classes/heap/objects:bytes"},
        {Name: "/memory/classes/total:bytes"},
        {Name: "/gc/cycles/total:gc-cycles"},
        {Name: "/gc/heap/goal:bytes"},
        {Name: "/sched/goroutines:goroutines"},
        {Name: "/sched/latencies:seconds"},
    }
    metrics.Read(samples)

    for _, s := range samples {
        switch s.Value.Kind() {
        case metrics.KindUint64:
            fmt.Printf("%s = %d\n", s.Name, s.Value.Uint64())
        case metrics.KindFloat64:
            fmt.Printf("%s = %.6f\n", s.Name, s.Value.Float64())
        case metrics.KindFloat64Histogram:
            h := s.Value.Float64Histogram()
            fmt.Printf("%s = histogram (buckets: %d)\n", s.Name, len(h.Buckets))
        }
    }
}
```

### Key Runtime Metrics

| Metric path | What it measures | Historical context |
|-------------|-----------------|-------------------|
| `/gc/pauses:seconds` | GC pause durations | Dropped from 300ms (1.4) to 0.3ms (1.19+) |
| `/gc/cycles/total:gc-cycles` | Total GC cycles | More frequent but shorter with concurrent GC |
| `/sched/goroutines:goroutines` | Goroutine count | Scheduling improved with G-M-P model |
| `/sched/latencies:seconds` | Scheduling latency | Improved with non-cooperative preemption (1.14) |

---

## Apply it

1. Define the user or business outcome that **History of Go — Under the Hood** should improve.
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

- Which measurable outcome justifies investing in History of Go — Under the Hood?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
