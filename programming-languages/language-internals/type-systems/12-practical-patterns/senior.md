# Practical Type-System Patterns — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Practical Type-System Patterns** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Phantom types: compile-time tags, zero runtime cost

A phantom type parameter appears in the type but not in any field:

```rust
use std::marker::PhantomData;

struct Connection<State> {
    socket: Socket,
    _state: PhantomData<State>,   // zero-sized; State carries no data
}

struct Open;
struct Closed;
```

`Connection<Open>` and `Connection<Closed>` have *identical* runtime representation — a `Socket`. `PhantomData<State>` occupies zero bytes. The `State` parameter exists purely so the compiler can distinguish them and offer different methods. That's the whole trick: **attach a fact to a value that the compiler tracks and the CPU never sees.**

### 2. Typestate: methods that only exist in the right state

Define methods on *specific* states, and make transitions return the new-state type:

```rust
impl Connection<Closed> {
    fn open(self) -> Connection<Open> { /* ... */ }   // only Closed can open
}
impl Connection<Open> {
    fn read(&self) -> Vec<u8> { /* ... */ }           // only Open can read
    fn close(self) -> Connection<Closed> { /* ... */ } // consumes self
}

let conn = Connection::<Closed>::new();
let conn = conn.open();      // Closed -> Open
let data = conn.read();      // ✅ Open has read
let conn = conn.close();     // Open -> Closed (conn is moved)
// conn.read();              // ❌ read doesn't exist on Connection<Closed>
```

The key is that `open`/`close` **consume `self`** (take it by value). After `conn.open()`, the old `Connection<Closed>` is *gone* — moved away — so you can't accidentally hold a stale handle in the wrong state. The compiler enforces the protocol: open before read, can't read after close, can't open twice.

### 3. Session-types-lite: a protocol as a type sequence

Generalize typestate to a multi-step protocol. A handshake "send hello → receive ack → send data → close" becomes a chain of types where each step's method returns the next step's type:

```rust
struct Handshake<Step>(Conn, PhantomData<Step>);
struct Start; struct AwaitingAck; struct Ready;

impl Handshake<Start> {
    fn send_hello(self) -> Handshake<AwaitingAck> { /* ... */ }
}
impl Handshake<AwaitingAck> {
    fn recv_ack(self) -> Handshake<Ready> { /* ... */ }
}
impl Handshake<Ready> {
    fn send(self, msg: &[u8]) -> Handshake<Ready> { /* ... */ }
}
```

You physically cannot call `send` before `recv_ack` before `send_hello`. The protocol's grammar is in the types; an out-of-order call is a type error. This is the local, lightweight cousin of full session types.

### 4. Capabilities as types

A token type can represent *authorization*. Holding a `AdminToken` is the proof you're allowed to perform admin actions; the function signature demands it:

```rust
struct AdminToken(());  // only obtainable via authentication

fn delete_user(_cap: &AdminToken, id: UserId) { /* ... */ }
```

`delete_user` cannot be called without an `AdminToken`, and an `AdminToken` can only be minted by the auth module. The capability flows through the type system as a permission slip — you can't forget the check because the check is the *type*.

### 5. Type-driven development: let the holes guide you

Write the type signature, leave the body as a hole, and ask the compiler what's needed:

```haskell
mergeUsers :: User -> User -> Either Conflict User
mergeUsers a b = _            -- typed hole

-- compiler: "hole _ :: Either Conflict User; in scope: a :: User, b :: User, ..."
```

The hole's reported type (`Either Conflict User`) and the in-scope bindings tell you exactly what you must construct from what you have. You refine the hole step by step, the types narrowing the space of valid implementations until — often — there's essentially one thing that typechecks. The slogan: **make the type precise enough that the implementation writes itself.**

### 6. TypeScript's type-level machinery

TS gives you a small functional language *at the type level*. The everyday tools:

- **Mapped + utility types:** `Partial<T>`, `Required<T>`, `Readonly<T>`, `Pick<T, K>`, `Omit<T, K>`, `Record<K, V>` — derive related types instead of hand-writing them.
- **Conditional types + `infer`:** `type ElementType<T> = T extends (infer U)[] ? U : never;` — compute types from types.
- **Template literal types:** `` type Route = `/users/${number}` | `/posts/${string}`; `` — typed routes and keys.
- **`as const`:** freeze a literal into its narrowest type so `["GET","POST"] as const` is a tuple of literal strings, not `string[]`.
- **`satisfies`:** verify a value matches a type *without* losing the precise inferred type — the best of annotation and inference.

```ts
const routes = {
  home: "/",
  user: "/users/:id",
} satisfies Record<string, `/${string}`>;
// routes.user is still the literal "/users/:id", AND the shape was checked
```

### 7. The judgment axis: power vs readability

Every pattern here trades safety for cognitive load. The senior question is *where on that curve does this code belong?*

