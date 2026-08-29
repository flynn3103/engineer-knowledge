# Practical Type-System Patterns — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Practical Type-System Patterns** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The type system is a proof checker

When you write `function greet(name: string)`, you are asserting a fact: every caller passes a string. The compiler *verifies* it. If somebody passes a number, the build fails. You did not write a test, you did not run the program — the bug simply cannot exist.

The patterns on this page all work the same way. You encode a rule as a type. The compiler enforces the rule everywhere, on every build, forever — including in code you write next year and forgot the rule. **A type is a test that runs on every line at compile time.**

### 2. Make illegal states unrepresentable

Look at this common shape (TypeScript):

```ts
interface RequestState {
  isLoading: boolean;
  data: User | null;
  error: string | null;
}
```

How many states does this describe? `2 × 2 × 2 = 8`. But how many are *valid*? Really only three: *loading*, *loaded with data*, *failed with error*. The other five are nonsense — `isLoading: true` with `data` already present, or `data` and `error` both set. Yet your code can *create* all eight, so somewhere a junior dev will, and the UI will flicker or crash.

The fix is to make the type describe only the three valid states:

```ts
type RequestState =
  | { status: "loading" }
  | { status: "loaded"; data: User }
  | { status: "failed"; error: string };
```

Now there is no way to be loading *and* have data. The nonsense states cannot be typed. **You cannot have a bug in a state you cannot construct.** This is the most important idea on the page, and it is a sum type doing the work.

### 3. Parse, don't validate

The slogan comes from Alexis King. The idea: when untyped input arrives, do the checking *once*, at the boundary, and produce a value whose **type proves** it passed. After that, the rest of your code holds that proven value and never re-checks.

The anti-pattern — *validate* — looks like this:

```ts
function validateEmail(s: string): boolean { /* returns true/false */ }

// ...500 lines later, in some other function:
function sendInvite(email: string) {
  // is `email` valid here? Who knows. Better re-check. Or forget to. 🐛
}
```

The function takes a plain `string`. The fact that it was validated lives only in the programmer's memory. Three call sites later, someone forgets, and an invalid email reaches the mail server.

The *parse* version returns a **new type**:

```ts
function parseEmail(s: string): Email | null { /* ... */ }

function sendInvite(email: Email) {  // can ONLY be called with a parsed Email
  // no re-checking — the type IS the proof
}
```

`sendInvite` literally cannot be called with a raw string. The validity is in the type. Re-validation bugs disappear because there is nothing to re-validate — you already hold the proof.

### 4. Make absence explicit (kill the null)

`null` is the "billion-dollar mistake" because it hides inside every type silently. In old Java, a `String` might be a string *or* `null`, and the compiler said nothing. You found out at runtime, with a `NullPointerException`.

Modern languages fixed this by making nullability **opt-in and visible** in the type:

- **Kotlin:** `String` can never be null. `String?` can. The compiler forces a null check before you use a `String?`.
- **TypeScript (`strictNullChecks`):** `string` excludes `null`/`undefined`. `string | null` includes them, and you must narrow.
- **Swift:** `String` is non-optional. `String?` (an `Optional<String>`) must be unwrapped.
- **Rust / Haskell:** There is no `null` at all. Absence is `Option<T>` / `Maybe a`, a sum type you must pattern-match.

The pattern: **never let "this might be missing" be invisible.** Put it in the type, and the compiler makes you handle it.

### 5. Exhaustiveness: the compiler reminds you of every case

The hidden superpower of sum types is **exhaustive matching**. When you `switch`/`match` over a sum type and the compiler knows you handled every case, you get a guarantee. Better: when you *add* a new case later (say, a `"cancelled"` status), every `switch` that doesn't handle it becomes a **compile error**, pointing you at exactly the code you need to update.

Compare to a `string` status field with `if`/`else if` chains: add a new status and the code silently falls through the `else`. No error, just a quiet bug. The sum type turns "I hope I updated every place" into "the compiler listed every place for me."

### 6. Push checks left (toward compile time)

A theme connecting all five concepts: **move the moment of failure earlier.** A bug caught by the type checker fails on your machine, in the build, with a precise location. The same bug caught at runtime fails on a user's machine, in production, with a stack trace and an incident channel. Same bug — radically different cost. Good type design is the art of dragging failures from runtime to compile-time.

---

## Code Examples

We'll model the same little problem — **the state of a data fetch** and **a validated email** — across languages, plus the null story.

### TypeScript — illegal states unrepresentable

Buggy "bag of flags" version:

