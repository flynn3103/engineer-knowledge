# Capability-Based Security — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Capability-Based Security** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Three Rules, Stated to Be Checkable

Treat ocap as a checklist you can run against a design:

- **Rule 1 — No ambient authority.** *Can any component reach a resource without holding a reference to it?* If yes (a global `open`, a static registry, a singleton DB connection, an env-var read), you have ambient authority and the model's guarantees do not hold. The test: delete the import of every authority source and see what still compiles. Anything that still reaches the world was using ambient power.
- **Rule 2 — Propagation only by reference-passing.** *Can a component gain a new capability by any means other than endowment, introduction, or parenthood?* If there is a `lookupByName`, a service locator, a reflection-based `Class.forName(...).newInstance()` that grabs authority, the answer is yes and Rule 2 is broken.
- **Rule 3 — Unforgeability.** *Can a component fabricate a valid capability from data it controls?* Integer-indexed handles you can guess, predictable URLs, type-confusion in an unsafe language — all break unforgeability. In a memory-safe language, references are unforgeable for free; in C or with `unsafe`, you must enforce it.

When all three hold, a component's reachable authority equals the transitive closure of the references it holds — and *nothing else*. That single fact is the whole value proposition.

### 2. Capability vs Facet

A raw capability is the underlying object/handle. A **facet** is a wrapper object that mediates access to it. Facets are how you do everything interesting:

- **Attenuate:** a facet that forwards only `read`, dropping `write`.
- **Revoke:** a facet that forwards until you flip a switch, then forwards to nothing.
- **Log/audit:** a facet that records each use before forwarding.
- **Rate-limit:** a facet that forwards only N times per second.

The holder of a facet cannot tell (and cannot reach) what is behind it. They can only do what the facet exposes. This is the in-process analog of a reverse proxy.

### 3. Attenuation Is the Normal Case, Not the Exception

In a healthy capability design, almost no one holds a *raw* powerful capability. The filesystem authority lives in one place; everyone else holds *attenuated facets*: "a read handle to this one file," "a write handle to this one directory," "an HTTP client locked to this one host." You attenuate **at every hand-off**: when you delegate downstream, you pass the weakest sufficient facet. Over a call graph, authority monotonically *narrows* the further it travels from its source — the opposite of ambient authority, where every callee inherits everything.

### 4. Revocation: The Caretaker Pattern

A raw capability, once handed out, cannot be taken back — the holder has the reference and you cannot reach into their memory. So **you never hand out the raw capability if you might need to revoke.** Instead you hand out a **caretaker**: a forwarding facet that you also hold a control handle to.

```text
   holder ──► [ CARETAKER facet ] ──forwards──► [ real resource ]
                     ▲
                     │ revoke() flips an internal switch
              you hold the control side
```

After `revoke()`, the caretaker forwards to nothing (or throws). The holder still has *their* reference — but it now points at a dead forwarder. You revoked authority without touching the holder's memory. This is the standard, and it composes: a caretaker can wrap a caretaker.

### 5. Delegation and the Diamond

Capabilities delegate transitively: if A gives a (caretaker) capability to B, and B passes it to C, then C can use the resource — *and A can still revoke all of them at once* by killing the original caretaker, because B and C both forward through it. This is far cleaner than ACLs, where revoking a permission that has been re-granted through several layers is a notoriously hard problem ("the revocation problem"). With caretakers, revocation is just "stop forwarding."

### 6. The Powerbox: Where Broad Authority Is Allowed to Live

Total no-ambient-authority would mean no component can ever do anything new. The escape valve is the **powerbox**: a single, trusted, audited component that *does* hold broad authority (the real filesystem, the real network) and whose job is to **hand out narrow, attenuated capabilities** — usually mediated by policy or user consent. The macOS/Windows "open file" dialog is a powerbox: the app has no filesystem authority, but when the user picks a file, the OS hands the app a capability to *that one file*. The user's act of choosing *is* the grant. This keeps the powerful authority in one auditable place and makes grants explicit and intentional.

### 7. Retrofitting Least Authority onto Ordinary Code

Most real code is ambient: it `import os`, `import requests`, reads env vars, opens a global DB pool. You retrofit toward capabilities incrementally:

1. **Find the authority sources.** Grep for `open`, `socket`, `requests`, `os.environ`, `subprocess`, global singletons.
2. **Push them to the edge.** Move every authority acquisition up to a single `main`/composition-root.
3. **Inject downward.** Pass the resulting handles (or attenuated facets) as parameters, so inner modules import *no* authority.
4. **Attenuate at boundaries.** Where a module only needs to read one directory, give it a facet for that directory, not the real `open`.

The end state: a thin "impure shell" at the top that holds all real authority, and a large "capability-pure core" that can only act through what it was handed. This mirrors functional-core/imperative-shell design, but the discipline is about *authority*, not side effects.

---

## Code Examples

