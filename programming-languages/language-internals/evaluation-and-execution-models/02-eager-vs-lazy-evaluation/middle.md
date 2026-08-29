# Eager vs. Lazy Evaluation — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Eager vs. Lazy Evaluation** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Universal Shape: Lazy Steps, Eager Consumers

Every lazy-pipeline API in every language splits operations into two kinds:

- **Lazy (intermediate):** `map`, `filter`, `take`, `Select`, `Where`, `Skip`. These return a *new lazy sequence* and do **no work**.
- **Strict (terminal):** `toList`/`collect`/`sum`/`count`/`forEach`/`reduce`/materializing into an array. These **pull** values through the whole chain and trigger every recorded step.

```python
# Python: filter and map are lazy; list(...) is the terminal that forces it all.
pipeline = map(lambda x: x * x, filter(lambda x: x % 2 == 0, range(10)))
# Nothing has run. 'pipeline' is a lazy iterator.
result = list(pipeline)   # NOW the filter and map run, element by element.
```

The mental rule: **building the pipeline is free; consuming it is where the work lives.** If you forget the terminal operation, you get a sequence object and zero output — the famous "it never ran."

### 2. Infinite Streams: `repeat`, `iterate`, `naturals`

Laziness makes infinite data ordinary. The three canonical generators:

```python
import itertools

# repeat: same value forever
ones = itertools.repeat(1)                       # 1, 1, 1, ...

# count: naturals (iterate with +1)
naturals = itertools.count(0)                    # 0, 1, 2, ...

# iterate-style: seed, f(seed), f(f(seed)), ... (hand-rolled)
def iterate(f, seed):
    x = seed
    while True:
        yield x
        x = f(x)

powers_of_two = iterate(lambda x: x * 2, 1)      # 1, 2, 4, 8, ...
print(list(itertools.islice(powers_of_two, 6)))  # [1, 2, 4, 8, 16, 32]
```

None of these would terminate eagerly. Laziness lets you *describe* the whole infinite sequence and pull a finite slice with `islice` / `takeWhile`.

### 3. The Fibonacci Stream

The Fibonacci sequence is the textbook lazy-stream example because each element depends on the previous two, and you want as many as you ask for — no more:

```python
def fibonacci():
    a, b = 0, 1
    while True:
        yield a
        a, b = b, a + b

import itertools
print(list(itertools.islice(fibonacci(), 10)))
# [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]
```

The stream is infinite and self-referential in spirit ("the next Fib is the sum of the last two"), but the generator computes exactly the elements you pull. Ask for 10, compute 10. Ask for a million, compute a million. The *description* is bounded; the *data* is unbounded.

### 4. The Sieve of Eratosthenes — Lazily

The sieve is the canonical "generate-and-filter" lazy program. Generate `2, 3, 4, 5, …`; the first is prime; remove every multiple of it; recurse on the rest. Eagerly this needs a bounded array. Lazily it produces primes forever:

```python
def sieve(stream):
    p = next(stream)
    yield p
    # Lazily filter out multiples of p, then recurse on the rest.
    yield from sieve(x for x in stream if x % p != 0)

import itertools
primes = sieve(itertools.count(2))
print(list(itertools.islice(primes, 10)))
# [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
```

Each prime found installs a new lazy filter over the stream of candidates. (This is the elegant-but-slow "incremental sieve" — beautiful as a demonstration of generate-and-filter, not as a fast primality engine. The point is the *shape*: an unbounded source, layered lazy filters, pull as many as you want.)

### 5. Generate-and-Filter: the Modularity Win

Lazy sequences let you separate *generation* from *selection* with no efficiency penalty. The classic argument (from the paper *Why Functional Programming Matters*): eagerly, "generate all candidates then take the best" wastes work because you build the whole candidate list. Lazily, "generate" and "take the best" *fuse* — generation stops the moment the consumer stops asking.

```python
# Newton's method square root: generate an infinite stream of approximations,
# then lazily take the first one that's "good enough." Generation halts there.
def approximations(n, guess=1.0):
    while True:
        yield guess
        guess = (guess + n / guess) / 2

def within(eps, stream):
    prev = next(stream)
    for cur in stream:
        if abs(cur - prev) < eps:
            return cur
        prev = cur

print(within(1e-9, approximations(2)))   # ~1.41421356
```

`approximations` is infinite; `within` decides when to stop. Neither knows about the other. That separation — possible *only* because generation is lazy — is the modularity payoff.

### 6. Same Idea, Five Languages

The shape is identical; only the names change.