- A two-state typestate (`Open`/`Closed`) is cheap and obviously worth it.
- A ten-state typestate with conditional-type transitions may produce error messages no teammate can read and refactors only you can do.
- A deeply conditional TS utility type can be a maintenance hazard the team routes around.

The metaprogramming material's "when not to" wisdom applies verbatim: the cleverest version is rarely the right version. Optimize for the *reader* — the colleague debugging this at 2 a.m. who didn't write it. If the type error message is incomprehensible, you've over-built. A simpler type plus a runtime check and a test is sometimes the better engineering choice.

---

## Code Examples

### Rust — full typestate file handle

```rust
use std::marker::PhantomData;

struct Unopened; struct Opened; struct ClosedState;

struct File<S> { fd: i32, _s: PhantomData<S> }

impl File<Unopened> {
    fn new() -> File<Unopened> { File { fd: -1, _s: PhantomData } }
    fn open(self, path: &str) -> File<Opened> {
        let fd = sys_open(path);
        File { fd, _s: PhantomData }
    }
}
impl File<Opened> {
    fn read(&self) -> Vec<u8> { sys_read(self.fd) }
    fn write(&mut self, data: &[u8]) { sys_write(self.fd, data) }
    fn close(self) -> File<ClosedState> {
        sys_close(self.fd);
        File { fd: -1, _s: PhantomData }
    }
}

fn main() {
    let f = File::<Unopened>::new();
    let f = f.open("/etc/hosts");
    let _ = f.read();              // ✅
    let f = f.close();
    // f.read();                   // ❌ File<ClosedState> has no read()
    // File::<Unopened>::new().read(); // ❌ unopened has no read()
}
# fn sys_open(_: &str) -> i32 { 0 }
# fn sys_read(_: i32) -> Vec<u8> { vec![] }
# fn sys_write(_: i32, _: &[u8]) {}
# fn sys_close(_: i32) {}
```

The protocol "open → (read/write)* → close" is enforced entirely by which methods exist on which state, and by `open`/`close` consuming `self` so stale handles can't linger.

### TypeScript — typestate without ownership (return-the-next-type)

TS has no move semantics, so typestate is approximated by returning a new typed handle and trusting callers to use the latest one:

```ts
type Open = { readonly _tag: "open" };
type Closed = { readonly _tag: "closed" };

interface Conn<S> { _s: S; }

function connect(): Conn<Open> { return { _s: { _tag: "open" } }; }
function send(c: Conn<Open>, msg: string): Conn<Open> { /* ... */ return c; }
function close(c: Conn<Open>): Conn<Closed> { return { _s: { _tag: "closed" } }; }

const c = connect();
send(c, "hi");
const c2 = close(c);
// send(c2, "late");   // ❌ Conn<Closed> not assignable to Conn<Open>
```

The caveat: nothing stops you reusing the *old* `c` after `close` (no move). This is the cost of structural typing without ownership — typestate is a *guide*, not an absolute guarantee, in TS.

### TypeScript — template literal types for typed routes

```ts
type HttpMethod = "GET" | "POST" | "PUT" | "DELETE";
type Path = `/${string}`;
type Endpoint = `${HttpMethod} ${Path}`;

const routes = ["GET /users", "POST /users", "DELETE /users/:id"] as const;
type Route = (typeof routes)[number];   // exactly those three literals

function handle(e: Endpoint) { /* ... */ }
handle("GET /users");      // ✅
// handle("PATCH /users"); // ❌ PATCH not in HttpMethod
```

### TypeScript — conditional + mapped types for a typed event map

```ts
type Events = {
  click: { x: number; y: number };
  keypress: { key: string };
  close: {};
};

// A handler map derived from the event map — no hand-duplication:
type Handlers = { [K in keyof Events]: (payload: Events[K]) => void };

function emit<K extends keyof Events>(type: K, payload: Events[K]) { /* ... */ }
emit("click", { x: 1, y: 2 });    // ✅ payload type checked against the key
// emit("click", { key: "a" });   // ❌ wrong payload for "click"
```

### TypeScript — `satisfies` to keep narrow inference

```ts
type Color = "red" | "green" | "blue";

// Without satisfies, `palette.primary` would widen to string.
const palette = {
  primary: "green",
  accent: "blue",
} satisfies Record<string, Color>;

const p: Color = palette.primary;   // ✅ still the literal "green"
```

### Haskell — phantom type for validation state

```haskell
{-# LANGUAGE GADTs, KindSignatures #-}
data Unvalidated
data Validated

newtype Form a = Form FormData     -- `a` is phantom

parseForm :: FormData -> Form Unvalidated
parseForm = Form

validate :: Form Unvalidated -> Either Error (Form Validated)
validate (Form d) = if ok d then Right (Form d) else Left BadForm

save :: Form Validated -> IO ()    -- can ONLY accept validated forms
save (Form d) = persist d
```

`save` cannot be passed a `Form Unvalidated`; the phantom `a` enforces the workflow, with `Form Validated` and `Form Unvalidated` sharing one runtime representation.

