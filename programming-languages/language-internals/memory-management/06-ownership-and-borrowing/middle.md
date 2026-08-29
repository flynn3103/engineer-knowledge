# Ownership & Borrowing — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Ownership & Borrowing** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Lifetimes are regions, not durations

A lifetime is *not* "how long in seconds." It is a **region of code** — a set of program points — over which a reference must remain valid. The core safety property is one sentence:

> A borrow must not outlive the value it points to.

If you borrow `&x`, that reference's lifetime must end before `x` is dropped. The compiler checks this by comparing regions.

### Lifetime elision: why you rarely write `'a`

Most functions never mention lifetimes because three **elision rules** fill them in:

1. Each elided input reference gets its own distinct lifetime.
2. If there is exactly one input lifetime, it is assigned to all output references.
3. If there is a `&self` or `&mut self`, its lifetime is assigned to all output references.

So `fn first(s: &str) -> &str` is shorthand for `fn first<'a>(s: &'a str) -> &'a str`: the returned reference lives as long as the input. You only write lifetimes explicitly when elision can't decide — typically when a function takes *multiple* references and returns one, and the compiler can't tell which input the output borrows from.

```rust
// Ambiguous: does the result borrow from x or y? You must say.
fn longest<'a>(x: &'a str, y: &'a str) -> &'a str {
    if x.len() > y.len() { x } else { y }
}
```

The `'a` here means: "the returned reference is valid for the *shorter* of the regions that `x` and `y` are valid for." It's a constraint, not an instruction to allocate anything.

### Aliasing XOR mutability, formalized

At any program point, for any given value, you may have **either**:

- any number of shared references `&T` (readers), **or**
- exactly one mutable reference `&mut T` (a writer),

**but never both at once.** This is the rule that:

- prevents **data races** (a data race requires two accesses, at least one a write, with no synchronization — impossible if writes are exclusive),
- prevents **iterator invalidation** (you can't hold a `&` into a `Vec` while something else holds a `&mut` to push and reallocate it),
- enables aggressive optimization (the compiler knows a `&T` won't change underneath it).

### NLL — borrows end at last use

The original borrow checker tied a borrow to its lexical scope (the enclosing `{}`). **Non-lexical lifetimes** changed that: a borrow lasts only until its **last use**. This made huge numbers of correct programs compile.

```rust
let mut v = vec![1, 2, 3];
let first = &v[0];      // shared borrow starts
println!("{first}");    // ...last use of `first` here
v.push(4);              // OK under NLL: the shared borrow already ended
```

Under the old rules this was an error because `first` was "alive" until the end of the block. Under NLL the borrow is dead after the `println!`, so the `&mut` from `push` is fine.

## Code Examples

### A lifetime error and its fix

```rust
fn dangling() -> &String {     // ERROR: missing lifetime / returns ref to local
    let s = String::from("hi");
    &s                         // s is dropped at the `}` — ref would dangle
}
```

The compiler rejects this because the returned reference would point at freed memory. Fixes: return the owned `String` (move it out), or take the data as a parameter and return a borrow of *that*:

```rust
fn first_word(s: &str) -> &str {   // elided: output borrows from input
    s.split(' ').next().unwrap_or("")
}
```

### Structs that hold references need lifetimes

```rust
struct Excerpt<'a> {
    part: &'a str,    // the struct cannot outlive the str it points into
}

fn main() {
    let novel = String::from("Call me Ishmael. Some years ago...");
    let first_sentence = novel.split('.').next().unwrap();
    let e = Excerpt { part: first_sentence }; // e tied to `novel`'s lifetime
    println!("{}", e.part);
} // novel dropped here; e already done — fine
```

### Box: single owner on the heap

```rust
let boxed: Box<i32> = Box::new(5);   // i32 lives on the heap, one owner
println!("{}", *boxed);              // deref to read
// boxed dropped at scope end -> heap freed
```

`Box` is the simplest escape hatch: it's needed for recursive types (a type that contains itself) and for owning a value whose size isn't known at compile time (trait objects, `Box<dyn Trait>`).

### Rc/Arc: shared ownership

```rust
use std::rc::Rc;

let a = Rc::new(String::from("shared"));
let b = Rc::clone(&a);     // both own it; refcount = 2 (no deep copy)
let c = Rc::clone(&a);     // refcount = 3
println!("count = {}", Rc::strong_count(&a)); // 3
// value freed only when the LAST Rc drops (count hits 0)
```

`Rc::clone` is cheap — it bumps a counter, it does not copy the string. Use `Arc` (atomic refcount) when sharing across threads; `Rc` is single-threaded only and the compiler enforces that.

### RefCell: interior mutability

```rust
use std::cell::RefCell;

let cell = RefCell::new(vec![1, 2, 3]);
cell.borrow_mut().push(4);            // mutate through a shared handle
println!("{:?}", cell.borrow());     // [1, 2, 3, 4]

// Violating the rule panics at RUNTIME, not compile time:
let _a = cell.borrow_mut();
// let _b = cell.borrow_mut();        // PANIC: already mutably borrowed
```

`Rc<RefCell<T>>` is the common combination for "shared, mutable, single-threaded" data (e.g., nodes in a tree you need to edit). The thread-safe analogue is `Arc<Mutex<T>>`.

## Coding Patterns

- **Take `&str`, not `&String`; `&[T]`, not `&Vec<T>`.** Borrowing the slice type makes functions accept more callers (string literals, sub-slices) and signals "I only read this."
- **Return owned data to break a borrow dependency.** If a returned reference would tangle lifetimes, returning an owned `String`/`Vec` decouples the caller. Measure before assuming the clone matters.
- **`Rc<RefCell<T>>` for shared-mutable single-threaded graphs; `Arc<Mutex<T>>` across threads.** This is the standard recipe when the static checker can't express your sharing.
- **`Weak<T>` for back-pointers.** In a parent→child tree where children also point to parents, make the child→parent edge a `Weak` so the `Rc` cycle can't leak.

## Best Practices

- **Don't add lifetime annotations until the compiler asks.** Let elision work; reach for `'a` only when you get a "missing lifetime specifier" error, and read it as "tell me which input the output borrows from."
- **Prefer the static checker over `RefCell`.** Interior mutability is a tool, not a default. Every `RefCell` is a borrow check you moved to runtime — only do it when the compile-time version is genuinely impossible to express.
- **Audit `Rc` graphs for cycles.** If two `Rc`s can point at each other, you have a leak. Make one direction `Weak`.
- **Keep `&mut` borrows short.** Thanks to NLL, finishing with a mutable borrow quickly frees the value for other uses; long-lived `&mut` borrows are the usual cause of "cannot borrow as X" errors.

## Edge Cases & Pitfalls

- **`RefCell` double-borrow panic.** `borrow_mut()` while another borrow is live panics at runtime. This is the price of interior mutability; it can hide in conditional code paths.
- **`Rc` cycles leak memory.** `a → b → a` keeps both refcounts ≥ 1 forever; neither is ever freed. This is the one way to leak in safe Rust, and it's why `Weak` exists.
- **"Cannot return reference to temporary."** Returning `&` to something created inside the function (or to a temporary) is rejected; the value dies at the function boundary.
- **Self-referential structs.** A struct that holds a reference into *its own* field cannot be expressed with normal lifetimes (if it moves, the reference dangles). This is a real wall — the senior/professional pages cover `Pin` and why linked lists are hard.
- **`Cell` vs `RefCell`.** `Cell<T>` gives interior mutability by *replacing* the whole value (`get`/`set`, `T: Copy`), with no runtime borrow tracking and no panic risk; `RefCell<T>` hands out references and tracks borrows at runtime. Use `Cell` for small `Copy` values, `RefCell` when you need a reference to the inner data.

---

## Apply it

1. Find a real component where **Ownership & Borrowing** affects an interface or dependency.
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

- Which boundary is most affected by Ownership & Borrowing?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
