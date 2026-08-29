# JIT Compilation & Tiering — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **JIT Compilation & Tiering** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why bytecode starts slow

When you compile a Java file, you do **not** get machine code — you get **bytecode** in a `.class` file. Bytecode is a tidy list of simple operations for an imaginary "virtual machine" (the JVM). JavaScript is even more direct: the browser receives plain source text and turns it into bytecode internally.

The reason bytecode exists is portability: the same `.class` file runs on an x86 laptop, an ARM phone, and a mainframe. But the CPU cannot execute bytecode. Something has to bridge the gap. The simplest bridge is an **interpreter**: a big loop that reads one bytecode instruction, does what it says, reads the next, and so on.

The interpreter works everywhere and starts instantly — there is nothing to compile. But it is slow, often **10× to 100× slower** than native code, because for every tiny operation (`add two numbers`) it pays overhead: fetch the bytecode, figure out what it means, jump to the handler, do the work. The actual "add" is one CPU instruction; the bookkeeping around it is dozens.

### 2. The JIT's bargain: spend time to save time

Compiling a function to machine code costs CPU time *now*. If a function only ever runs once (say, your `main()` startup logic), compiling it is a waste — you would spend more time compiling than you would ever save. But if a function runs **a million times** inside a loop, then paying to compile it once and running the fast version a million times is an enormous win.

So the runtime makes a bet on every function: *is this going to run often enough that compiling it pays off?* It cannot know the future, so it **counts**. Every method has an invocation counter. Every loop has a back-edge counter (counting how many times the loop jumped back to the top). When a counter crosses a threshold, the runtime concludes "this is hot" and hands the method to the JIT.

This is why **cold code stays interpreted forever**. Your error-handling branch that runs once a week never gets compiled, and that is correct — compiling it would be pure waste.

### 3. Tiered compilation: fast-and-rough, then slow-and-good

Here is a tension. A *good* optimizing compiler is slow — it analyzes the code deeply and produces excellent machine code. But if you make every hot method wait for the slow compiler, the program stays in the slow interpreter for a long time. That hurts startup.

The solution is **tiers**. Think of it as a ladder:

1. **Interpreter** — instant, no compilation, slowest execution.
2. **A quick compiler** ("baseline" or "template" JIT) — compiles fast, produces decent (not great) machine code. Gets you off the interpreter quickly.
3. **An optimizing compiler** — compiles slowly, produces excellent machine code. Reserved for the *hottest* methods that have proven they deserve the investment.

A method climbs the ladder. It starts interpreted. When it gets warm, the quick compiler gives it decent machine code right away. While that decent code runs, the runtime keeps gathering **profiling data** about it. When it gets *truly* hot, the optimizing compiler uses all that gathered data to produce a highly tuned version, and the method graduates to the top tier.

This is the best of both worlds: fast startup (the quick tier) **and** fast steady state (the top tier), with the expensive compiler only used where it pays.

### 4. Counters and thresholds (the simple version)

The runtime keeps two main counts per method:

- **Invocation counter** — how many times the method was entered.
- **Back-edge counter** — how many times a loop inside the method jumped back to its start.

The back-edge counter matters because of a special case: imagine `main()` contains one giant loop that runs ten million times. The *method* `main` was only called **once**, so its invocation counter is stuck at 1. But the loop inside is blazing hot. If we only watched invocation counters, we would never compile it. The back-edge counter catches this.

When a counter passes its threshold, the method is queued for compilation. The threshold is just a tuned number — high enough that one-shot code never qualifies, low enough that genuinely hot code gets compiled promptly.

### 5. On-Stack Replacement (OSR), gently

Back to that giant loop in `main()`. Suppose it has already run two million times in the interpreter and the back-edge counter finally trips. We want to switch to compiled code — but the loop is **still running right now**, in the middle of iteration two million. We cannot wait for `main()` to be called again, because it never will be.

**On-Stack Replacement** is the trick that swaps the running, interpreted loop for a compiled version *mid-flight*. The runtime compiles the loop, then carefully transfers the current state (the loop variable, the partial results) from the interpreter's world into the compiled code's world, and jumps into the compiled loop at the right iteration. The loop never stops; it just suddenly gets faster. As a junior, you only need to know that this exists and *why* — long-running loops would otherwise be stuck slow forever.