### Rust — capability token

```rust
struct DbWriteCap(());

fn authenticate(user: &User) -> Option<DbWriteCap> {
    if user.is_admin { Some(DbWriteCap(())) } else { None }
}
fn delete_all(_cap: &DbWriteCap) { /* destructive */ }

fn main() {
    let user = current_user();
    if let Some(cap) = authenticate(&user) {
        delete_all(&cap);     // ✅ only reachable with the capability
    }
    // delete_all(&DbWriteCap(())); // ❌ can't mint outside this module if field private
}
# struct User { is_admin: bool }
# fn current_user() -> User { User { is_admin: true } }
```

---

## Coding Patterns

### Pattern 1: phantom-state newtype + per-state impls

`struct T<S> { data: D, _s: PhantomData<S> }`, then `impl T<StateA>` / `impl T<StateB>` with state-specific methods. Transitions consume `self`.

### Pattern 2: consume `self` on transition

Always take `self` by value for state-changing methods so the old-state handle is moved away and can't be misused.

### Pattern 3: derive types, don't duplicate them (TS)

Use `Pick`/`Omit`/`Partial`/mapped types to compute `CreateUserDto` from `User`, `UpdateUserDto` from `Partial<User>`, etc. One source of truth.

### Pattern 4: `as const` + indexed access for literal unions

```ts
const STATUSES = ["draft", "live", "archived"] as const;
type Status = (typeof STATUSES)[number];   // "draft" | "live" | "archived"
```

Single source for both the runtime array and the type.

### Pattern 5: type-first, holes-second

Write the signature, leave the body as `todo!()`/`undefined`/`_`, read the expected type, fill incrementally. Let the compiler narrow the space.

### Pattern 6: keep the clever type behind a simple facade

If a powerful conditional type is genuinely needed, hide it behind a clearly-named alias or helper so call sites read simply and only the definition is complex.

---

## Best Practices

- **Model the FSM first, then map it to types.** Don't grow typestate ad hoc; draw the states and transitions, then translate mechanically.
- **Consume `self` (or move) on every transition** in languages that support it — this is what makes the guarantee airtight rather than advisory.
- **Reserve heavy machinery for high-misuse, high-cost surfaces.** Protocols people *will* get wrong, money, security, public APIs. Don't typestate a throwaway internal helper.
- **Optimize for the error message.** Before shipping a clever type, *trigger* the error and read it as a newcomer would. If it's incomprehensible, simplify.
- **Prefer `satisfies` over `as`** in TS to check conformance without throwing away inference or lying to the compiler.
- **Derive related types** with utility/mapped types instead of hand-maintaining parallel definitions that drift.
- **Document the protocol the types encode.** A short comment ("states: Closed→Open→Closed; read only when Open") helps the next reader who can't reverse-engineer the FSM from the impls.
- **Know when to stop.** The metaprogramming "when not to" rule applies: if a simpler type plus a unit test conveys the constraint and the team understands it faster, that's the better engineering. Cleverness is a cost, not a virtue.

---

## Edge Cases & Pitfalls

- **Structural typestate is advisory, not airtight.** In TS, returning a `Conn<Closed>` doesn't *destroy* the old `Conn<Open>` — a caller can still use the stale handle. Document this; don't claim a Rust-grade guarantee.
- **`PhantomData` variance and `Send`/`Sync` surprises (Rust).** The phantom parameter affects auto-trait inference and variance. `PhantomData<*const T>` vs `PhantomData<T>` behave differently; get it wrong and you'll see baffling `Send`/`Sync` errors. Use `PhantomData<fn() -> State>` for invariant tag types when unsure.
- **Combinatorial state explosion.** Tracking *k* independent boolean facts as type parameters yields 2^k states and unreadable signatures. If you reach that, a runtime state field is often clearer.
- **Cryptic error messages.** Deep conditional/mapped types in TS produce errors like `Type 'X' is not assignable to type '...50 lines...'`. This is a real maintenance cost; weigh it.
- **Type-level computation compile-time blowup.** Recursive conditional types and large template-literal unions can slow the TS compiler dramatically or hit recursion limits. Measure build time.
- **Serialization erases phantom state.** A `File<Open>` serialized and deserialized loses its `Open` tag — the wire is untyped. Re-establish state via parsing/constructors on the way back in.
- **Over-abstraction lock-in.** A too-clever type becomes load-bearing; only its author can change it, and refactors stall. This is the same trap metaprogramming warns about — the abstraction outlives the cleverness budget.
- **Phantom types don't add runtime checks.** They steer the *compiler*. If you also need a runtime guarantee (e.g. data from an untyped boundary), you still need a runtime check at that boundary; the phantom only protects the typed region.

---

## Apply it

1. State the system invariant that **Practical Type-System Patterns** must protect.
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

- Which invariant must remain true when Practical Type-System Patterns fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