| Concept | Python | JavaScript | C# (LINQ) | Java | Scala |
|---|---|---|---|---|---|
| Lazy source | generator / `itertools` | `function*` | `IEnumerable<T>` | `Stream<T>` | `LazyList` |
| Lazy map | `map` / genexpr | manual / lib | `.Select()` | `.map()` | `.map()` |
| Lazy filter | `filter` | manual / lib | `.Where()` | `.filter()` | `.filter()` |
| Bound it | `islice`, `takewhile` | `take` helper | `.Take()` | `.limit()` | `.take()` |
| Terminal | `list()`, `sum()` | `[...gen]`, loop | `.ToList()`, `foreach` | `.collect()`, `.count()` | `.toList`, `.force` |
| Single-value lazy | — | — | `Lazy<T>` | `Supplier<T>` | `lazy val` |
| Deferred argument | `lambda` thunk | arrow thunk | `Func<T>` | `Supplier<T>` | by-name `=> A` |

---

## Code Examples

### JavaScript: generators and a lazy `take`

```javascript
function* naturals() {
  let n = 0;
  while (true) yield n++;          // infinite, but lazy
}

function* take(n, iterable) {
  let i = 0;
  for (const x of iterable) {
    if (i++ >= n) return;          // stop early — pulls only n values
    yield x;
  }
}

console.log([...take(5, naturals())]);   // [0, 1, 2, 3, 4]
```

### C#: LINQ deferred execution and the multiple-enumeration trap

```csharp
// Deferred: Where + Select do NOTHING here. No DB call, no iteration.
IEnumerable<int> query = numbers
    .Where(x => { Console.WriteLine($"filtering {x}"); return x % 2 == 0; })
    .Select(x => x * x);

// First enumeration — NOW the Where runs.
var list1 = query.ToList();

// Second enumeration — the Where runs AGAIN. The work is duplicated!
var count = query.Count();   // re-filters everything

// Fix: materialize once.
var cached = query.ToList();   // run the work a single time
var c1 = cached.Count;
var c2 = cached.Sum();         // reuse — no re-run
```

This is the **multiple enumeration** bug: a deferred `IEnumerable` is cold, so each consuming call (`ToList`, `Count`, a `foreach`) re-executes the entire pipeline. If the source is a database or network call, you pay for it every time. The fix is to materialize (`.ToList()` / `.ToArray()`) when you'll consume more than once.

### C#: the modified-closure trap with deferred queries

```csharp
// Pre-C# 5 / classic trap: the lambda captures the LOOP VARIABLE, not its value.
var queries = new List<IEnumerable<int>>();
for (int threshold = 0; threshold < 3; threshold++)
    queries.Add(numbers.Where(x => x > threshold));   // captures 'threshold'

// Because the queries are DEFERRED, none ran during the loop.
// By the time we enumerate, 'threshold' == 3 for ALL of them.
foreach (var q in queries)
    Console.WriteLine(q.Count());   // all use threshold == 3

// Fix: copy the loop variable into a local captured per-iteration.
for (int t = 0; t < 3; t++) {
    int local = t;                                    // fresh binding each pass
    queries.Add(numbers.Where(x => x > local));
}
```

Deferred execution *amplifies* the closure trap: because the query doesn't run during the loop, the captured variable has moved on by the time it does. (C# `foreach` was later changed to give each iteration a fresh variable, but `for` loops and many other languages still bite here.)

### Java: Stream intermediate vs. terminal

```java
import java.util.stream.*;

// peek/filter/map are INTERMEDIATE (lazy). No "peeking 1" prints yet.
Stream<Integer> s = Stream.of(1, 2, 3, 4, 5)
    .peek(x -> System.out.println("peeking " + x))
    .filter(x -> x % 2 == 0)
    .map(x -> x * 10);

System.out.println("stream built, nothing ran");

// collect is TERMINAL — it forces the pipeline, one element at a time.
var result = s.collect(Collectors.toList());   // now the peeks run, interleaved
System.out.println(result);                     // [20, 40]
```

```java
// Infinite Java stream + limit (the terminal-bounded pattern):
Stream.iterate(0, n -> n + 1)   // infinite, lazy
      .filter(n -> n % 3 == 0)
      .limit(5)                 // still intermediate, but bounds it
      .forEach(System.out::println);   // terminal → 0 3 6 9 12
```

