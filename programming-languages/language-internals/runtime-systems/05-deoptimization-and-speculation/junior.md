# Deoptimization & Speculation — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Deoptimization & Speculation** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Your code does not start fast — it *becomes* fast

When you run `node script.js` or launch a Java program, the runtime does **not** stop to compile everything into optimal machine code first. That would make startup painfully slow. Instead it uses **tiers**:

```text
Tier 0:  Interpreter         — runs immediately, slow per op
Tier 1:  Baseline compiler   — quick compile, modest speedup        (V8 Sparkplug, HotSpot C1)
Tier 2+: Optimizing compiler — slow compile, biggest speedup        (V8 TurboFan, HotSpot C2)
```

The runtime *profiles* your program as it runs — counting how many times each function is called, what types flow through each operation — and **promotes** the hottest code up the tiers. Optimization happens *lazily*, only where it pays off.

### 2. To go fast, the compiler must assume things it can't prove

Consider this tiny JavaScript function:

```js
function add(a, b) {
  return a + b;
}
```

In JavaScript, `+` is wildly general. It can add two numbers, concatenate two strings, coerce an object to a string, add a boolean to a number, and so on. The *fully correct* machine code for `a + b` has to check the types of `a` and `b` and dispatch to one of many behaviors. That's slow.

But suppose, while profiling, the engine notices that **every single time** `add` has been called, both `a` and `b` were small integers. It now *bets* that this will keep being true and emits machine code that does essentially one CPU `ADD` instruction — as fast as C. That bet is **speculation**.

### 3. The bet always comes with a guard

The engine is not reckless. Alongside the fast `ADD`, it inserts a **guard**: a cheap check at the top, like *"if `a` is not a small integer, or `b` is not a small integer, abandon ship."* In pseudocode the optimized `add` looks like:

```text
optimized_add(a, b):
    if not isSmallInt(a): DEOPT      # guard
    if not isSmallInt(b): DEOPT      # guard
    return a + b                     # single fast integer add
```

The guards are cheap — a tag check and a branch — far cheaper than the general "figure out what `+` means" logic. As long as the guards pass, you get near-C speed.

### 4. Deoptimization: what happens when a guard fails

Now someone calls `add("hello", "world")`. The guard `isSmallInt(a)` fails. The optimized code **cannot** continue — it has no string-concatenation logic; it was compiled assuming integers. So the engine performs a **deoptimization**:

1. It **stops** running the optimized native code at the guard.
2. It **reconstructs** the state the program would have been in if the slow interpreter had been running this function all along — the values of `a`, `b`, any locals, where in the function we are.
3. It **resumes** execution in the interpreter (or baseline tier) from that point.
4. The interpreter handles `"hello" + "world"` correctly, producing `"helloworld"`.

The crucial point: **the program produced the correct answer.** Deopt is not an error and not a crash. It's a controlled fallback that trades speed for the generality the situation now requires.

### 5. Semantics are *always* preserved — this is the law

This is the single most important idea on this page. **Speculation and deoptimization never change what your program computes.** They only change *how fast* it computes it. The guard + deopt machinery exists precisely to guarantee that the fast path is only ever taken when it would produce the identical result to the slow path. If there is any chance the fast path would be wrong, the guard fails and you fall back to code that is guaranteed correct.

So you never debug a "deopt produced the wrong number" bug — it can't happen. You only ever debug a "my code is slow because it keeps deopting" *performance* problem. Keep that distinction sharp.

### 6. The expensive failure mode: deopt loops

A single deopt is cheap and harmless. The problem is when it happens **over and over**. Imagine your `add` function gets optimized for integers, then deopts when a string shows up, then gets re-optimized, then a string shows up again, deopts again… The engine spends all its time compiling and throwing away code instead of running it. This is a **deopt loop** or **deopt storm**, and it can make code *slower than if it had never been optimized at all*. Most of this topic, at higher tiers, is about recognizing and preventing this.