### Attenuation by Facet (TypeScript / JS)

```ts
// The raw capability: a full read/write file handle.
interface FileCap {
  read(): string;
  write(data: string): void;
  delete(): void;
}

// A read-only FACET: same shape minus the dangerous methods.
function readOnly(file: FileCap): { read(): string } {
  return { read: () => file.read() };   // forwards read; write/delete unreachable
}

// A logging facet that wraps and observes.
function audited(file: FileCap, log: (m: string) => void): FileCap {
  return {
    read:   ()   => { log("read");          return file.read(); },
    write:  (d)  => { log(`write ${d.length}`); file.write(d); },
    delete: ()   => { log("delete");        file.delete(); },
  };
}

// Hand a plugin the weakest sufficient capability:
runPlugin(readOnly(audited(theFile, console.log)));
// the plugin can ONLY read, and every read is logged.
```

### The Caretaker / Revoker Pattern (JS)

```js
// Wrap any object so its authority can be revoked later.
function makeCaretaker(target) {
  let live = target;                       // the only reference to the real object
  const facet = new Proxy({}, {
    get(_, prop) {
      if (live === null) throw new Error("revoked");
      const v = live[prop];
      return typeof v === "function" ? v.bind(live) : v;
    },
  });
  const revoke = () => { live = null; };   // control side: severs the link
  return { facet, revoke };
}

const { facet, revoke } = makeCaretaker(theBankAccount);
giveToUntrustedCode(facet);   // they hold the facet, not the account
// ... later, on suspicion ...
revoke();                     // every future call through `facet` now throws
```

JavaScript even has this built into the language: `Proxy.revocable(target, handler)` returns `{ proxy, revoke }` for exactly this purpose. The holder keeps their reference; you keep the kill switch.

### Sealer / Unsealer (rights amplification, JS)

```js
// A matched pair: only the unsealer can open what the sealer boxed.
function makeBrand() {
  const boxes = new WeakSet();
  const contents = new WeakMap();
  const seal = (value) => {
    const box = Object.freeze({});         // opaque token
    boxes.add(box); contents.set(box, value);
    return box;                            // can be passed through untrusted code
  };
  const unseal = (box) => {
    if (!boxes.has(box)) throw new Error("not my box");
    return contents.get(box);              // only THIS unsealer recovers it
  };
  return { seal, unseal };
}
// Used to safely carry a privileged value through code that must not read it,
// and to amplify rights: holding BOTH a box and the matching unsealer = access.
```

### Retrofitting: Ambient → Injected (Python)

```python
# BEFORE: ambient authority scattered through the module.
import os, requests
def sync_user(uid):
    data = requests.get(f"https://api.internal/users/{uid}").json()  # any host
    with open(f"/data/{uid}.json", "w") as f:                        # any path
        f.write(str(data))
    return os.environ["SIGNING_KEY"]                                  # any env var

# AFTER: authority injected; the function imports nothing powerful.
def sync_user(http, storage, signing_key, uid):
    data = http.get_user(uid)        # http = client locked to api.internal
    storage.put(f"{uid}.json", data) # storage = facet over ONE directory
    return signing_key               # handed in, not read from the environment

# Composition root (the only place that holds real authority):
def main():
    http    = HostBoundClient("https://api.internal")   # attenuated net
    storage = DirStore("/data")                          # attenuated fs
    key     = os.environ["SIGNING_KEY"]                  # ambient read, ONCE, here
    sync_user(http, storage, key, uid="42")
```

`sync_user` now cannot reach an arbitrary host, an arbitrary path, or the environment. Its entire authority is three parameters, and an auditor can see it at a glance.

### A Powerbox Hand-Out (pseudocode)

```text
# The app holds NO filesystem authority. It asks the powerbox:
chosen = powerbox.requestFile(prompt="Pick a file to import",
                              mode="read")
# The powerbox shows the user a dialog. The user's pick IS the grant.
# The app receives a read-only capability to EXACTLY that one file.
parse(chosen)   # cannot read anything the user didn't choose
```

---

## Coding Patterns

### Pattern 1: Composition root holds all authority

```text
main() {
  net   = attenuate(realNetwork, allow=["api.internal"])
  store = attenuate(realFS, dir="/data")
  app(net, store)        // everything below imports NO authority
}
```

### Pattern 2: Attenuate at every hand-off

```python
def handle_request(req, store):
    tenant_store = store.scoped(req.tenant_id)   # narrow before passing down
    process(req.body, tenant_store)              # process can't cross tenants
```

### Pattern 3: Hand a caretaker when revocation may be needed

```js
const { facet, revoke } = makeCaretaker(resource);
register(plugin, facet);
onUninstall(plugin, revoke);   // revocation designed in, not bolted on
```

### Pattern 4: Facet exposes only what's used

