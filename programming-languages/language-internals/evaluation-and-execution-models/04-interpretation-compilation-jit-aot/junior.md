# Interpretation, Compilation, JIT, AOT — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Interpretation, Compilation, JIT, AOT** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The CPU only speaks machine code

Your CPU has a fixed instruction set: a finite list of operations encoded as numbers. `0x48 0x01 0xC3` on x86-64 means "add the `rax` register into `rbx`." That's it. Every program, no matter the language, must *eventually* become a stream of these instructions for the CPU to execute. The four strategies are simply **four different times and ways to produce those instructions.**

### 2. Interpretation: do it as you read it

A pure interpreter never produces machine code for *your* program. Instead, the interpreter *itself* is machine code (someone compiled the Python interpreter from C), and it reads your program as data and acts on it.

Think of it like this. To run `x = 2 + 3`, a tree-walking interpreter:

```text
1. Sees the "assignment" node.
2. Evaluates the right side: a "+" node.
3. Evaluates "+"'s children: the numbers 2 and 3.
4. Adds them → 5.
5. Stores 5 into the variable x.
```

The interpreter does steps 1–5 *every time it runs that line.* If that line is in a loop running a million times, it re-does all that bookkeeping a million times. **That bookkeeping overhead is why interpreters are slow.**

### 3. Compilation (AOT): translate everything first

An AOT compiler reads your *entire* program once, translates it all into machine code, and writes out an executable file. When you run that file, the CPU executes your code *directly* — no interpreter in the loop, no per-line bookkeeping. `x = 2 + 3` becomes a couple of machine instructions, and a million-iteration loop is a million iterations of those instructions, nothing more.

This is why C and Go are fast and why they start instantly: by the time you run them, *all the translation work is already done.* The cost is paid once, at build time, by the developer — not every time, at runtime, by the user.

### 4. Bytecode: the popular middle ground

Pure tree-walking is slow. Full AOT to machine code ties you to one CPU and one OS. So most "interpreted" languages do something in between: they **compile your source to bytecode** — a flat, compact, CPU-independent instruction set — and then **interpret the bytecode.**

CPython does this automatically. When you `import mymodule`, Python compiles `mymodule.py` to bytecode and caches it as `mymodule.pyc`. The bytecode looks like:

```text
LOAD_CONST    2
LOAD_CONST    3
BINARY_ADD
STORE_NAME    x
```

This is *much* faster to interpret than walking a tree, because each instruction is simple and the dispatch is a tight loop. **CPython is not "interpreted" in the naïve sense — it is "compiled to bytecode, then the bytecode is interpreted."** Keep that phrase; it dissolves a lot of confusion.

### 5. JIT: interpret first, then compile the hot parts

Here's the clever one. A JIT-based runtime (like Java's HotSpot or JavaScript's V8) *starts* by interpreting bytecode — so startup is reasonably quick and nothing is wasted compiling code that only runs once. But it **watches** which functions and loops run a lot. When a piece of code crosses a "this is hot" threshold, the JIT **compiles that specific code into machine code, right then, while the program is running**, and from then on the program runs that part at native speed.

Why bother, if AOT already gives you native code? Two reasons:

- **You don't pay to compile code that never gets hot.** Most code in a big app runs rarely; compiling all of it (as AOT must) wastes effort. A JIT only compiles what matters.
- **The JIT knows things the AOT compiler couldn't.** It has watched the program run. It *knows* this loop variable is always an integer, that this `if` is almost never taken, that this method is always called on the same type. It can compile *specialized* machine code based on *real runtime behavior.* An AOT compiler has to be conservative because it can't see the future. This is the deep reason a great JIT can sometimes beat AOT at peak performance.

The price of a JIT is **warmup**: at the start, the program runs slowly (interpreting) and *also* spends CPU compiling. Only after warmup does it hit peak speed.

### 6. The spectrum, not the binary

It is tempting to file languages into "compiled" vs "interpreted." That's wrong. It's a **spectrum**:

```text
SLOWER startup-to-peak translation ......... FASTER

Pure tree-walking interpreter
   │
Bytecode interpreter (CPython, Ruby)
   │
Bytecode interpreter + JIT (Java HotSpot, JS V8, .NET, PyPy)
   │
AOT to native (C, C++, Rust, Go)
```

