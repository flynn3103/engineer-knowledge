# Side Channels & Spectre — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Side Channels & Spectre** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The output is not the only observable

When you reason about a function, you think about inputs and the returned value. A security analyst thinks about everything an attacker can *observe*:

- **Time:** how many nanoseconds (or milliseconds) it ran.
- **Memory access pattern:** which addresses / cache lines it touched.
- **Power:** how much current it drew (relevant for smartcards, IoT, hardware tokens).
- **Electromagnetic emission:** the faint radio noise the chip emits while switching.
- **Sound:** yes — capacitors and coils on a board emit a faint whine that correlates with what the CPU is doing (acoustic cryptanalysis is real, though exotic).

If *any* of these observables changes depending on the *secret*, you have a side channel. The fix is always the same shape: make the observable **independent of the secret**.

### 2. The canonical leak: early-exit comparison

Look closely at how a normal string/byte comparison works:

```text
compare(a, b):
    for i in 0..len:
        if a[i] != b[i]:
            return false      # <-- stops HERE, early
    return true
```

That `return false` is the whole problem. The number of loop iterations executed depends on **how many leading characters matched** — which depends on the secret. Concretely:

- Guess `Xxxxxxxx` vs secret `password` → mismatch at index 0 → loop runs **1** iteration.
- Guess `pxxxxxxx` vs secret `password` → mismatch at index 1 → loop runs **2** iterations.
- Guess `paxxxxxx` vs secret `password` → mismatch at index 2 → loop runs **3** iterations.

The function takes slightly longer the more leading characters you get right. An attacker times each guess, notices that `p...` is consistently a tiny bit slower than `X...`, concludes the first character is `p`, then attacks the second character, and so on. Instead of guessing a 16-character secret (astronomically hard), they guess it **one character at a time** (trivially easy). The math collapses from "impossible" to "a few thousand requests."

This is not a hypothetical. Timing attacks on MAC and token comparison are a recurring real-world vulnerability class.

### 3. The cure: constant-time comparison

To compare two secrets without leaking, you must **always look at every byte** and **combine the results without branching**:

```text
constant_time_equal(a, b):           # assume same length
    diff = 0
    for i in 0..len:
        diff |= a[i] XOR b[i]        # accumulate differences, never branch
    return diff == 0
```

Walk through it. `a[i] XOR b[i]` is `0` when the bytes match and non-zero when they differ. We `OR` (`|=`) every result into `diff`. After the loop, `diff` is `0` if *and only if* every byte matched. Crucially:

- The loop **always runs the full length** — no early exit.
- There is **no branch inside the loop** that depends on the secret.
- The running time depends only on the *length*, which is not secret.

This is the single most important defensive habit in this whole topic. Real languages and crypto libraries give you a ready-made version (see Code Examples). **Use them. Never compare a secret with `==`, `memcmp`, or `.equals()`.**

### 4. Cache attacks: watching which memory you touched

Timing the *whole function* is the simplest channel. A sharper one watches *which memory addresses* you touched, using the cache. The intuition you need now:

- Reading data that is **in the cache** is fast. Reading data that is **not** (a cache miss, goes to RAM) is much slower — and the difference is large enough to measure with a clock.
- So an attacker can ask: "Did the victim recently touch *this particular* cache line?" by timing how long *they* take to read it. Fast read → the victim loaded it (it is cached). Slow read → the victim did not.

Why does that leak a secret? Because some code touches **different memory depending on secret data**. A classic example: an encryption routine that uses a secret key byte as an *index* into a lookup table (`table[key_byte]`). Which table entry it reads — and therefore which cache line gets loaded — reveals the value of that key byte. By watching the cache, the attacker reads the key out of the *access pattern*, never touching the key directly. (You will meet the named techniques — Flush+Reload, Prime+Probe — in `middle.md`.)

The defense rhymes with constant-time comparison: **do not let secrets steer which memory you touch.** Don't index tables with secret bytes; don't branch to different code based on secret bits.

### 5. Power, EM, and acoustic channels (brief)