---

## Code Examples

The examples below are deliberately small. The point is to *see* speculation and deopt with your own eyes by turning on the engine's tracing.

### Example 1: Watch V8 deoptimize a JavaScript function

```js
// add.js
function add(a, b) {
  return a + b;
}

// Warm it up with integers so V8 optimizes it for SMIs.
let total = 0;
for (let i = 0; i < 1_000_000; i++) {
  total += add(i, i + 1);   // always integers -> monomorphic, optimized
}

// Now break the assumption ONCE.
console.log(add("hello", "world"));   // string -> guard fails -> deopt

console.log(total);
```

Run it with V8's tracing flags (works in Node.js):

```bash
node --trace-opt --trace-deopt add.js
```

You'll see lines like:

```text
[marking 0x... <JSFunction add> for optimized recompilation, reason: hot ...]
[completed optimizing 0x... <JSFunction add (...)>]
...
[deoptimizing (DEOPT eager): begin 0x... <JSFunction add> ...]
  ;;; deoptimize at <add.js:3:12>, not a Smi
```

That `not a Smi` is the engine telling you: *the guard that checked "is this a small integer" failed.* The fast version got abandoned and execution fell back. The program still printed `helloworld` and the correct `total`.

### Example 2: A self-inflicted deopt loop (anti-pattern)

```js
// loop-deopt.js
function classify(x) {
  return x + 1;          // engine will specialize this for the type it sees
}

for (let i = 0; i < 1_000_000; i++) {
  // Alternate between number and string every iteration.
  const arg = (i % 2 === 0) ? i : String(i);
  classify(arg);          // type flips constantly -> repeated deopts
}
```

Run with `node --trace-deopt loop-deopt.js` and you'll see deopt messages firing repeatedly. The function can never *settle* on a single specialization because you keep changing the input type. This is the deopt-storm shape in miniature — and it's exactly what to avoid.

The fix is trivial: **don't mix types into the same hot function.** Keep numbers with numbers and strings with strings.

### Example 3: The same idea on the JVM (HotSpot)

Java is statically typed, so you won't get *type* deopts the way JS does. But HotSpot speculates on *which method a virtual call lands on* (class-hierarchy analysis) and on *which branches are taken*. You can watch compilation and deopt activity:

```bash
java -XX:+UnlockDiagnosticVMOptions \
     -XX:+PrintCompilation \
     -XX:+TraceDeoptimization \
     YourProgram
```

In `PrintCompilation` output, a method tagged with `%` is an *on-stack-replacement* (a hot loop compiled mid-run), and a method later marked `made not entrant` or `made zombie` is one whose optimized code was invalidated — often because the runtime had to deoptimize after an assumption (like "this method is never overridden") was broken when a new class loaded. You don't need to read every line as a junior; the goal is to *see that it happens*.

### Example 4: Proving semantics are preserved

```js
// correctness.js
function half(x) {
  return x / 2;
}

// Optimize for integers.
for (let i = 0; i < 1_000_000; i++) half(i);

// Now feed it values that break the int assumption — fractions, big numbers.
console.log(half(7));        // 3.5  -> correct
console.log(half(2 ** 40));  // 549755813888 -> correct, even after deopt
console.log(half(NaN));      // NaN -> correct
```

No matter how many guards fail and how many deopts occur, every printed value is mathematically correct. Speed varies; **answers do not.**

---

## Coding Patterns

### Pattern 1: Keep types monomorphic in hot functions

```js
// ❌ Mixed types feed the same function -> polymorphic -> deopts.
function size(x) { return x.length; }
size([1, 2, 3]);     // array
size("abc");          // string
size({ length: 9 }); // object

// ✅ If a function is hot, feed it ONE shape/type consistently,
//    or split into specialized functions.
function arrSize(a) { return a.length; }   // only ever arrays
function strSize(s) { return s.length; }   // only ever strings
```