### 6. Why warmup happens (and why it confuses people)

Put the pieces together and warmup is obvious:

- **Second 0:** everything is interpreted. Slow.
- **Second 1:** hot methods get quick-tier compilation. Faster.
- **Second 5:** the hottest methods reach the top optimizing tier. Full speed.

So the *same program* gets faster over its first several seconds without you changing anything. If you measure its speed at second 0 and announce "this language is slow," you measured warmup, not the language.

This is also why **a fresh process is slow**. After a deploy or a restart, every JIT-managed service starts cold and has to warm up all over again. Senior engineers plan for this; juniors are surprised by it.

---

## Code Examples

The point of these examples is to *observe* the JIT, not to write one. We will run small programs and ask the runtime to show its work.

### Example 1 — Feeling warmup in Java

```java
public class Warmup {
    // A function the JIT will eventually compile because we call it a lot.
    static long work(long n) {
        long sum = 0;
        for (long i = 0; i < n; i++) {
            sum += (i * 31) ^ (i >> 3);
        }
        return sum;
    }

    public static void main(String[] args) {
        // Run the same work() many times and time each batch.
        for (int round = 0; round < 10; round++) {
            long start = System.nanoTime();
            long acc = 0;
            for (int k = 0; k < 1000; k++) {
                acc += work(10_000);
            }
            long ms = (System.nanoTime() - start) / 1_000_000;
            System.out.println("round " + round + ": " + ms + " ms (acc=" + acc + ")");
        }
    }
}
```

Run it and watch the timings. The first few rounds are noticeably slower; then the time per round drops and flattens out. That drop is the JIT compiling `work()` and `main`'s loop. You did not change the code between rounds — the *runtime* changed how it was executed.

### Example 2 — Asking the JVM to narrate

The JVM can print every compilation it performs:

```bash
java -XX:+PrintCompilation Warmup
```

You will see a stream of lines like:

```text
  45    1       3       Warmup::work (28 bytes)
  46    2       4       Warmup::work (28 bytes)
```

Each line is a compilation event. The number after the method name region (the `3` then `4` above) is the **tier**: tier 3 is a quick profiling compile; tier 4 is the top optimizing compile. Seeing `work` appear first at a low tier and later at tier 4 *is* tiered compilation happening in front of you. (You do not need to memorize the exact columns — just recognize "my method got compiled, then recompiled at a higher tier.")

### Example 3 — Turning the top tier off

You can ask the JVM to stop at a lower tier and never use the heavy optimizing compiler:

```bash
java -XX:TieredStopAtLevel=1 Warmup
```

Now compare its steady-state speed to the default. It will usually be **slower** in steady state, because the best optimizations (the ones in the top tier) are now disabled. But it may *start* faster, because it never pays for the expensive compiles. This single experiment makes the whole startup-versus-throughput trade-off concrete.

### Example 4 — The same idea in Node.js (V8)

```js
// warmup.js
function work(n) {
  let sum = 0;
  for (let i = 0; i < n; i++) {
    sum += (i * 31) ^ (i >> 3);
  }
  return sum;
}

for (let round = 0; round < 10; round++) {
  const start = process.hrtime.bigint();
  let acc = 0;
  for (let k = 0; k < 1000; k++) acc += work(10000);
  const ms = Number(process.hrtime.bigint() - start) / 1e6;
  console.log(`round ${round}: ${ms.toFixed(1)} ms`);
}
```

Run with V8's optimization trace:

```bash
node --trace-opt --trace-deopt warmup.js
```

You will see lines saying V8 is *optimizing* `work` (it climbed to a higher tier) and, if anything surprises it, *deoptimizing* it. Same lesson as Java: the function starts slow, gets compiled, and speeds up — and the runtime will happily tell you when it does.

### Example 5 — A benchmark mistake you must never make

```java
// WRONG: this "benchmark" measures warmup, not steady-state speed.
long start = System.nanoTime();
long r = work(10_000_000);   // called exactly ONCE, all interpreted
long ms = (System.nanoTime() - start) / 1_000_000;
System.out.println(ms + " ms");   // reports the SLOW interpreted time
```

