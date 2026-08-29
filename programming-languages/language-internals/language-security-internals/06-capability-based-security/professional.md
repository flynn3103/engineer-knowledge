# Capability-Based Security — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Capability-Based Security** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### Retrofitting Least-Authority Into a Real Codebase

The single most important professional move is mechanical and unglamorous: **stop importing authority; start receiving it.** A module that does `import fs from 'node:fs'` has reached into the ambient world and grabbed the entire filesystem. A module that takes a `storage` parameter in its constructor holds exactly the authority its caller chose to grant. The first is ambient authority; the second is a capability. The refactor from one to the other is the whole game at this tier.

The recipe, applied to a real service:

**Step 1 — Inventory the ambient reach.** Grep for the ambient authority sources: `fs`, `net`, `http`, `child_process`, `process.env`, `dns`, global database clients, global HTTP clients. Each import is a place a module can do something its callers never authorized. This list *is* your attack surface for the confused-deputy and supply-chain classes.

**Step 2 — Push authority to the edges (the powerbox).** Decide where broad authority is *allowed* to live: usually `main()`, a composition root, a DI container, or a small "platform" module. That place opens files, dials sockets, reads env. Everything else receives capabilities from it. This is the powerbox pattern at application scale — you are not eliminating ambient authority from the *process*, you are confining it to one auditable place.

**Step 3 — Inject narrowed capabilities.** Instead of handing a module `fs`, hand it `openFileInDir(configDir)` bound to one directory, or a `ConfigStore` object exposing only `read(key)`. The module's authority is now a strict subset of the filesystem. The narrowing is the security; the injection is just plumbing.

**Step 4 — Make the ambient path a lint error.** Once a module receives its authority, forbid it from reaching for ambient authority again. `eslint-plugin-no-restricted-imports` banning `node:fs`/`node:net` in the business-logic layer is a capability boundary you can enforce in CI. Without this, the next contributor re-introduces `import fs` and silently re-opens the door.

The friction is real and worth naming: injection makes call signatures longer, makes wiring explicit, and makes "just read this one file here" annoying. That annoyance is the *point* — it surfaces every place a module exercises authority, which was previously invisible. The discipline pays off the first time you can answer "could the markdown renderer have read `/etc/passwd`?" with "no, it was only given a string" instead of "let me audit the whole call graph."

### Object-Capability Discipline in Practice

Object-capability (ocap) discipline turns the dependency-injection refactor above into a *language-enforced* property. Three deployable forms matter in production today.

**SES / Hardened JavaScript.** SES (Secure ECMAScript, shipping as Hardened JS in Agoric/Endo and the basis for the TC39 Compartments proposal) does two things: `lockdown()` *freezes the primordials* — `Object.prototype`, `Array.prototype`, `Function`, etc. — so a guest cannot mutate shared intrinsics to attack the host, and `Compartment` evaluates guest code in a scope whose globals contain only the endowments you pass. A plugin run in a Compartment with no `fetch` and no `process` literally cannot do network I/O or read the environment, because those names do not exist in its scope. This is the strongest in-process confinement you can deploy without a separate runtime, and it is the basis of Agoric's smart-contract platform where mutually distrustful code runs in one process.

**The Node permission model.** For whole-process confinement without rearchitecting, Node's `--permission` flag (stable as of recent Node majors) turns ambient `fs`/`net`/`child_process`/native-addon access into an allowlist. `node --permission --allow-fs-read=/app/config app.js` means any `fs.readFile` outside `/app/config` throws `ERR_ACCESS_DENIED`. This is coarse — process-level, not module-level — but it is a one-flag capability island that defends against a compromised dependency reaching the filesystem or shelling out. Treat it as the outer perimeter; SES Compartments are the inner walls.

**Compartments for dependency confinement.** The high-leverage pattern is to load *individual dependencies* into Compartments. Your business logic runs with full authority; the risky transitive dependency (a markdown parser, a template engine, an image decoder) runs in a Compartment endowed with only what it legitimately needs — usually *nothing* but pure-computation globals. A supply-chain compromise of that dependency is then contained: the malicious code has no socket, no `fs`, no `process` to exfiltrate through.

### WASI Capability Filesystem for Plugin and Edge Sandboxing

