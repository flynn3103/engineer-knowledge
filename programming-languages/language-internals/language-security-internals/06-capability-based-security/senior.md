# Capability-Based Security — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Capability-Based Security** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Capabilities in the Kernel: seL4 as the Reference Design

In seL4 there is no ambient anything. Every action — sending a message, mapping a page, starting a thread — is the **invocation of a capability** the process holds in its CSpace. There is no `open("/etc/passwd")`; there is no global file namespace at all. A driver can touch a device register only if it holds the capability to that frame of physical memory. The kernel's entire job is to be the unforgeable, mediated translation from "slot index in this process's CSpace" to "kernel object + rights."

Three properties make this powerful:

- **No ambient authority, enforced by hardware + kernel.** Userspace cannot fabricate a capability; it can only invoke, copy (with `CNode_Copy`), mint a weaker child (`CNode_Mint`, adding a badge or reducing rights), or delete one.
- **Derivation tree + `Revoke`.** Capabilities form a tree (parent → minted children). `seL4_CNode_Revoke` on a capability deletes the entire subtree of descendants. This is membrane-style revocation, in the kernel, in bounded time.
- **Formal verification.** seL4's C implementation is proven to refine an abstract spec, and the spec is proven to enforce **integrity** and **authority confinement** — i.e., the math says a subject cannot gain authority it wasn't given. This is only tractable *because* the model is capabilities: the security policy is "the capabilities you hold," which is small enough to reason about formally. An ACL system's ambient authority is far harder to prove anything about.

KeyKOS and EROS/CapROS are the lineage seL4 descends from: persistent, capability-based, with the same "everything is a capability invocation" stance and the same confinement guarantees (EROS proved its confinement mechanism). Fuchsia/Zircon carries the idea into a shipping consumer OS: every kernel object is named by a **handle** with **rights** bits, handles are transferred over channels, and there is no ambient filesystem — a component's namespace is exactly the handles it was given at launch by its parent (a powerbox-style model at the OS level).

### 2. Capabilities in the Language: Removing Ambient Globals

A capability OS confines *processes*. An object-capability *language* confines *modules within a process* — finer grained, and the right tool for plugin systems and supply-chain defense.

The enabling trick is always the same: **deny the guest the ambient globals.** Ordinary languages hand every line of code `fs`, `net`, `process.env`, `Date.now()`, `Math.random()` — all ambient authority and all nondeterminism. An ocap language/runtime *withholds* them and forces endowment:

- **E** (Miller et al.) was designed from scratch with no ambient authority: capabilities are object references, distributed objects communicate by eventual-send, and the powerbox pattern originates here.
- **Joe-E** is a verified, ambient-authority-free subset of Java: it removes `static` mutable state, `java.io.File` (ambient), reflection, and `finalize`, leaving a language where the heap reference graph *is* the authority graph.
- **SES / Compartments (JavaScript).** SES (now shipping as Hardened JavaScript in Agoric/Endo, and the basis for the TC39 Compartments proposal) *freezes* the primordials (so guest code can't mutate `Array.prototype` to attack the host) and runs guest code in a `Compartment` whose globals contain only what you endow. A guest in a Compartment with no `fetch` simply cannot do network I/O. This is the practical, deployable form of language-level ocap today.
- **Pony** bakes capabilities into the *type system*: its reference capabilities (`iso`, `val`, `ref`, `box`, `trn`, `tag`) statically guarantee that shared data is either immutable or uniquely owned, giving data-race freedom *and* a foundation for object-capability security at compile time.
- **Newspeak** has no global namespace at all — even class names are not ambient; modules receive their dependencies through a *module manifest*, making it ocap by construction.

The common thread: the **absence of ambient globals is the security mechanism.** Everything else (endowment, membranes) is plumbing on top of that absence.

### 3. WASI: Capabilities as the Sandbox Contract

WebAssembly's core has no I/O at all — by design. **WASI (the WebAssembly System Interface)** gives a module I/O, but on a **capability basis**: there is no `open("/etc/passwd")`. A module receives **preopened** file descriptors from the host (e.g., the runtime is told `--dir /sandbox`), and the module's `path_open` can only resolve paths *relative to a directory capability it already holds*. No preopen, no filesystem. The same applies to sockets, clocks, and randomness — each is an explicitly granted capability, not ambient.

This is the cleanest mainstream example of the model: WASI didn't *add* a sandbox to an ambient system; it started from *zero authority* and made every grant explicit. A compromised or malicious WASM module that was handed only `/sandbox` cannot exfiltrate over the network, because it holds no socket capability — full stop. That is structural supply-chain defense, which is precisely why WASI is attractive for plugin runtimes and edge compute.

### 4. The Membrane: Transitive, Revocable Boundaries

A caretaker (middle level) revokes *one* object. But objects hand out other objects: an account returns a transaction, which returns a ledger entry. Revoking the account doesn't revoke the objects it already vended. The **membrane** fixes this. A membrane is a wrapper with one extra rule: **whenever a wrapped object passes a reference across the membrane (as an argument *in* or a return value *out*), that reference is automatically wrapped by the same membrane.** So the *entire object subgraph* reachable through the membrane is mediated by it, and flipping the membrane's single revocation switch severs *all* of it atomically. This is the in-language analog of seL4's `Revoke` over a derivation subtree, and it is the correct tool for sandboxing a stateful object graph you must later cut off whole.

### 5. Macaroons: Attenuable Bearer Capabilities for Distributed Systems

Across a network, capabilities are bearer tokens. A plain signed token is a *fixed* capability: you can't make it narrower without asking the issuer to mint a new one. **Macaroons** (Google, 2014) make tokens *attenuable offline*. A macaroon is an HMAC chain: the issuer signs an empty token with a secret; to add a **caveat** (a restriction like `expires < T` or `object = 42`), *anyone* re-HMACs the current signature using the caveat text as the key. Because HMAC is one-way, you can only ever *add* caveats — never remove them — so derived macaroons are **strictly weaker**. The verifier re-runs the chain with the root secret and checks every caveat.

This gives capability properties to tokens: **attenuation by any holder, offline, with no issuer round-trip**; **delegation** (hand the attenuated macaroon onward); and even **third-party caveats** ("valid only if you also present a discharge macaroon from the auth service proving the user is an admin"), which compose authority across services without a central session store. Macaroons are the distributed-systems realization of the same "attenuate-and-delegate" algebra you saw with facets — and a clean answer to "OAuth scopes are too coarse and can't be narrowed by the client."

### 6. Why Mainstream OSes Stayed ACL-Based

If capabilities are this good, why is your laptop ACL-based? History and friction:

- **The Unix model won** on simplicity and the `everything-is-a-path` global namespace, which is *ambient by design* and deeply baked into every program, library, and shell idiom.
- **Audit-by-identity** ("who did this?") maps naturally to ACLs and is what compliance regimes ask for; capabilities answer "what was held," which is harder to retrofit onto identity-centric tooling.
- **Retrofitting is invasive.** Going capability-secure means *every* program must receive its authority instead of reaching for it — an ecosystem-wide rewrite. Pure capability OSes (KeyKOS, EROS) never reached the application gravity Unix had.
- **The compromise** — and where the field is actually moving — is *capability islands inside ambient systems*: file descriptors (already capabilities), `pledge`/`unveil` on OpenBSD, `capsicum` on FreeBSD (Capsicum turns an ambient process into a capability one with `cap_enter`), Linux `seccomp` + `landlock`, WASI sandboxes, and SES compartments. You don't convert the OS; you convert the *trust-sensitive component*.

---

## Code Examples

### SES / Compartment: Endow Exactly What a Guest May Reach (JavaScript)

```js
import 'ses';
lockdown();   // freeze primordials: guest can't mutate Array.prototype etc.

// A guest module with NO ambient authority:
const compartment = new Compartment({
  // endowments — the guest's ENTIRE reachable world:
  log: (msg) => console.log('[guest]', msg),
  readConfig: () => structuredClone(CONFIG),   // attenuated, copy-out
  // deliberately ABSENT: fetch, fs, process, Date, Math.random
});

compartment.evaluate(`
  log('hi');                 // works: endowed
  readConfig();              // works: endowed (read-only copy)
  // fetch('https://evil');  // ReferenceError: fetch is not defined
  // process.env.SECRET;     // ReferenceError: process is not defined
`);
// The guest cannot phone home or read the environment: those names don't exist here.
```

### A Membrane (transitive revocation) — the shape

```js
function makeMembrane(target) {
  let enabled = true;
  const wrapped = new WeakMap();

  function wrap(obj) {
    if (Object(obj) !== obj) return obj;          // primitives pass through
    if (wrapped.has(obj)) return wrapped.get(obj);
    const proxy = new Proxy(obj, {
      get(t, p) {
        if (!enabled) throw new Error('revoked');
        return wrap(t[p]);                        // wrap returned objects too
      },
      apply(t, thisArg, args) {
        if (!enabled) throw new Error('revoked');
        return wrap(t(...args.map(wrap)));         // wrap args in, result out
      },
    });
    wrapped.set(obj, proxy);
    return proxy;
  }

  return { facet: wrap(target), revoke: () => { enabled = false; } };
}
// revoke() severs the WHOLE subgraph the guest reached through `facet`, at once.
```

### Macaroon: Attenuate Offline (Python, conceptual)

```python
import hmac, hashlib

def macaroon(root_key, identifier, caveats):
    sig = hmac.new(root_key, identifier.encode(), hashlib.sha256).digest()
    for c in caveats:
        sig = hmac.new(sig, c.encode(), hashlib.sha256).digest()  # chain
    return identifier, caveats, sig

# Issuer mints a broad macaroon:
id_, cav, sig = macaroon(ROOT, "user=alice", [])

# A CLIENT attenuates it OFFLINE — no issuer round-trip — by adding caveats:
cav2 = cav + ["object = 42", "time < 1719300000"]
sig2 = sig
for c in ["object = 42", "time < 1719300000"]:
    sig2 = hmac.new(sig2, c.encode(), hashlib.sha256).digest()
# (id_, cav2, sig2) is STRICTLY weaker. The client cannot REMOVE a caveat:
# HMAC is one-way, so it can't recover an earlier signature in the chain.

# Verifier re-derives from ROOT and checks every caveat holds.
```

### seL4-style Capability Invocation (C, conceptual)

```c
// No open("/path"). To send on an endpoint, you INVOKE a capability slot:
seL4_MessageInfo_t msg = seL4_MessageInfo_new(0, 0, 0, 1);
seL4_SetMR(0, request);
seL4_Call(EP_CAP_SLOT, msg);     // EP_CAP_SLOT indexes THIS process's CSpace

// Mint a WEAKER, badged child capability for a client to call us back:
seL4_CNode_Mint(dest_cnode, dest_slot, depth,
                src_cnode, ep_slot, depth,
                seL4_AllRights, client_badge);   // attenuated + identified

// Revoke the whole derivation subtree (membrane-in-the-kernel):
seL4_CNode_Revoke(root_cnode, ep_slot, depth);
```

### Capsicum: Turn an Ambient Process Capability-Secure (FreeBSD, C)

```c
int dir = open("/sandbox", O_DIRECTORY);   // acquire authority FIRST
cap_enter();                               // CROSS THE LINE: now in capability mode
// After cap_enter(): open("/etc/passwd") FAILS — no ambient namespace.
// You may only use fds you already hold (and *at fds derived from `dir`):
int f = openat(dir, "data.txt", O_RDONLY); // relative to the held directory cap
```

---

## Coding Patterns

### Pattern 1: Lockdown then compartmentalize (SES)

```js
lockdown();
const guest = new Compartment({ /* only the endowments this guest needs */ });
guest.evaluate(untrustedSource);
```

### Pattern 2: Membrane around a vended object graph

```js
const { facet, revoke } = makeMembrane(domainRoot);
plugin.attach(facet);          // plugin reaches the graph only via the membrane
onPluginRemoved(revoke);       // cut the whole subgraph atomically
```

### Pattern 3: Mint-weaker-then-delegate (kernel or macaroon)

```text
child = mint(parent, rights = reduce(parent.rights), badge = clientId)
give(child) to the less-trusted party        # never give the parent
revoke(parent.subtree) when the relationship ends
```

### Pattern 4: WASI preopen as the only authority

```text
wasmtime --dir=/sandbox::/  module.wasm     # module's ENTIRE fs = /sandbox
# no --dir => module has NO filesystem at all
```

### Pattern 5: Third-party caveat for cross-service authority (macaroons)

```text
macaroon.addThirdPartyCaveat(authServiceLocation, predicate="user is admin")
# holder must obtain a DISCHARGE macaroon from authService to use it
```

---

## Best Practices

- **Match the enforcement layer to the trust boundary.** Untrusted binary → WASI; untrusted in-process module → Compartment/membrane; untrusted service/driver → capability kernel. Don't enforce at the wrong granularity.
- **Freeze the primordials before running guests (SES).** A guest that can mutate shared intrinsics escapes the model regardless of endowments. `lockdown()` is non-negotiable.
- **Use a membrane, not a caretaker, when revoking a stateful graph.** If the holder will obtain objects *transitively*, only a membrane catches them.
- **Mint badged, reduced-rights children; never delegate the parent capability.** Keep the parent (and its `Revoke` power) on your side of the boundary.
- **Treat macaroon root keys like crowns.** Root-key compromise forges everything. Rotate, scope per-service, and prefer third-party caveats over one omnipotent root.
- **Keep nondeterminism out of confined guests deliberately.** Withholding `Date.now`/`Math.random` is a feature (determinism, no covert clock channels); supply *attenuated* deterministic versions where the guest legitimately needs them.
- **Build capability islands in ambient systems** (`cap_enter`, `pledge`/`unveil`, `landlock`) for the security-critical component rather than waiting to rewrite the whole OS.

---

## Edge Cases & Pitfalls

- **Primordial poisoning before lockdown.** If guest code (or a guest's dependency) runs before `lockdown()`, or the host shares a mutable intrinsic, the guest can patch `Object.prototype` and exfiltrate through the host's own objects. Order and isolation matter.
- **Membrane identity breakage.** Wrapping changes `===` and prototype identity; code that uses objects as map keys or does `instanceof` across the membrane misbehaves. Membranes must carefully shadow identity, and some patterns simply can't cross.
- **Covert and side channels survive confinement.** Capabilities bound *authority*, not *information flow*. A confined guest with a shared cache or a real clock can still leak bits through timing. seL4 proves authority confinement, not the absence of timing channels (those need separate, expensive mitigations).
- **Macaroon caveat verification is the soft spot.** The cryptography only guarantees caveats can't be *removed*; if the verifier forgets to *check* a caveat (e.g., never evaluates `time < T`), the attenuation is decorative. Most macaroon CVEs are missing or mis-ordered caveat checks.
- **WASI ambient leakage via the host.** WASI confines the *module*, but a host that wires a too-broad preopen (`--dir /`) or a permissive custom import re-creates ambient authority. The sandbox is only as tight as the host's grants.
- **Capsicum/pledge after the fact.** Authority acquired *before* `cap_enter()`/`pledge()` is retained. Mis-ordering — sandboxing before opening the fds you need, or opening too many before sandboxing — defeats the point.
- **Rights amplification via sealer pairs across a membrane.** If a sealer/unsealer pair straddles the boundary, it can move authority the membrane was meant to mediate. Audit sealer pairs as first-class authority.

---

## Common Mistakes

1. **Running guest JS without `lockdown()`** — shared mutable primordials make the Compartment porous.
2. **Caretaker where a membrane is needed** — the guest obtains objects transitively and your revocation misses them.
3. **Delegating the parent capability** instead of a minted, reduced child — you lose the revocation handle and over-grant.
4. **Forgetting to *check* macaroon caveats** — you verified the signature but not the restrictions; attenuation is now cosmetic.
5. **Over-broad WASI preopen** (`--dir /`) — the module is "sandboxed" but the sandbox is the whole disk.
6. **Sandboxing in the wrong order** (`cap_enter`/`pledge` before acquiring needed fds, or after acquiring too many).
7. **Assuming confinement stops information leaks** — it stops *authority* gain, not timing/cache side channels.
8. **One omnipotent macaroon root key** shared everywhere — its theft forges every token in the system.

---

## Tricky Points

- **Formal verification is *enabled by* the capability model, not bolted onto it.** seL4 could be proven because "your authority is the capabilities you hold" is a small, explicit, closed statement. You cannot write that statement crisply for an ambient-authority system — there's no bounded set to reason about. The model and the proof are the same intellectual move.
- **A membrane is the language-level dual of `seL4_CNode_Revoke`.** Both revoke a *subtree* of derived authority atomically: the kernel over a derivation tree, the membrane over the reachable object subgraph. Recognizing them as the same pattern at different layers is the senior insight.
- **Macaroons make "shrink-only" a law of physics (HMAC), which is why a *client* can be trusted to attenuate.** In OAuth you must trust the issuer to mint a narrower scope; with macaroons the math forbids widening, so delegation needs no central authority — a genuinely different trust topology.
- **"No ambient authority" and "no nondeterminism" come together in realms, and that's deliberate.** Withholding `Date.now`/`Math.random`/`fetch` from a guest removes both an authority *and* a covert channel (clocks leak, network leaks). Capability languages tend toward determinism not by accident but because the same globals carry both authority and observability.
- **Bearer capabilities (fds, macaroons, tokens) are powerful *because* they carry no identity, and dangerous for the same reason.** Theft is total: the thief *is* authorized. This is the price of "possession is the permission," and it's why such capabilities must be short-lived, narrowly scoped, and revocable.

---

## Apply it

1. State the system invariant that **Capability-Based Security** must protect.
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

- Which invariant must remain true when Capability-Based Security fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