Because `work` is called once, the JIT may never compile it (or compiles it via OSR only partway through). The number you print is the cold, interpreted speed — which is *not* how the function performs in a real long-running program. The fix is to call the code thousands of times to let it warm up, **then** start timing. This is exactly why real benchmark tools (JMH for Java, `benchmark.js` for Node) force a warmup phase before measuring.

---

## Coding Patterns

These are habits that help you *work with* a JIT rather than against it. None require you to understand the JIT internals.

**Pattern 1 — Always warm up before benchmarking.**

```text
for a few thousand iterations:   # warmup: let the JIT compile
    run the code, ignore the time
now start the timer
for many iterations:             # measurement: steady state
    run the code
report the measured time
```

Or better: use a real harness (JMH, `benchmark.js`) that does this correctly for you.

**Pattern 2 — Write predictable, monomorphic code on hot paths.** A JIT optimizes best when a hot call site sees *one* concrete type. If a hot loop sometimes processes `Cat`, sometimes `Dog`, sometimes `int`, sometimes `String`, the JIT cannot specialize and produces slower code. Keep hot loops type-consistent. (You will hear the word "monomorphic" — it just means "one shape.")

**Pattern 3 — Keep hot methods small enough to inline.** The JIT's biggest win is **inlining** — pasting a small called method into its caller. Enormous methods do not get inlined and block optimization. Small, focused methods on the hot path tend to get inlined and run faster, which (pleasantly) is also good clean-code advice.

**Pattern 4 — Don't micro-optimize cold code.** Hand-tuning a startup routine or an error handler is wasted effort — it stays interpreted and runs rarely. Spend optimization energy where the counters are high, not where *you* think it looks slow.

---

## Best Practices

- **Measure steady state, not warmup.** Run the workload until timings stabilize before you trust any number. Most "language X is slow" claims are warmup measurements.
- **Let the runtime tell you what it did.** `-XX:+PrintCompilation` (JVM) and `--trace-opt`/`--trace-deopt` (Node/V8) are free narration. Use them when you are confused about performance.
- **Prefer the defaults until you can prove otherwise.** Tiered compilation defaults are tuned by people who do this full-time. Reach for `-XX:TieredStopAtLevel` and friends only with a measurement in hand.
- **Keep hot paths type-stable and simple.** Consistent types and small methods are what the optimizing tier rewards.
- **Plan for warmup in deploys.** If a fresh process is slow, consider sending it some traffic to warm up before it serves real users, or rolling deploys so not everything is cold at once. (Deeper strategies are in `professional.md`.)
- **Don't fight the JIT with clever code.** Obscure "fast" tricks often *defeat* the JIT (they confuse its assumptions). Clear, idiomatic code usually optimizes better than clever code.

---

## Edge Cases & Pitfalls

**Pitfall 1 — Benchmarking a single call.** Calling a function once and timing it measures the interpreter, not the JIT. Always warm up. (See Example 5.)

**Pitfall 2 — Dead-code elimination eating your benchmark.** If your benchmark computes a result and never uses it, the JIT may legally *delete the whole computation* and report an impossibly fast time. Always consume the result (print it, accumulate it, return it). This is the single most common reason a microbenchmark reports "0 ms."

**Pitfall 3 — Thinking warmup is a bug.** It is not. It is the JIT doing its job. The "bug" is usually a benchmark that measured the wrong phase, or a deployment that did not account for cold starts.

**Pitfall 4 — Believing "compiled = always faster."** A method only gets compiled if the runtime decides it is hot. Cold methods stay interpreted *on purpose*, and that is correct. Not every line of your program runs as native code.

**Pitfall 5 — Mixing types on a hot path.** A loop that processes a list of mixed types prevents the JIT from specializing and silently runs slower. This is invisible in the source; only profiling or trace flags reveal it. (The deeper version — "megamorphic call sites" — is covered in `senior.md`.)

**Pitfall 6 — Restarting under load.** Restarting a JIT-based service drops all its warm, compiled code. If you restart every instance at once under heavy traffic, the whole fleet is cold and slow simultaneously — a self-inflicted outage. Roll restarts.

**Pitfall 7 — Assuming the first run reflects the program.** Profilers, demos, and "quick tests" that run once show you cold numbers. Real behavior emerges only after the program has run for a while.

---

## Apply it

1. Choose one small, known input for **JIT Compilation & Tiering**.
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

- What problem does JIT Compilation & Tiering solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