When the untrusted code is a *binary* rather than a module in your language, WASI is the production answer. WebAssembly core has no I/O; WASI adds it on a strict capability basis. The host **preopens** directories and sockets and hands the module file descriptors for them; the module's `path_open` can only resolve paths *relative to a preopen it already holds*. Run a module with `--dir /sandbox` and its entire filesystem is `/sandbox`; run it with no `--dir` and it has no filesystem at all.

In production this is how edge and plugin platforms get structural isolation. A Shopify Function, a Fastly Compute or Cloudflare-style edge module, a Figma-style plugin, or a database UDF compiled to WASM receives only the preopens the host grants. The supply-chain consequence is sharp: a compromised or malicious module handed only `/sandbox` and no socket preopen *cannot exfiltrate over the network* — not because a policy says so, but because it holds no network capability. The sandbox is exactly as tight as the host's grants, which is the one thing you must get right: a host that wires `--dir /` re-creates ambient authority and throws the whole model away.

The operational discipline for a WASI plugin host: (1) grant the *minimum* preopens per plugin, scoped to a per-plugin directory; (2) deny socket capabilities by default and grant them only to plugins whose function genuinely requires network egress, ideally through a host-mediated, policy-checked proxy rather than a raw socket; (3) treat the host's import surface (the functions you expose to the module) as authority too — a permissive custom host import is just as much ambient authority as a broad preopen.

### Macaroons and Capability Tokens in Distributed Systems

Across a network, a capability is a bearer token. The professional question is how to make those tokens *attenuable* and *delegable* without an issuer round-trip, and macaroons are the cleanest answer. A macaroon is an HMAC chain: the issuer signs an identifier with a root secret; any holder can append a **caveat** (`expires < T`, `object = 42`, `method = GET`) by re-HMACing the current signature with the caveat text. Because HMAC is one-way, holders can only ever *add* caveats, never remove them — derived macaroons are strictly weaker. The verifier re-runs the chain from the root secret and *must check every caveat*.

This buys three properties ordinary signed tokens lack. **Offline attenuation:** a client holding a broad macaroon can mint a tightly-scoped, 30-second token for a downstream cache without contacting the issuer. **Delegation:** hand the attenuated macaroon onward; the recipient's authority is bounded by every caveat in the chain. **Third-party caveats:** "valid only if you also present a discharge macaroon from the auth service proving the user is an admin" — this composes authority across services *without a shared session store*, because the discharge proof travels with the request. This is exactly the gap OAuth scopes leave: scopes are coarse and can only be narrowed by the issuer, whereas a macaroon holder narrows client-side, cryptographically.

The standing production hazard is not the cryptography — it is verification. The HMAC chain guarantees caveats cannot be *removed*; it guarantees *nothing* about whether your verifier actually *evaluates* them. The recurring macaroon vulnerability is a verifier that checks the signature, accepts the token, and never evaluates `expires < T` or `object = 42` — at which point the attenuation is decorative and every short-lived token is effectively eternal. Treat the caveat-verification function as the security-critical core, test it adversarially, and fail closed on any caveat the verifier does not recognize.

### Revocation: The Caretaker and Membrane Patterns

Granting authority is easy; *taking it back* is where capability systems earn their keep, and it is where teams most often get the pattern wrong. The two tools are the caretaker and the membrane, and choosing between them is a senior-to-professional judgment call you make on every revocable grant.

A **caretaker** wraps *one* capability behind a revocable indirection. The holder gets the caretaker, not the real object; the real object stays on your side. Flip the caretaker's switch and the wrapped capability throws. This is correct when the thing you grant is a *single object with no vending* — a one-shot file handle, a config reader, a logger.

A **membrane** is the transitive caretaker, and it is what you actually need most of the time. The problem: objects vend other objects. A tenant given a `Database` caretaker calls `db.table('orders')`, which returns a `Table`, which returns `Row` objects. Revoking the `Database` caretaker severs `db` but *not* the `Table` and `Row` objects the tenant already obtained — those are live references with full authority, and your "revocation" did nothing to the data the tenant can still reach. The membrane fixes this by wrapping *every* object that crosses the boundary, in either direction, with the same revocation switch. Revoke the membrane and the *entire reachable subgraph* the tenant ever obtained dies atomically. This is the in-language dual of `seL4_CNode_Revoke` over a derivation subtree.