```ts
// ❌ 8 representable states, only 3 valid
interface FetchState {
  loading: boolean;
  user?: User;
  error?: string;
}

function render(s: FetchState) {
  if (s.loading) return "Spinner";
  if (s.error) return `Error: ${s.error}`;
  return `Hello ${s.user!.name}`;   // s.user! — the "!" is you lying to the compiler
}
```

Fixed with a discriminated union:

```ts
// ✅ exactly 3 states exist
type FetchState =
  | { status: "loading" }
  | { status: "success"; user: User }
  | { status: "error"; message: string };

function render(s: FetchState): string {
  switch (s.status) {
    case "loading": return "Spinner";
    case "success": return `Hello ${s.user.name}`;  // s.user is guaranteed here
    case "error":   return `Error: ${s.message}`;
  }
}
```

No `!`, no optional chaining, no "is user defined here?" The compiler *knows* `s.user` exists inside `case "success"` and *knows* it doesn't exist elsewhere. Add a fourth case `"cancelled"` and the `switch` won't compile until you handle it (with `strict` settings) — the compiler hands you the to-do list.

### TypeScript — strictNullChecks kills the NPE

```ts
// With "strictNullChecks": true in tsconfig.json

function firstName(user: User | null): string {
  // return user.name;        // ❌ compile error: user is possibly null
  if (user === null) return "Guest";
  return user.name;            // ✅ narrowed to User, safe
}
```

Turning on `strictNullChecks` is the single highest-value config change in a TypeScript project. It converts a class of runtime `Cannot read property 'name' of null` crashes into compile errors.

### Rust — Option and Result instead of null and exceptions

```rust
// No null exists in Rust. Absence is Option<T>.
fn find_user(id: u64, users: &[User]) -> Option<&User> {
    users.iter().find(|u| u.id == id)
}

fn main() {
    let users = load_users();
    match find_user(42, &users) {
        Some(user) => println!("Found {}", user.name),
        None => println!("No such user"),   // compiler FORCES this branch
    }
}
```

You cannot accidentally use a missing value, because there is no value until you've matched `Some`. Errors work the same way with `Result`:

```rust
fn parse_age(s: &str) -> Result<u8, String> {
    s.parse::<u8>().map_err(|_| format!("'{}' is not a valid age", s))
}

// The caller must deal with the error; it's in the type.
match parse_age("twelve") {
    Ok(age) => println!("Age is {}", age),
    Err(msg) => eprintln!("{}", msg),
}
```

### Rust — make illegal states unrepresentable with an enum

```rust
// ❌ if this were a struct with bools, you'd allow nonsense:
//    struct Conn { connected: bool, addr: Option<String>, error: Option<String> }

// ✅ enum: exactly one variant at a time
enum Connection {
    Disconnected,
    Connected { addr: String },
    Failed { reason: String },
}

fn describe(c: &Connection) -> String {
    match c {
        Connection::Disconnected => "not connected".into(),
        Connection::Connected { addr } => format!("connected to {}", addr),
        Connection::Failed { reason } => format!("failed: {}", reason),
    }
}
```

### Kotlin — non-nullable by default

```kotlin
fun lengthOf(s: String): Int = s.length        // s can NEVER be null
fun lengthOrZero(s: String?): Int = s?.length ?: 0  // s? must be handled

fun main() {
    // lengthOf(null)        // ❌ compile error
    println(lengthOf("hi"))  // 2
    println(lengthOrZero(null)) // 0 — the ?: forces a default
}
```

The `?` is the entire null-safety story: a type *with* `?` may be null and the compiler makes you handle it; a type *without* `?` is guaranteed non-null.

### Swift — optionals make absence explicit

```swift
func firstName(of user: User?) -> String {
    guard let user = user else { return "Guest" }  // unwrap or bail
    return user.name
}

// Parsing returns an optional; you must unwrap before use.
let maybeAge = Int("42")     // Int? — could be nil if the string isn't a number
if let age = maybeAge {
    print("Age: \(age)")
}
```

### Haskell — Maybe, the original

```haskell
data User = User { name :: String, age :: Int }

lookupUser :: Int -> [User] -> Maybe User
lookupUser uid = find (\u -> userId u == uid)

greet :: Maybe User -> String
greet Nothing  = "Guest"
greet (Just u) = "Hello " ++ name u   -- compiler forces both cases
```

### The email "parse, don't validate" pattern (TypeScript)

