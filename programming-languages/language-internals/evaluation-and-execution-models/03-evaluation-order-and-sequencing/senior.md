# Evaluation Order & Sequencing — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Evaluation Order & Sequencing** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The static initialization order fiasco

Within a single translation unit, static/global objects are dynamically initialized **top to bottom** in declaration order. *Across* translation units, the order is **unspecified** — the linker and runtime may construct `.cpp` files' statics in any order. So:

```cpp
// file_a.cpp
extern Logger logger;          // defined in file_b.cpp
Config config = load(logger);  // uses logger during ITS OWN construction
```

```cpp
// file_b.cpp
Logger logger;                 // may or may not be constructed before config
```

If `config`'s constructor runs before `logger` is constructed, it uses a not-yet-built object — undefined behavior, and the bug appears or vanishes depending on link order, compiler, or even the order of object files on the command line. This is the **static initialization order fiasco**.

**The cure — construct on first use.** Replace the eagerly-constructed global with a function that holds a function-local static, whose initialization is guaranteed to happen on first call (and, since C++11, is thread-safe):

```cpp
Logger& logger() {
    static Logger instance;   // constructed on first call; order is now demand-driven
    return instance;
}
```

Now `config`'s construction *calls* `logger()`, which forces `logger` to exist first. The dependency, not the link order, decides the sequence. (Beware the symmetric "static *de*-initialization" order fiasco at shutdown; function-local statics also help here, often via leak-on-purpose or Nifty-Counter idioms.)

### 2. Member initialization order = declaration order

A subtle, frequently-misunderstood rule: a class's members are initialized in the order they are **declared**, *not* the order they appear in the constructor's initializer list.

```cpp
struct Buffer {
    size_t size;
    char*  data;
    Buffer(size_t n) : data(new char[n]), size(n) {}  // looks like data first...
    // ...but 'size' is declared first, so 'size' initializes FIRST, then 'data'.
};
```

This usually doesn't matter — until one member's initializer reads another:

```cpp
struct Bad {
    int b;
    int a;
    Bad(int x) : a(x), b(a + 1) {}   // b is declared first -> b initializes using
                                     // a, which is NOT YET constructed. UB / garbage.
};
```

Compilers warn (`-Wreorder`), but the discipline is: **order your initializer list to match declaration order, and never let one member's initializer depend on a later-declared member.**

### 3. Program order *is* the sequenced-before chain

Here is the unifying insight. The single-thread relation from `middle.md` — *sequenced-before* — is precisely what we informally call **program order**: the order operations would execute if you ran the abstract machine straight down the source. For one thread in isolation, that's the whole story; the compiler/CPU may reorder underneath as long as the *observable* result matches (the as-if rule), so a single thread can never catch itself out of order.

Threads change everything. *Another* thread can observe your operations in an order inconsistent with your program order, because:

- Your **compiler** reordered independent operations (legal under as-if for a single thread).
- The **CPU** executed or retired them out of order, or buffered stores.
- There is no synchronization edge forcing a consistent view.

So: **sequenced-before is per-thread program order; it does not, by itself, order anything between threads.** To get cross-thread ordering you need a *synchronizes-with* edge (release/acquire, lock/unlock, atomic with the right memory order, thread start/join, channel send/receive), which splices two threads' sequenced-before chains into a single **happens-before** order.

### 4. Sequenced-before → happens-before

The memory model defines, roughly:

```
A happens-before B  if:
    A is sequenced-before B (same thread), OR
    A synchronizes-with B (cross-thread sync edge), OR
    transitively via a chain of the above.
```

The first clause is *exactly* the in-expression / in-statement ordering we have been studying. The second is what concurrency adds. The data-race definition then falls out: if two accesses to the same location conflict (one writes) and **neither happens-before the other**, it's a **data race** → undefined behavior in C++/C, "no guarantees" in Java/Go. Evaluation-order sequencing is thus the single-thread foundation that the entire concurrency edifice is built on.

### 5. The as-if rule licenses reordering

The compiler is permitted to do *anything* to your program as long as **observable behavior** is preserved (the **as-if rule**). Observable behavior is: the sequence of I/O, accesses to `volatile` objects, and (C++11+) the synchronization/atomic ordering. Everything else — the order of two independent additions, whether a temporary is materialized, whether a redundant load is elided — is fair game.

Consequences:

- Within one thread, reordering you can't observe is invisible and harmless.
- Across threads, the *same* reordering becomes observable — and is *still legal* unless you established happens-before. That's why "it looked sequential in the source" is not a correctness argument in concurrent code.

### 6. What `volatile` does and does not do

`volatile` is widely misunderstood, so be precise:

**`volatile` DOES:**
- Force each access to actually happen at the abstract-machine level (no eliding repeated reads, no caching the value in a register across a `volatile` read).
- Preserve the *relative order of `volatile` accesses* among themselves (the compiler won't reorder one `volatile` access past another).
- Make sense for memory-mapped I/O registers and `sig_atomic_t` flags touched by signal handlers.

**`volatile` does NOT:**
- Provide atomicity (`volatile int x; x++;` is still a non-atomic read-modify-write).
- Establish happens-before / synchronizes-with between threads. A `volatile` write in one thread does **not** publish your other writes to another thread (this is the *Java* `volatile`, which is a *different* keyword with acquire/release semantics — do not transfer the intuition).
- Emit CPU memory fences in C/C++. It does not stop the *hardware* from reordering relative to *non-volatile* accesses.

So for cross-thread ordering in C/C++, use `std::atomic` (or mutexes), **not** `volatile`. The only correct uses of C/C++ `volatile` are hardware registers and signal flags.

---

## Code Examples

### Example 1 — The fiasco and its cure

```cpp
// PROBLEM (cross-TU eager statics):
// registry.cpp:  Registry g_registry;
// plugin.cpp:    Plugin g_plugin(g_registry);   // g_registry may not exist yet -> UB

// CURE (construct on first use):
Registry& registry() {
    static Registry instance;   // thread-safe, lazy init since C++11
    return instance;
}
// plugin.cpp:  Plugin g_plugin(registry());   // forces registry() before use
```

### Example 2 — Member-init order bug, caught by reordering the list

```cpp
struct View {
    int width;
    int height;
    int area;
    // BUG: area declared last but if it were declared first and read width/height...
    View(int w, int h) : width(w), height(h), area(w * h) {}  // OK: matches decl order
};
```

If you reorder the list to `: area(width*height), width(w), height(h)`, the compiler warns (`-Wreorder`) because `area` (declared last) *appears* first in the list but actually initializes last — and if `area` read `width`/`height` it would read uninitialized members. Keep list order = declaration order.

### Example 3 — Sequenced-before is NOT cross-thread ordering

```cpp
// Thread 1:
data = 42;          // (1)
ready = true;       // (2)  -- sequenced-before nothing across threads!

// Thread 2:
if (ready)          // (3)
    use(data);      // (4)  -- may read data == 0!
```

Although (1) is sequenced-before (2) in thread 1's program order, thread 2 has **no happens-before edge** to (1) or (2). The compiler or CPU may publish `ready` before `data`, or thread 2 may see them out of order. The fix is a synchronization edge:

```cpp
std::atomic<bool> ready{false};
// Thread 1: data = 42; ready.store(true, std::memory_order_release);
// Thread 2: if (ready.load(std::memory_order_acquire)) use(data);  // now ordered
```

### Example 4 — `volatile` does not fix the above

```cpp
volatile bool ready = false;   // STILL WRONG for thread publication.
// volatile orders volatile-vs-volatile accesses and prevents the compiler from
// caching 'ready' in a register, but it does NOT publish 'data' (non-volatile) and
// emits no hardware fence. Thread 2 may still see data == 0. Use std::atomic.
```

### Example 5 — Java/Go/Rust contrasts

```java
// Java: 'volatile' HAS acquire/release semantics — different keyword, different meaning.
volatile boolean ready = false;   // a volatile write publishes prior writes (JMM)
```

```go
// Go: no volatile; use channels or sync/atomic. Channel send/receive create happens-before.
// done <- struct{}{}  pairs with  <-done  to order writes before/after.
```

```rust
// Rust: data races are prevented at compile time by the borrow checker for safe code;
// cross-thread sharing requires Send/Sync, and ordering uses std::sync::atomic with Ordering.
```

---

## Coding Patterns

**Pattern: Construct-on-first-use (Meyers singleton).**

```cpp
T& get() { static T instance; return instance; }
```

**Pattern: Match initializer list to declaration order.** Always write the list in the same order members are declared; enable `-Wreorder -Werror`.

**Pattern: Publish with release, consume with acquire.**

```cpp
payload = build();                 // ordinary writes
flag.store(true, std::memory_order_release);   // publish
// reader:
if (flag.load(std::memory_order_acquire)) use(payload);   // consume
```

**Pattern: Reserve `volatile` for hardware/signals only.** Never use it as a threading primitive in C/C++.

---

## Best Practices

1. **Never let one static depend on another across TUs eagerly** — use construct-on-first-use.
2. **Keep initializer-list order identical to declaration order**, and never read a later-declared member in an earlier one's initializer.
3. **Treat single-thread program order as worthless evidence of cross-thread ordering.** Always identify the synchronization edge.
4. **Use `std::atomic` or mutexes — not `volatile` — for inter-thread ordering** in C/C++.
5. **Remember Java/Go/Rust differ:** Java `volatile` *is* a sync primitive; Go uses channels/atomics; Rust enforces it at compile time.
6. **Lean on tooling:** `-Wreorder`, ThreadSanitizer, and static analyzers catch init-order and race issues you can't eyeball.

---

## Edge Cases & Pitfalls

- **Static *de*-initialization order** at shutdown is the mirror fiasco — a destructor using an already-destroyed static. Function-local statics destruct in reverse construction order, which usually (not always) helps.
- **`-Wreorder` is only a warning** — a wrong initializer list compiles silently if warnings are off.
- **`volatile` + multithreading** is the single most common false-fix in legacy C++.
- **`std::memory_order_relaxed`** gives atomicity but *no* ordering — using it where you needed release/acquire reintroduces the publication bug.
- **Const-initialized statics** (constant expressions) are *not* subject to the fiasco — they're statically initialized before dynamic init runs. Only *dynamic* init has the ordering problem.
- **Inline variables / templates** can change which TU "owns" a static and surprise your mental order.

---

## Common Mistakes

| Mistake | Reality |
|---------|---------|
| "Members init in initializer-list order" | They init in *declaration* order. |
| "`volatile` makes my flag thread-safe in C++" | It does not; use `std::atomic`. |
| "If it's sequential in the source, threads see it sequentially" | Only with a happens-before edge. |
| "Cross-TU global init order is left-to-right by file" | It is *unspecified*. |
| "Java `volatile` == C++ `volatile`" | Different semantics; Java's is a real sync primitive. |
| "relaxed atomics order my data writes" | Relaxed gives no ordering; you need release/acquire. |

---

## Apply it

1. State the system invariant that **Evaluation Order & Sequencing** must protect.
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

- Which invariant must remain true when Evaluation Order & Sequencing fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