In production, reach for a membrane whenever you grant access to a *stateful object graph* that the holder will navigate transitively — a plugin's view of your domain model, a tenant's handle to a multi-table store, an extension's reference to the editor's document tree. The membrane's cost is real (proxy overhead on every crossing, and `===`/`instanceof` identity breaks across the boundary), so don't reach for it when a caretaker suffices; but a caretaker where a membrane is needed is a *silent* authority leak, which is the worst kind.

### Supply-Chain Defense Through Capability Confinement

The most compelling modern argument for capability security is supply-chain. A typical service has thousands of transitive dependencies, any one of which could be compromised (typosquat, hijacked maintainer account, malicious update). Under ambient authority, *every* one of those dependencies can `require('fs')`, open a socket, and exfiltrate your secrets — the moment any of them is malicious, the whole process's authority is theirs. This is not hypothetical; it is the mechanism behind a long line of npm/PyPI/crates supply-chain incidents.

Capabilities change the default. **A capability-secure module cannot reach the network unless someone hands it a socket.** Run a dependency in an SES Compartment endowed with only pure computation, or as a WASI module with no socket preopen, and a malicious version of it has *no path* to exfiltrate — it holds no network capability, full stop. This is structural, not heuristic: it does not depend on detecting the malicious behavior, scanning the code, or trusting the maintainer. It depends only on the dependency genuinely not needing the authority you withheld, which for a markdown parser or a left-pad equivalent is trivially true.

The professional framing for a security review: classify each dependency by the authority it *legitimately* needs. Pure-computation dependencies (parsers, formatters, math) need *nothing* and should run confined — the cost is a Compartment or a WASM boundary, the payoff is that their compromise is contained. I/O dependencies (an HTTP client, a database driver) need authority and must be trusted or wrapped in a narrowing facet. This classification turns "we have 3,000 dependencies and trust them all implicitly" into "we have 40 dependencies that hold real authority, and the other 2,960 are confined."

### Migrating an ACL/RBAC System Toward Capabilities

Most systems you inherit are ACL- or RBAC-based: a request arrives with an identity, and a policy check asks "is this identity allowed to do this action on this object?" Migrating toward capabilities means moving from *identity-plus-policy-check* to *possession-of-an-unforgeable-reference*. This migration is where most of the friction — and most of the value — lives, so be honest about both.

**Why it is hard.** ACLs answer "who did this?" — exactly what compliance and audit ask for — and that question maps awkwardly onto "what was held." Your entire codebase assumes ambient identity: the current user is in a thread-local, a request context, a session. Every authorization decision reaches for that ambient identity, which is the confused-deputy vulnerability waiting to happen. Ripping out ambient identity is as invasive as ripping out ambient `fs`, and your auditors will ask where the identity went.

**Where to start (and stop).** Do *not* attempt to convert the whole system. Convert the *delegation-heavy, confused-deputy-prone* edges first: where service A acts on behalf of user U against service B and currently forwards U's full identity (so B can't tell whether A is doing what U asked or something broader). Replace that with a capability — a macaroon attenuated to exactly the action U authorized — and the confused deputy is structurally gone, because A can only present authority it was granted. Cross-service delegation, "share this document with a link," scoped API tokens, and per-tenant data access are the natural first targets.

**The hybrid that actually ships.** The endpoint stays ACL/RBAC for coarse, identity-centric, auditable decisions ("is this user a member of this org?"). Capabilities handle the fine-grained, delegable, attenuable decisions inside that boundary ("this specific link grants read on these three documents until Friday"). You keep identity for audit and authentication; you add capabilities for authorization-by-possession where delegation and least-authority matter. The migration is additive and reversible, which is the only kind of authorization migration a sane organization will approve.

### Production Capability Systems: seL4 and Fuchsia Handles

Two systems prove capabilities are not just a research toy but ship in products under adversarial load.

**seL4** is a formally verified microkernel where there is no ambient authority at all: every action is the invocation of a capability held in the process's capability space (CSpace), capabilities are minted weaker and badged, and `seL4_CNode_Revoke` severs a derivation subtree. Its C implementation is *proven* to enforce authority confinement and integrity. The professional significance is twofold: it ships in high-assurance products (secure phones, defense, automotive, avionics) where you need a *proof* rather than a test suite, and it demonstrates that the proof is *enabled by* the capability model — "your authority is the capabilities you hold" is a small enough statement to verify formally, which you simply cannot say about an ambient-authority system.