On a smartcard, a hardware security key, or an IoT chip, an attacker may have *physical access* and can put a probe on the power line or near the chip. The current the chip draws depends on what it is computing — a `1` bit and a `0` bit flip different numbers of transistors and draw measurably different power. **Power analysis** (especially "differential power analysis") can extract keys from a chip by averaging thousands of power traces. EM (electromagnetic) and acoustic channels are the same idea through different physics. As a junior writing application code, you will rarely defend against these directly — they are the domain of hardware and embedded-crypto engineers — but you should know they exist, because they explain why secure hardware (HSMs, secure enclaves, smartcards) is engineered so carefully.

### 6. The modern headline: Spectre and Meltdown (intuition only)

In 2018 the world learned that the CPU itself contains a side channel, built into a *performance optimization* present in nearly every processor made in the previous two decades. Here is the intuition; the mechanism is in `middle.md`.

Modern CPUs do not patiently wait to find out whether an `if` is true before continuing. They **guess** (this is *speculative execution* and *out-of-order execution*) and race ahead, executing instructions *past* the branch on the assumption their guess is right. If the guess was right, great — free speed. If wrong, the CPU **rolls back** the wrong work so your program never officially sees it.

The catch: the rollback is *incomplete*. The CPU undoes the **architectural** state (registers, memory) — but it does **not** undo the **microarchitectural** state, specifically *the cache*. During the wrongly-speculated run, the CPU may have loaded some data into the cache based on a secret. That data load is rolled back logically, but the *cache line it pulled in stays warm*. Now the attacker uses a cache attack (Core Concept 4) to detect which line is warm — and reads out the secret that the speculation "should never have touched."

That is the whole trick: **architectural state is rolled back; microarchitectural state is not; the gap between them is a covert channel.** **Spectre** tricks a program into speculating past a bounds check and leaking via the cache. **Meltdown** transiently reads privileged (kernel) memory before the "you're not allowed" fault is delivered. Both forced enormous, expensive changes across the entire industry — browsers, operating systems, and cloud platforms — which is why this topic matters far beyond academic curiosity.

---

## Code Examples

### The bug: leaky token comparison (do **not** do this)

```python
# INSECURE — early-exit comparison leaks via timing.
def check_token(submitted: str, correct: str) -> bool:
    return submitted == correct          # stops at first mismatching char
```

```java
// INSECURE — String.equals short-circuits on the first difference.
boolean checkToken(String submitted, String correct) {
    return submitted.equals(correct);
}
```

```c
/* INSECURE — memcmp returns as soon as it finds a differing byte. */
int check_token(const unsigned char *submitted, const unsigned char *correct, size_t n) {
    return memcmp(submitted, correct, n) == 0;
}
```

All three are functionally correct and all three leak. The leak is the *early exit*.

### The fix: use the library's constant-time comparison

Do not hand-roll crypto — use the vetted function your platform already ships:

```python
# Python: hmac.compare_digest is constant-time for equal-length inputs.
import hmac
def check_token(submitted: str, correct: str) -> bool:
    return hmac.compare_digest(submitted, correct)
```

```java
// Java: MessageDigest.isEqual is constant-time (since Java 6u17).
import java.security.MessageDigest;
boolean checkToken(byte[] submitted, byte[] correct) {
    return MessageDigest.isEqual(submitted, correct);
}
```

```go
// Go: subtle.ConstantTimeCompare returns 1 if equal, 0 otherwise.
import "crypto/subtle"
func checkToken(submitted, correct []byte) bool {
    return subtle.ConstantTimeCompare(submitted, correct) == 1
}
```

```c
/* C with libsodium: sodium_memcmp is constant-time. */
#include <sodium.h>
int check_token(const unsigned char *a, const unsigned char *b, size_t n) {
    return sodium_memcmp(a, b, n) == 0; /* 0 == equal */
}
```

### What "constant-time" looks like under the hood

You will normally call the library, but it helps to see the shape so you recognize it:

```c
/* Conceptual constant-time byte comparison. Always scans all n bytes,
 * never branches on the data. (Real libraries also guard against the
 * compiler "optimizing" the constant-timeness away.) */
int ct_equal(const unsigned char *a, const unsigned char *b, size_t n) {
    unsigned char diff = 0;
    for (size_t i = 0; i < n; i++) {
        diff |= a[i] ^ b[i];   /* accumulate; no early return */
    }
    return diff == 0;          /* one branch at the very end, on a non-secret bit */
}
```