```ts
// A branded type: a string the compiler treats as distinct.
type Email = string & { readonly __brand: "Email" };

function parseEmail(raw: string): Email | null {
  const trimmed = raw.trim().toLowerCase();
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(trimmed)
    ? (trimmed as Email)   // the ONLY place a string becomes an Email
    : null;
}

// This function CANNOT receive an unvalidated string:
function sendWelcome(to: Email) { /* ... */ }

const input = "  ALICE@Example.com  ";
const email = parseEmail(input);
if (email) {
  sendWelcome(email);       // ✅ typechecks
}
// sendWelcome(input);      // ❌ compile error: string is not Email
```

The validity check happens **once**, in `parseEmail`. Everywhere downstream, the `Email` type *is* the proof. No function re-validates.

---

## Coding Patterns

### Pattern 1: The discriminated-union state

Always give the union a literal **tag field** (`status`, `kind`, `type`) so you can `switch` on it:

```ts
type Result<T> = { kind: "ok"; value: T } | { kind: "err"; error: string };
```

### Pattern 2: Parse at the boundary, trust inside

```ts
// boundary.ts  — the ONLY file that touches raw JSON
function parseUser(json: unknown): User | null { /* ...checks... */ }

// everywhere else: functions take `User`, never `unknown` or `any`
```

### Pattern 3: Replace `null` returns with `Option`/optional

```kotlin
// ❌ fun find(id: Int): User      (might return null, type lies)
fun find(id: Int): User? { /* ... */ }   // ✅ honest about absence
```

### Pattern 4: Exhaustive switch with a compile-time guard (TS)

```ts
function area(s: Shape): number {
  switch (s.kind) {
    case "circle": return Math.PI * s.r * s.r;
    case "square": return s.side * s.side;
    default:
      const _exhaustive: never = s;  // ❌ compile error if a case is unhandled
      return _exhaustive;
  }
}
```

The `never` trick makes "you forgot a case" a build failure.

### Pattern 5: Narrow, don't assert

```ts
// ❌ user!.name        — telling the compiler "trust me" (you might be wrong)
// ✅ if (user) { user.name }   — proving it, so the compiler agrees
```

Avoid `!`, `as`, and `any` — each one switches the proof checker off for that spot.

---

## Best Practices

- **Turn on the strict flags.** `strictNullChecks` (TS), warnings-as-errors, Kotlin's null-safety, Swift's optionals — opt into the strongest checking your language offers. It's the cheapest win available.
- **Model states as sum types, not flag bags.** The moment you have two related booleans, ask whether a sum type describes the real states better.
- **Parse once, at the edge.** All raw input gets converted to typed values in a thin boundary layer. The core of your app never sees `any`/`unknown`/raw strings.
- **Return `Option`/`Result`, don't return `null` or throw silently.** Make the "nothing" and "error" cases visible in the signature.
- **Handle every case explicitly.** Prefer exhaustive `switch`/`match` over `if/else` chains on a string field.
- **Avoid escape hatches.** `as any`, `!`, unchecked casts, and force-unwraps (`user!` in Swift) turn off the safety you're trying to build. Use them only with a comment explaining why it's safe.
- **Name types for meaning, not shape.** `Email`, `UserId`, `Cents` — not `string`, `number`. The name carries the rule.

---

## Edge Cases & Pitfalls

- **The `!` / force-unwrap trap.** `user!.name` (TS) or `user!.name` (Swift) silences the null check without proving anything. It crashes at runtime exactly like the null you were avoiding. Narrow instead.
- **`any` poisons everything.** A single `any` in TypeScript spreads — values derived from it lose all checking. Prefer `unknown` and narrow.
- **Validate-then-cast is not parsing.** `if (isEmail(s)) { use(s as Email) }` *works*, but if `isEmail` and the `Email` brand can drift apart, you've lied. Keep the check and the type-production in **one function** (`parseEmail`) so they can't disagree.
- **Optional chaining hides missing handling.** `user?.address?.city` silently produces `undefined` and moves on. Sometimes that's right; sometimes you needed to *handle* the missing user. Don't let `?.` become a way to ignore absence.
- **Non-exhaustive switch on a string.** `switch (status)` over a plain `string` (not a union) gives you no exhaustiveness check. Use a union type so adding a case is a compile error, not a silent fallthrough.
- **Re-introducing null inside the type.** `Email | null | undefined` defeats the point. Decide: either a value exists (`Email`) or you model absence in *one* explicit way (`Email | null`), not three.
- **Trusting the boundary too little or too much.** Data from your *own* database can still violate invariants (an old row written before a rule existed). Parse it too; don't assume internal == valid.

---

## Apply it

1. Choose one small, known input for **Practical Type-System Patterns**.
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

- What problem does Practical Type-System Patterns solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