**Fuchsia / Zircon** carries the idea into a shipping consumer OS. Every kernel object is named by a **handle** carrying rights bits; handles are the only way to act on kernel objects, they are transferred over channels, and there is no ambient filesystem — a component's namespace is exactly the set of handles its parent granted at launch. This is the powerbox pattern at OS scale: a component holds the handles for its job and no more, so a compromised driver holds only the MMIO and IRQ handles for its device and cannot touch the rest of the system. Fuchsia is the existence proof that capability-by-handle scales to a full, maintainable, consumer operating system — the thing KeyKOS and EROS proved was *possible* but never reached application gravity for.

---

## Code Examples

### Refactor: From Ambient `fs` to an Injected Directory Capability (Node/TS)

```ts
// BEFORE — ambient authority: this module can read the entire filesystem.
// A compromise of this file, or of anything it imports, reaches all of disk.
import { readFile } from 'node:fs/promises';

export async function loadTemplate(name: string): Promise<string> {
  return readFile(`/app/templates/${name}.html`, 'utf8'); // unbounded reach + path traversal risk
}

// AFTER — injected capability: the module receives a directory capability
// bound to exactly one directory and can touch nothing else.
export interface DirCap {
  read(name: string): Promise<string>; // resolves only within the bound directory
}

export async function loadTemplate(dir: DirCap, name: string): Promise<string> {
  return dir.read(`${name}.html`); // authority is exactly what `dir` was given
}

// The POWERBOX (composition root / main) is the only place that opens the dir:
import { openDirCap } from './platform/fs-cap.js'; // narrowing factory, traversal-checked
const templates = openDirCap('/app/templates');
await loadTemplate(templates, 'invoice');
// loadTemplate now provably cannot read /etc/passwd: it was never handed it.
```

### Confine a Risky Dependency in an SES Compartment (JavaScript)

```js
import 'ses';
lockdown(); // freeze primordials so the guest can't poison Array.prototype etc.

// A transitive dependency we don't fully trust (e.g., a markdown renderer).
// It needs NOTHING but pure computation, so we endow it with nothing dangerous.
const sandbox = new Compartment({
  // endowments = the dependency's ENTIRE reachable world:
  // (deliberately ABSENT: fetch, fs, process, require, Buffer with network)
});

const render = sandbox.evaluate(untrustedRendererSource); // returns a pure (md) => html
const html = render(userMarkdown);
// Even if `untrustedRendererSource` is malicious, it holds no socket and no fs:
// it cannot phone home. Supply-chain compromise is structurally contained.
```

### Process Perimeter with the Node Permission Model (shell)

```bash
# Outer capability island: the whole process may read only /app/config,
# write only /app/cache, and may NOT spawn children or load native addons.
node --permission \
     --allow-fs-read=/app/config \
     --allow-fs-write=/app/cache \
     server.js
# Any fs access outside those paths -> ERR_ACCESS_DENIED at runtime.
# child_process and native addons are denied by default under --permission.
```

### WASI Plugin Host: Preopen Is the Only Authority (shell + host policy)

```bash
# Plugin gets EXACTLY /plugins/acme as its filesystem and NO network.
wasmtime run --dir=/plugins/acme::/ plugin.wasm
# No --dir => the module has no filesystem at all.
# No socket capability granted => the module cannot open a network connection,
# so a malicious plugin cannot exfiltrate, regardless of its code.
```

### Macaroon: Offline Attenuation + the Caveat-Check That Must Not Be Skipped (Python)