> ⚠️ **Length is not secret here, but be careful:** if the two inputs can have *different* lengths and you bail out early on a length mismatch, you have leaked the length. For tokens and MACs, hash or pad to a fixed length, or use a library function designed for the case.

### Don't index memory with a secret (cache-attack surface)

```c
/* RISKY: which table entry (and cache line) is loaded depends on the secret.
 * This pattern is how naive table-based AES leaked keys via cache attacks. */
unsigned char sub = sbox[secret_byte];   /* memory access steered by a secret */
```

The defensive replacement is to use hardware crypto instructions (e.g., AES-NI) or a bitsliced/constant-time implementation that does not index tables by secret data. As a junior: **don't roll your own crypto; call a vetted library that has already solved this.**

---

## Coding Patterns

**Pattern: constant-time equality, always.** Any time the values being compared include a secret, route through a constant-time comparison function. Make it a code-review checklist item.

**Pattern: fixed-length, fixed-work.** Where you can, make the work independent of the secret: compare hashes of fixed length, pad inputs, process all elements rather than stopping early.

**Pattern: lean on the library.** Crypto libraries (`hmac`, `crypto/subtle`, `MessageDigest`, libsodium, BoringSSL) have already solved constant-time comparison and constant-time crypto. Calling them is the pattern; re-implementing them is the anti-pattern.

**Pattern: don't branch or index on secrets.** If a branch condition or an array index is derived from a secret, that is a side-channel smell. Restructure so the secret only flows through arithmetic/bitwise operations, never through control flow or addresses.

---

## Best Practices

1. **Never compare secrets with `==`, `memcmp`, or `.equals()`.** Use `hmac.compare_digest`, `crypto/subtle.ConstantTimeCompare`, `MessageDigest.isEqual`, or `sodium_memcmp`.
2. **Don't roll your own crypto.** The vetted libraries have already handled constant-time comparison, constant-time table lookups, and blinding. You will get it subtly wrong.
3. **Treat timing as an output.** When a function handles a secret, ask: "Does its running time depend on the secret?" If yes, fix it.
4. **Keep secret data out of control flow and addresses.** No secret-dependent branches; no secret-dependent array indices.
5. **Keep your platform patched.** Spectre/Meltdown mitigations ship as OS, microcode, browser, and compiler updates. Applying them is most of the practical defense for application developers.
6. **Understand *why* your platform is slower.** KPTI, retpolines, and site isolation cost performance — that cost is the price of closing these channels, not a bug.

---

## Edge Cases & Pitfalls

- **"It passed all my tests" is not safety.** Side channels are invisible to functional tests. A leaky comparison and a constant-time one return identical values for every input — they differ only in timing.
- **Early-exit hidden inside a library call.** `==`, `strcmp`, `Arrays.equals`, and `memcmp` all short-circuit. The leak hides inside the standard library you trusted.
- **Comparing different-length inputs leaks the length.** If you `return false` immediately when lengths differ, you've revealed the secret's length. Hash first, or use a function designed for it.
- **The compiler can "optimize away" your constant-time code.** A clever compiler may notice it can short-circuit your careful loop and reintroduce a branch. This is exactly why you use the library's version, which is written to resist that.
- **High-resolution timers help attackers.** Browsers deliberately reduced timer precision and restricted `SharedArrayBuffer` after Spectre to make timing the cache harder — a reminder that even "read the clock" can be an attack tool.
- **Logging timing of secret operations.** If you log "auth check took 1.3ms," you may be *publishing* the side channel. Be careful what you measure and expose.
- **Assuming Spectre is "only a CPU/OS problem."** It is mostly mitigated below your code — but in shared environments (browsers running untrusted JS, multi-tenant clouds) the *reason* your platform isolates processes is to contain these attacks. Don't disable those protections to chase performance without understanding the cost.

---

## Apply it

1. Choose one small, known input for **Side Channels & Spectre**.
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

- What problem does Side Channels & Spectre solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