Two Java rules worth memorizing: (1) a stream can be consumed **once** — a second terminal op throws `IllegalStateException` (Java's version of "exhausted"); (2) `limit` on an infinite stream is the standard way to keep the terminal op from running forever.

### Scala: `lazy val` and by-name parameters

```scala
// lazy val: computed at most once, on first access, then cached (memoized thunk).
lazy val config = {
  println("loading config (expensive)")
  loadFromDisk()
}
// 'loading config' has NOT printed yet.
println("about to use config")
println(config.timeout)   // NOW it loads — and only this once
println(config.retries)   // cached; no reload

// By-name parameter: `body: => Unit` is a thunk, re-evaluated on each use.
def repeat(n: Int)(body: => Unit): Unit =
  for (_ <- 1 to n) body          // 'body' re-runs each iteration

repeat(3) { println("hi") }       // prints hi three times
```

The distinction is sharp: `lazy val` runs **once** and memoizes; a **by-name parameter** runs **each time** it is referenced. One is call-by-need (cached); the other is call-by-name (re-evaluated). Both defer the work past the point you wrote it.

### Scala: an infinite `LazyList`

```scala
val fibs: LazyList[BigInt] =
  BigInt(0) #:: BigInt(1) #:: fibs.zip(fibs.tail).map { case (a, b) => a + b }

println(fibs.take(10).toList)   // List(0, 1, 1, 2, 3, 5, 8, 13, 21, 34)
```

`#::` is the lazy cons — the tail is a thunk, so this self-referential definition is well-founded and computes each Fib exactly once (memoized in the `LazyList`).

---

## Coding Patterns

**Pattern: bound an infinite stream at the terminal.** Always pair an infinite source with `take`/`limit`/`takeWhile`/`islice`. Never call a fully-forcing terminal (`toList`, `sum`, `count`) on an unbounded stream.

**Pattern: materialize-once for multiple reads.** If a cold sequence will be consumed more than once, snapshot it: `var data = query.ToList();` in C#, `results = list(gen)` in Python, collect a Java stream into a `List`.

**Pattern: generate-and-filter.** Express the unbounded source separately from the selection logic; let early termination prune generation.

```python
# Find the first 3 perfect squares above 1000.
import itertools
squares = (n * n for n in itertools.count(1))                # generate
big = (s for s in squares if s > 1000)                       # filter
print(list(itertools.islice(big, 3)))                        # take → [1024, 1089, 1156]
```

**Pattern: capture by value, not by variable.** In loops that build deferred work, copy the loop variable into a fresh local (`int local = t;` / `lambda i=i: i`) before capturing it.

**Pattern: keep lazy stages pure.** Put side effects (logging, writes) in the terminal step or outside the pipeline, so their timing is predictable.

---

## Best Practices

- **Memorize intermediate vs. terminal** for whatever API you use. Intermediate = lazy, free, returns a sequence. Terminal = forces, runs the work, returns a value/collection.
- **Treat a cold lazy sequence like a function.** Enumerating it twice means running it twice. Cache if that's expensive.
- **Bound every infinite stream** before a forcing terminal op, or you hang.
- **Don't pass generators across module boundaries** if the caller expects re-readable data — return a `list`/array, or document the one-shot nature loudly.
- **Avoid side effects in `map`/`filter`/`peek`.** Use them for transformation only; do effects in a terminal `forEach` where timing is clear.
- **Watch closures in deferred code.** If a lambda captures a loop variable, copy it locally first.
- **Profile by consumption, not construction.** The cost shows up at the terminal op; that's where to measure.

---

## Edge Cases & Pitfalls

**Pitfall 1: forgetting the terminal op.** `numbers.Where(...)` / `stream.filter(...)` / `(x for x in xs)` with no consumer does nothing. There's no error — just silence. Always end with a terminal op (or know you're intentionally returning a lazy value).

**Pitfall 2: multiple enumeration of a cold source.** `query.Count()` then `query.ToList()` runs the whole pipeline twice. Over a DB, that's two queries. Materialize once.

**Pitfall 3: consuming a one-shot source twice.** Python generators go empty; Java streams throw `IllegalStateException: stream has already been operated upon or closed`. A generator/stream is not a re-readable collection.

**Pitfall 4: `limit`/`take` after a *blocking* infinite op.** `Stream.iterate(...).sorted().limit(5)` hangs — `sorted` is a *stateful* intermediate op that must see *all* elements first, so it never returns on an infinite stream. Only *stateless* intermediates (`map`, `filter`) stay lazy; `sorted`, `distinct` (sometimes) buffer.

**Pitfall 5: deferred side effects firing at the wrong time.** A `peek(println)` or a logging `Select` prints when consumed, not when written, and interleaves with the consumer. Logs look scrambled. Keep effects out of lazy stages.

**Pitfall 6: the modified-closure trap, amplified.** Because deferred queries run *later*, captured loop variables have moved on. Copy to a local before capturing.

**Pitfall 7: laziness hiding exceptions.** An error in a lazy stage doesn't throw when you build the pipeline — it throws when you *consume*, far from the code that caused it. The stack trace points at the terminal op, not the buggy `map`.

---

## Apply it

1. Find a real component where **Eager vs. Lazy Evaluation** affects an interface or dependency.
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

- Which boundary is most affected by Eager vs. Lazy Evaluation?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