```python
import hmac, hashlib, time

def mint(root_key: bytes, identifier: str, caveats: list[str]):
    sig = hmac.new(root_key, identifier.encode(), hashlib.sha256).digest()
    for c in caveats:
        sig = hmac.new(sig, c.encode(), hashlib.sha256).digest()  # chain
    return identifier, list(caveats), sig

# Issuer mints a broad macaroon for a user.
ident, cav, sig = mint(ROOT, "user=alice", [])

# CLIENT attenuates OFFLINE — no issuer round-trip — before delegating.
new_caveats = ["object = 42", f"time < {int(time.time()) + 30}"]
cav2, sig2 = cav + new_caveats, sig
for c in new_caveats:
    sig2 = hmac.new(sig2, c.encode(), hashlib.sha256).digest()
# (ident, cav2, sig2) is STRICTLY weaker. HMAC one-wayness forbids removing a caveat.

def verify(root_key, ident, caveats, sig, request_object) -> bool:
    s = hmac.new(root_key, ident.encode(), hashlib.sha256).digest()
    for c in caveats:
        s = hmac.new(s, c.encode(), hashlib.sha256).digest()
    if not hmac.compare_digest(s, sig):
        return False  # signature (chain integrity) check
    for c in caveats:                 # <-- THE STEP THAT IS FATALLY EASY TO OMIT
        if not check_caveat(c, request_object):
            return False              # fail CLOSED on any caveat that does not hold
    return True
# Skipping the caveat loop is the recurring macaroon CVE: the signature verifies,
# attenuation becomes decorative, and "30-second" tokens live forever.
```

### Transitive Revocation: A Membrane Over a Vended Object Graph (JavaScript)

```js
function makeMembrane(target) {
  let live = true;
  const wrapped = new WeakMap();
  const wrap = (obj) => {
    if (Object(obj) !== obj) return obj;             // primitives pass through
    if (wrapped.has(obj)) return wrapped.get(obj);
    const proxy = new Proxy(obj, {
      get(t, p) { if (!live) throw new Error('revoked'); return wrap(t[p]); },
      apply(t, self, args) {
        if (!live) throw new Error('revoked');
        return wrap(t(...args.map(wrap)));           // wrap args IN and result OUT
      },
    });
    wrapped.set(obj, proxy);
    return proxy;
  };
  return { facet: wrap(target), revoke: () => { live = false; } };
}

// A tenant navigates the graph transitively: db -> table -> row.
const { facet: dbForTenant, revoke } = makeMembrane(database);
tenant.attach(dbForTenant);
// On tenant churn, ONE call severs db, every table, and every row it ever obtained:
revoke();
// A caretaker on `database` alone would have left vended tables/rows live — a leak.
```

---

## Coding Patterns

### Pattern 1: Powerbox at the composition root

```ts
// One place holds broad authority; everything else receives narrowed capabilities.
const platform = { fs: openDirCap('/app/data'), net: dialScoped('payments.internal:443') };
const service = makeService(platform.fs, platform.net); // injected, not imported
```

### Pattern 2: Confine-the-dependency

```js
lockdown();
const dep = new Compartment({ /* only what THIS dependency legitimately needs */ });
const safe = dep.evaluate(untrustedDependencySource);
```

### Pattern 3: Attenuate-then-delegate (macaroon)

```text
narrow = addCaveat(broadToken, "object=42"); narrow = addCaveat(narrow, "expires<+30s")
send(narrow) to the less-trusted downstream      # never send the broad token
```

### Pattern 4: Membrane for a vended graph

```js
const { facet, revoke } = makeMembrane(domainRoot);
tenant.attach(facet);          // tenant reaches the graph only through the membrane
onTenantChurn(revoke);         // sever the whole subgraph atomically
```

### Pattern 5: Confused-deputy fix on a delegation edge

```text
# BEFORE: service A forwards user U's full identity to B (B can't tell scope)
# AFTER:  service A presents a macaroon attenuated to exactly the action U authorized
authority = attenuate(userMacaroon, ["action=read", "object=" + requestedDoc])
callB(authority)   # A can only ever exercise what it was granted
```

---

## Best Practices

- **Inject authority; never import it in the business layer.** Make `import fs`/`net` a lint error outside the powerbox.
- **Confine the broad authority to one auditable powerbox** and review what it hands out, not the whole codebase.
- **Confine pure-computation dependencies** (parsers, formatters) in a Compartment or WASM boundary endowed with nothing — that's where supply-chain risk concentrates and where the cost is lowest.
- **`lockdown()` before running any guest.** A guest that can mutate shared primordials escapes regardless of endowments.
- **Grant the minimum WASI preopen and deny sockets by default.** Mediate egress through a host-checked proxy, not a raw socket capability.
- **Treat the macaroon caveat-verification function as security-critical.** Test it adversarially, fail closed on unrecognized caveats, and never accept a token whose caveats you did not evaluate.
- **Use a membrane, not a caretaker, when the holder obtains objects transitively.** A caretaker where a membrane is needed is a silent leak.
- **Migrate ACL→capability on delegation edges first, keep a hybrid.** Identity for audit/authentication, capabilities for fine-grained, delegable authorization.
- **Rotate and scope macaroon root keys per service;** prefer third-party caveats over one omnipotent root.

