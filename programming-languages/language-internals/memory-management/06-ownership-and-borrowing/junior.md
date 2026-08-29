# Ownership & Borrowing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Ownership & Borrowing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Rule 1 — Each value has exactly one owner

When you write `let s = String::from("hello");`, the variable `s` *owns* that string. There is exactly one owner. Not zero, not two — one.

### Rule 2 — Ownership moves; the old name becomes invalid

If you assign the value to another variable or pass it to a function, ownership **moves**. The original variable is now "empty" and the compiler refuses to let you use it.

```rust
let a = String::from("hi");
let b = a;          // ownership MOVES from a to b
// println!("{a}"); // COMPILE ERROR: value borrowed after move
println!("{b}");    // fine — b is the owner now
```

This feels strange at first. In most languages `let b = a;` just makes both names point at the same thing. In Rust, allowing both to be "owners" would mean *two* variables think they must free the same memory — a classic **double-free** bug. Rust prevents it by making the move invalidate `a`.

### Rule 3 — When the owner goes out of scope, the value is dropped

```rust
{
    let s = String::from("hello"); // s owns the string
    // ... use s ...
}                                  // s goes out of scope -> string is freed automatically
```

You never write `free`. The closing brace does it. This is deterministic: it happens at a known point in the code, every time, with no GC deciding "later."

### Borrowing — using a value without owning it

Moving everything around would be exhausting. Usually you just want to *read* or *modify* a value and give it back. That is **borrowing**, written with `&`:

```rust
fn length(s: &String) -> usize { // borrows s, does not own it
    s.len()
}

let text = String::from("hello");
let n = length(&text); // lend text to the function
println!("{text} has {n} chars"); // text is still usable here!
```

Two kinds of borrows exist, and one core rule governs them:

- **`&T`** — a **shared** (read-only) reference. You can have *many* at once.
- **`&mut T`** — a **mutable** (read-write) reference. You can have *only one*, and no shared ones at the same time.

The one-sentence rule: **either many readers, or one writer — never both at the same time.** This is sometimes called *aliasing XOR mutability*. It is the single most important rule in this whole topic, and it is what stops whole classes of bugs.

## Code Examples

### Move on function call

```rust
fn consume(s: String) {        // takes ownership
    println!("consumed {s}");
} // s dropped here

fn main() {
    let msg = String::from("bye");
    consume(msg);              // msg MOVED into consume
    // println!("{msg}");      // ERROR: msg was moved away
}
```

To keep using `msg`, borrow instead:

```rust
fn peek(s: &String) {          // borrows
    println!("peeking {s}");
}

fn main() {
    let msg = String::from("bye");
    peek(&msg);                // lend it
    peek(&msg);                // lend it again — fine
    println!("still have {msg}"); // still owned here
}
```

### Copy types don't move

```rust
fn main() {
    let x = 5;
    let y = x;        // COPY, not move — integers are cheap
    println!("{x} {y}"); // both valid: prints 5 5
}
```

Integers, booleans, chars, floats, and tuples of those are `Copy`. They are duplicated, so the original stays valid. Strings, vectors, and most structs are *not* `Copy` — they move.

### Many readers OR one writer

```rust
fn main() {
    let mut v = vec![1, 2, 3];

    let r1 = &v;       // shared borrow
    let r2 = &v;       // another shared borrow — OK, many readers
    println!("{r1:?} {r2:?}");

    let m = &mut v;    // mutable borrow — OK now, the shared ones are done
    m.push(4);
    println!("{m:?}");
}
```

If you tried to take `&mut v` *while* `r1` was still in use, the compiler would reject it: you cannot have a writer and a reader live at once.

## Best Practices

- **Default to borrowing.** If a function only needs to read or temporarily modify a value, take `&T` or `&mut T`, not ownership. Take ownership only when the function truly needs to keep or consume the value.
- **Let scopes do the cleanup.** Don't fight the system trying to free things manually; arrange your scopes so values drop where you want.
- **Read move errors literally.** "value borrowed after move" means: you used a variable after its ownership left. The fix is usually to borrow instead of move, or to `.clone()` if you genuinely need two copies.
- **Reach for `.clone()` sparingly but without shame as a beginner.** Cloning makes an independent copy and sidesteps a move error. It costs performance, so you'll learn to remove unnecessary clones later — but early on it's a fine way to keep moving.

## Edge Cases & Pitfalls

- **"Why can't I use `a` after `let b = a;`?"** Because `String` moved. With an integer it would have copied and `a` would still work. The difference is whether the type is `Copy`.
- **Borrowing and then moving.** You cannot move a value while it's borrowed. Finish using the reference first.
- **Returning a reference to a local.** A function can't return `&` to a variable it created, because that variable is dropped when the function ends — the reference would dangle. The compiler stops you. (You'll learn the fix — lifetimes — at the middle level.)
- **`mut` is two different things.** `let mut x` means *you may reassign or mutate `x`*. `&mut x` means *a mutable borrow*. Both use the word "mut" but they are different ideas.

---

## Apply it

1. Choose one small, known input for **Ownership & Borrowing**.
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

- What problem does Ownership & Borrowing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