And the categories blur: Java compiles to bytecode (a compile step!) *and* interprets it *and* JITs it. Go is AOT but ships a runtime with a garbage collector. .NET can be JIT'd *or* AOT'd. The four strategies are *ingredients*, and real languages mix them.

### 7. AOT for "managed" languages, and why it came back

For decades, "AOT" meant C/C++/Rust/Go. But recently, languages that traditionally used a JIT (Java, C#) added AOT options: **GraalVM native-image** for Java, **.NET NativeAOT** for C#. Why? Because JIT warmup and memory overhead are *terrible* for short-lived programs:

- A **command-line tool** runs for 50 milliseconds and exits. With a JIT, it never warms up — it pays all the startup cost and gets none of the peak benefit. AOT makes it start instantly.
- A **serverless function** (AWS Lambda, etc.) spins up a fresh process per request burst. JIT warmup happens *on every cold start*, adding latency the user feels. AOT eliminates the warmup entirely.

So AOT "came back" for managed languages, driven by CLIs and serverless cold-starts. The trade-off: AOT gives up the JIT's runtime adaptive specialization, and it struggles with features like reflection (more on that at higher levels).

---

## Code Examples

We'll use one tiny program — *add the numbers 1 to N* — and look at how different strategies treat it. You can run all of these.

### See bytecode in Python (the "compiled to bytecode" reality)

Python compiles your function to bytecode. You can *look* at it:

```python
import dis

def add_to_n(n):
    total = 0
    for i in range(n):
        total += i
    return total

dis.dis(add_to_n)
```

Output (abbreviated) — this is the bytecode CPython *interprets*:

```text
  total = 0
        LOAD_CONST    0 (0)
        STORE_FAST    total

  for i in range(n):
        LOAD_GLOBAL   range
        LOAD_FAST     n
        CALL          1
        GET_ITER
   >>   FOR_ITER      ...

  total += i
        LOAD_FAST     total
        LOAD_FAST     i
        BINARY_OP     +
        STORE_FAST    total
```

Every loop iteration, CPython's interpreter loop fetches and dispatches each of those instructions. That fetch-decode-dispatch overhead, repeated `n` times, is why this Python loop is far slower than the same loop in C.

### See the AOT machine code in C

The same logic in C, AOT-compiled, becomes machine instructions with *no interpreter:*

```c
long add_to_n(long n) {
    long total = 0;
    for (long i = 0; i < n; i++) {
        total += i;
    }
    return total;
}
```

Compile and disassemble:

```bash
gcc -O2 -c add.c -o add.o
objdump -d add.o
```

The loop body is a handful of instructions (a compare, an add, a jump) that the CPU runs directly. No fetch-decode-dispatch of bytecode. This is the "translation already done at build time" payoff.

### Watch a JIT warm up in Java

```java
public class Warmup {
    static long addToN(long n) {
        long total = 0;
        for (long i = 0; i < n; i++) total += i;
        return total;
    }

    public static void main(String[] args) {
        for (int round = 0; round < 8; round++) {
            long start = System.nanoTime();
            long result = 0;
            for (int rep = 0; rep < 1000; rep++) result += addToN(1_000_000);
            long ms = (System.nanoTime() - start) / 1_000_000;
            System.out.printf("round %d: %d ms%n", round, ms);
        }
    }
}
```

Run it. You'll typically see something like:

```text
round 0: 14 ms      <- interpreting, slow
round 1: 11 ms
round 2: 4 ms       <- C1 (baseline JIT) kicked in
round 3: 2 ms
round 4: 1 ms       <- C2 (optimizing JIT) kicked in, fully warmed up
round 5: 1 ms
round 6: 1 ms
round 7: 1 ms
```

The first rounds are slow (the JVM is interpreting bytecode). As `addToN` gets hot, HotSpot compiles it — first with a quick baseline compiler, then with the heavy optimizing compiler — and the time drops by ~10×. **That drop is warmup made visible.** A C or Go version would be at "round 7 speed" from the very first run.

### The Go version: AOT, no warmup

```go
package main

import (
	"fmt"
	"time"
)

func addToN(n int64) int64 {
	var total int64
	for i := int64(0); i < n; i++ {
		total += i
	}
	return total
}

func main() {
	for round := 0; round < 4; round++ {
		start := time.Now()
		var result int64
		for rep := 0; rep < 1000; rep++ {
			result += addToN(1_000_000)
		}
		fmt.Printf("round %d: %v\n", round, time.Since(start))
	}
}
```

Build with `go build` and run. Every round is roughly the same speed — *there is no warmup*, because `go build` already produced native machine code. This is the AOT trade-off in one program: instant peak speed, no adaptivity.

---

## Coding Patterns

### Pattern 1: "Warm up before you measure" (for JIT languages)

Never benchmark the *first* run of JIT'd code — you'll measure the interpreter, not the compiled code. Run the hot path enough to trigger compilation, *then* measure.

```text
// pseudocode
for i in 1..10000: hotFunction()   // warmup — discard these timings
measure: for i in 1..10000: hotFunction()   // now measure
```

(In Java, use the JMH benchmarking framework, which does this correctly for you.)

### Pattern 2: Pick the strategy to fit the lifetime

Before choosing a language/runtime for a component, ask: *how long does this process live, and how often does it start?*

```text
Lives milliseconds, starts constantly (CLI, lambda) → AOT
Lives hours, starts rarely (server, daemon)        → JIT is fine, often best
One-off script, dev convenience first              → interpreter
```

### Pattern 3: Cache the bytecode

If your runtime compiles source to bytecode (Python), let it cache the `.pyc` so it doesn't recompile every launch. This is automatic in CPython; just don't delete `__pycache__` or run with flags that disable it in production.

### Pattern 4: For AOT of managed languages, declare your dynamic surface

When using GraalVM native-image or .NET NativeAOT, anything reflective (loading a class by name at runtime, deserializing arbitrary types) must be declared in a config file, because the AOT compiler removes code it can't see being used. The pattern: enumerate your reflection/serialization needs up front.

---

## Best Practices

- **Stop saying "compiled vs interpreted."** Say what the runtime actually does: "compiled to bytecode then JIT'd," "AOT to native," "tree-walked." Precision prevents confusion.
- **Match the strategy to the workload's lifetime.** Short-lived → AOT; long-lived → JIT is great. This single rule resolves most "which is faster?" arguments.
- **Don't micro-optimize an interpreter the way you'd optimize native code.** In an interpreted language, the win usually comes from *doing fewer interpreted operations* (vectorize with NumPy, push loops into C), not from clever arithmetic tricks.
- **Account for warmup in JIT'd services.** Send synthetic warmup traffic before a new instance takes real load, so users don't hit the slow interpreting phase.
- **Let the bytecode cache work.** Don't fight your runtime's caching of compiled artifacts.
- **Benchmark realistically.** Measure startup *and* steady-state separately — they're different numbers with different winners.

---

## Edge Cases & Pitfalls

- **"Python is compiled" surprises people — and it's true.** Python *does* compile to bytecode. It just interprets that bytecode instead of running it natively. The `.pyc` files are the evidence. Knowing this stops the false belief that "interpreted = no compile step."
- **Benchmarking JIT code cold.** Timing the first call of a Java/JS function measures the interpreter and the warmup, not the optimized code. Beginners conclude "Java is slow" from a benchmark that never warmed up.
- **Assuming AOT is always faster than JIT.** At *startup*, yes. At *peak*, a good JIT can match or beat AOT because it specializes on real runtime data the AOT compiler couldn't see.
- **Expecting reflection to work under AOT.** GraalVM native-image and .NET NativeAOT operate under a "closed-world" assumption: they need to see all reachable code at build time. Code that loads classes dynamically can break unless you configure it.
- **Confusing "VM" with "virtual machine."** The JVM and CPython VM are *language* virtual machines that execute bytecode — not hardware virtualization like VirtualBox or VMware. Same word, different thing.
- **Thinking the JIT compiles your whole program.** It doesn't. It compiles only the *hot* parts. Cold code stays interpreted forever — which is fine, because it barely runs.
- **Forgetting that AOT binaries are platform-specific.** A Go binary built for Linux x86-64 won't run on macOS ARM64. You must build per target. Bytecode (a `.jar`, a `.pyc`) is portable; native binaries are not.

---

## Apply it

1. Choose one small, known input for **Interpretation, Compilation, JIT, AOT**.
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

- What problem does Interpretation, Compilation, JIT, AOT solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