### Pattern 2: Initialize objects with all fields up front (stable shape)

```js
// ❌ Adding fields later mutates the hidden class -> shape churn -> deopts.
const p = {};
p.x = 1;
p.y = 2;       // each assignment can transition the hidden class

// ✅ Declare the full shape at construction so the hidden class is fixed.
const p2 = { x: 1, y: 2 };
```

### Pattern 3: Keep numeric arrays homogeneous

```js
// ❌ Mixing integers and floats can force the array out of its fast
//    integer representation.
const a = [1, 2, 3];
a.push(3.14);   // representation may transition

// ✅ Decide up front: all integers, or all doubles.
const ints = [1, 2, 3, 4];
const dbls = [1.0, 2.5, 3.14];
```

### Pattern 4: Don't leave holes in arrays

```js
// ❌ "Holey" array — the engine can't assume every slot is present.
const a = [];
a[0] = 1;
a[100] = 2;   // indices 1..99 are holes -> slow, deopt-prone path

// ✅ Fill densely / use the right size from the start.
const b = new Array(101).fill(0);
b[0] = 1;
b[100] = 2;
```

---

## Best Practices

- **Be predictable.** The single best thing you can do is feed hot functions consistent types and consistent object shapes. The JIT rewards consistency.
- **Measure before you worry.** Most functions are never hot enough to be optimized. Only chase deopts in code the profiler says is actually hot.
- **Turn on the trace when investigating.** `node --trace-deopt` and `-XX:+PrintCompilation` turn an invisible problem into a readable log.
- **Separate the slow path.** If a function is *usually* called with integers but *sometimes* with something weird, consider routing the weird case to a different function so the hot one stays monomorphic.
- **Don't micro-optimize blindly.** "JIT-friendly" patterns matter in genuine hot paths and almost nowhere else. Readability wins in cold code.
- **Trust correctness.** Never suspect deopt of producing wrong results. If your numbers are wrong, it's a logic bug, not the JIT.

---

## Edge Cases & Pitfalls

### Pitfall 1: Thinking a deopt is an error

A deopt log line looks alarming, but a *few* deopts during warm-up are completely normal — the engine is feeling out your program's behavior. Only **repeated** deopts on the **same** hot function are a problem.

### Pitfall 2: Mixing `int` and `double` in numeric code

In JS, `1` (a small integer) and `1.0`/`3.14` (a double) are represented differently. A loop that mostly works on integers but occasionally produces a fraction can keep tripping the integer guard. Pick one numeric domain for a hot loop.

### Pitfall 3: Building objects field-by-field

Every time you add a new property to an object, you may transition its hidden class. If you do this inside a hot loop, or build "the same kind of object" two different ways in two places, you create multiple shapes for what should be one — and that confuses speculation.

### Pitfall 4: Using `arguments` or `try/catch` in old engines (legacy gotcha)

Historically, certain JS constructs (`arguments`, `eval`, `with`, `try/catch`) disabled or hampered optimization entirely. Modern V8 handles most of these far better than it used to, but `arguments` in particular is still worth avoiding in hot code — prefer rest parameters (`...args`).

### Pitfall 5: Assuming the fast path always runs

You wrote "fast" code, but if its guards keep failing, the fast path is *never taken*. The optimized version exists in memory but execution keeps bailing to the slow tier. Always confirm with a trace before assuming your hot path is actually hot *and* stable.

### Pitfall 6: Expecting Java type-deopts like JS

Java is statically typed, so you won't get "wrong type" deopts. Java's deopts come from *other* speculations: an assumed-final method getting overridden by a newly loaded class, a branch the compiler pruned suddenly being taken, or a null-check that was speculated away. Different triggers, same mechanism.

---

## Apply it

1. Choose one small, known input for **Deoptimization & Speculation**.
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

- What problem does Deoptimization & Speculation solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