---

## Edge Cases & Pitfalls

- **Re-imported ambient authority.** A retrofit holds until the next contributor adds `import fs` to a confined module. Without a CI lint rule, the boundary silently erodes.
- **Powerbox bloat.** If "the one place with authority" grows to half the codebase, you have a powerbox in name only. Keep it small and audited.
- **Over-broad WASI preopen / permissive host import.** `--dir /` or a powerful custom host function re-creates ambient authority inside a "sandbox."
- **Membrane identity breakage.** `===`, `instanceof`, and using objects as map keys misbehave across the membrane; some patterns simply cannot cross.
- **Caretaker where a membrane was needed.** Revocation silently misses objects the holder obtained transitively.
- **Macaroon caveat not *checked*.** The signature verifies, the attenuation is cosmetic — the most common macaroon vulnerability.
- **Ambient identity survives the migration.** Converting object authority to capabilities while leaving a thread-local "current user" that handlers reach for keeps the confused-deputy hole open.
- **Confinement mistaken for information-flow control.** Capabilities bound *authority*, not *information*: a confined guest with a real clock or shared cache can still leak bits through timing.
- **Bearer-token theft is total.** A stolen macaroon *is* the authority; keep them short-lived, narrowly scoped, and revocable.

---

## Common Mistakes

1. **Importing ambient `fs`/`net` in business logic** instead of receiving an injected capability — the original sin every retrofit targets.
2. **Letting the powerbox sprawl** until "the one place with authority" is everywhere.
3. **Running guest/plugin JS without `lockdown()`** — shared mutable primordials make the Compartment porous.
4. **Over-broad WASI preopen** (`--dir /`) or a permissive custom host import re-creating ambient authority.
5. **Verifying a macaroon's signature but never *checking* its caveats** — attenuation becomes decorative.
6. **Using a caretaker where a membrane is required** — revocation silently misses transitively-vended objects.
7. **Converting object authority to capabilities while leaving ambient identity** (thread-local current user) — the confused deputy survives.
8. **Treating confinement as information-flow control** — timing and cache side channels survive.
9. **One omnipotent macaroon root key** everywhere — its theft forges every token.
10. **Trying to convert the whole ACL system at once** instead of starting with delegation edges and staying hybrid.

---

## Tricky Points

- **The retrofit's hardest part is social, not technical.** The mechanical change (import → inject) is easy; convincing a team to accept the friction *before* the payoff, and keeping ambient authority from creeping back via the next PR, is the real work. A CI lint rule turns a discipline into a guarantee.
- **"Confinement is containment, not detection" is the whole supply-chain argument.** You don't have to recognize the malicious dependency; you only have to not hand it a socket. That's why it defends against *future, unknown* compromises that no scanner can catch.
- **Macaroon security is entirely in the verifier.** The cryptography guarantees shrink-only; it guarantees nothing about whether you *evaluate* the caveats. Every macaroon incident is a missing or mis-ordered caveat check, never a broken HMAC.
- **A membrane is the language-level dual of `seL4_CNode_Revoke`.** Both atomically revoke a *subtree* of derived authority — the kernel over a derivation tree, the membrane over a reachable object subgraph. Recognizing them as one pattern at two layers is the professional insight.
- **Bundling designation with authority is what kills the confused deputy.** The bug exists because ambient authority *separates* "what to act on" (a path the user names) from "permission to act" (the deputy's ambient power). A capability fuses them: holding the reference *is* the permission, so a caller can only designate what it was authorized to touch.
- **You will ship a hybrid, and that is correct.** Identity-based ACLs for audit and authentication, capabilities for fine-grained delegable authorization. Purists who demand all-capabilities never ship; the value is in converting the confused-deputy-prone edges.

---

## Apply it

1. Define the user or business outcome that **Capability-Based Security** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Capability-Based Security?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