```ts
// Don't pass the whole SDK; pass exactly the verbs you need.
const mailer = { send: (to, body) => sdk.messages.create({ to, body }) };
notifier(mailer);   // notifier cannot list, delete, or read other messages
```

### Pattern 5: Powerbox for user-mediated grants

```text
cap = powerbox.grant(resource="camera", consentPrompt="Allow camera?")
useCamera(cap)   // app had no camera authority until the user said yes
```

---

## Best Practices

- **Establish a single composition root.** All authority enters there; nothing below imports an authority source. This is the structural backbone of capability discipline.
- **Never delegate a raw capability you might revoke.** Interpose a caretaker by default; raw hand-offs are forever.
- **Attenuate before you delegate, every time.** Pass the weakest facet that still works. Authority should narrow as it travels.
- **Keep the powerbox small and audited.** It is your concentrated trusted base; everything broad lives here and nowhere else.
- **Make facets expose verbs, not objects.** Hand `{ send }`, not the whole mail SDK; the shape of the facet *is* the granted authority.
- **Treat tokens (URLs, OAuth) as capabilities, with the same rules.** Unforgeable, attenuated (scoped), revocable (short-lived + a deny list). The macaroon model formalizes this (covered in `senior.md`).
- **Audit by reference closure in review.** Ask "what was this handed, and what does that reach?" rather than "what does the policy say?"

---

## Edge Cases & Pitfalls

- **Ambient leaks through the language runtime.** Even capability-injected code may, in an ordinary language, still do `import os`. Without a runtime that *denies* ambient access (a sandbox, a frozen realm, a capability OS), the discipline is by-convention only — and one careless import breaks it.
- **Over-broad facets.** A facet that forwards `__getattr__`/`get` for *everything* (a naive Proxy) re-exposes the whole object and attenuates nothing. Attenuation means *removing* verbs, not transparently forwarding all of them.
- **Capability leakage via return values.** A facet that *returns* a raw inner object hands out unattenuated authority through the back door. Wrap return values too.
- **Revocation that doesn't cover already-captured state.** If the holder copied data out before you revoked, revocation stops *future* access, not past extraction. Capabilities control *authority*, not *information already obtained*.
- **Caretaker chains and identity.** Wrapping breaks object identity (`===`), and a holder may rely on identity for equality/maps. Design facets so identity-sensitive code still works, or document the break.
- **Sealer/unsealer used as a covert channel.** A pair shared across a boundary can smuggle authority past an auditor who only follows ordinary references. Treat sealer pairs as authority and audit them.
- **The powerbox becomes a god object.** If everything routes through one powerbox that grants generously, you've recreated ambient authority with extra steps. The powerbox must grant *narrowly* and on policy.

---

## Common Mistakes

1. **Transparent proxies that forward everything.** That's not attenuation; you handed back the full object behind a thin shim.
2. **Handing out raw capabilities, then wanting to revoke.** Too late — you can't reach their reference. Always interpose a caretaker if revocation is plausible.
3. **Leaving one ambient import in an otherwise-injected module.** Reintroduces full authority and silently voids every guarantee.
4. **Returning inner objects from facets.** Authority escapes through return values; wrap them.
5. **Treating revocation as information control.** It governs future *access*, not data the holder already copied.
6. **A powerbox that grants broadly "for convenience."** Recreates ambient authority; grants must be narrow and policy-gated.
7. **Forgetting that tokens are capabilities.** Long-lived, unscoped bearer tokens are raw, unrevocable, over-broad capabilities — the worst kind.
8. **Confusing dependency injection of *anything* with capability injection.** Injecting a config value isn't capability discipline; injecting *authority* (and refusing to import it) is.

---

## Tricky Points

- **No-ambient-authority is a property of the *substrate*, not your code style.** You can write injection-style code all day, but if the language still offers a global `open`, a malicious or buggy module bypasses your design. True ocap needs the runtime to *withhold* ambient power (frozen realms, WASI, a capability kernel). Without that, you have *good hygiene*, not *enforced confinement*.
- **Revocation is forwarding, not deletion — always.** The holder's reference is unreachable to you forever. The only lever you have is the thing it points at. Internalize this and revocation design becomes obvious.
- **Attenuation is monotone; amplification needs a key.** You can always make a capability weaker for free. Making one stronger requires holding *another* capability (a sealer, an unsealer, a powerbox) — there is no free lunch, which is exactly why authority can't silently grow.
- **The delegation tree and the revocation tree are the same tree.** Because everyone forwards through the caretaker you planted, the structure you use to *share* authority is the structure you use to *reclaim* it. ACLs separate these, which is why ACL revocation is hard.
- **Confinement bounds authority, not information.** A confined component can't *gain new authority*, but if you handed it secret data it can still remember and reveal that data. Don't conflate "can't reach new resources" with "can't leak what it already saw."

---

## Apply it

1. Find a real component where **Capability-Based Security** affects an interface or dependency.
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

- Which boundary is most affected by Capability-Based Security?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
