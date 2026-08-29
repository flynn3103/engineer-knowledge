# Control-Flow Integrity — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Control-Flow Integrity** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Precision Ceiling: CFI Allows an Equivalence Class, Not a Point

Every CFI scheme answers "may this indirect branch go *here*?" by checking membership in a **target set** — an **equivalence class** of "indistinguishable" targets. Fine-grained CFI shrinks the class (type-based, type-hash), but it can almost never shrink it to the single, contextually-correct target, because the information to do so (which target is correct *at this call, in this state*) isn't statically available. Consequences:

- If two functions share a type, CFI treats them as interchangeable. An attacker who can only redirect *within* the class still has options.
- Indirect calls with permissive types (`void(void)`, `void*(void*)`, opaque callback ABIs) have large classes and weak CFI value.
- Backward-edge integrity (shadow stack/PAC-ret) is the exception — there's exactly *one* correct return target, so it can be precise. This is *why backward-edge integrity is stronger than forward-edge CFI*: the forward edge has a precision ceiling the backward edge doesn't.

So the honest statement is: CFI bounds the attacker to *legal-looking* control flow. The remaining attacks are the ones that *stay legal-looking*.

### 2. Data-Only Attacks: CFI's Structural Blind Spot

CFI protects **control data** (return addresses, code pointers). It is, by construction, blind to **non-control data**. If a bug lets an attacker flip an `is_admin` flag, enlarge a `length` field, swap a `file_path`, or corrupt a *data* pointer the program later trusts, the program's control flow stays *entirely legitimate* — every branch goes where the source says — yet the behavior is attacker-chosen.

Classic shapes (described, not weaponized):

- Overwrite a permission/role boolean so a later legitimate `if (authorized)` takes the privileged path.
- Corrupt a size/bounds field so a subsequent legitimate copy reads/writes more than intended.
- Redirect a *data* pointer (not a function pointer) — e.g., a buffer pointer or a configuration pointer — so legitimate code operates on attacker-chosen memory.
- **Data-Oriented Programming (DOP):** chain such non-control corruptions to achieve rich, even Turing-complete, computation — all without a single hijacked branch.

The takeaway: **CFI raises the cost of control-flow hijacking, which *pushes* sophisticated attackers toward data-only techniques.** A CFI-hardened target is not a safe target; it's a target where the cheap attack moved.

### 3. COOP: Defeating Even Fine-Grained vtable CFI

**Counterfeit Object-Oriented Programming (COOP)** is the canonical demonstration that *forward-edge CFI can be satisfied and still bypassed*. The idea: instead of forging a *fake* vtable (which `cfi-vcall` would reject), the attacker assembles **counterfeit objects** whose vtable pointers point at **real, valid vtables**, then drives a sequence of **legitimate virtual calls** ("vfgadgets" — whole virtual functions) to perform computation. Because every call dispatches through a *genuine* vtable to a *type-valid* method, vtable-integrity CFI sees nothing wrong.

COOP matters professionally because it proves a deep point: **enforcing that each individual indirect call is *type-valid* does not prevent a malicious *composition* of valid calls.** The "grammar" is enforced; the "sentence" is still hostile. Defenses respond with even tighter context (e.g., per-call-site argument/state checks), but the precision ceiling means there's always residual composition freedom. COOP is the forward-edge analog of "ROP reuses legitimate code" — only now it reuses legitimate *typed* calls.

### 4. The Economics: Performance, Adoption, and the Weakest Link

CFI's deployment is governed less by theory than by cost:

- **Performance.** Inserted checks cost cycles (forward-edge type checks), hardware features cost little (CET shadow stack, PAC) but not nothing. Hot indirect-call paths (interpreter loops, dispatch tables) feel it most. Real numbers are usually low single-digit percent, but "low" is relative to a product's margins.
- **Toolchain/ABI friction.** LLVM CFI wants LTO and whole-program visibility; PAC/CET need property-note marking; mixing instrumented and un-instrumented objects creates "legacy" gaps. The guarantee is only as strong as the *least-protected* linked component.
- **Hardware gating.** CET/PAC/BTI/MTE need capable silicon and OS support; you ship to a fleet with a long tail of old CPUs, so you maintain both paths.
- **Compatibility breakage.** JITs, `dlsym`, `setjmp`/`longjmp`, custom unwinders, signal handling, and stack switching all collide with CFI and must be handled or exempted — and every exemption is a potential hole.

The professional's job is to spend the CFI budget where the attack surface is (untrusted parsers, network input, IPC boundaries) and to *measure* both the overhead and the residual.

### 5. CFI in the Portfolio: ASLR, MTE, Sandboxing, Memory Safety

CFI is one layer. The complementary layers attack *different* parts of the exploit chain:

- **ASLR** hides addresses — but a single **info leak** undoes it, and CFI doesn't prevent leaks. ASLR + CFI is standard, but they share the info-leak weakness.
- **ARM MTE (Memory Tagging)** attacks the *root cause* CFI only mitigates downstream: it catches out-of-bounds and use-after-free *at the moment of the bad access*, before the attacker ever reaches a corrupted pointer. MTE and CFI are highly complementary — MTE kills many bugs that would otherwise feed a CFI-bypass.
- **Sandboxing / privilege separation** assumes the worst (code execution happens) and *contains* it, so a bypass yields little. Browsers' renderer sandboxes are the model.
- **Memory-safe languages** (Rust, Go, managed runtimes) *delete the bug class*. The strategic endgame for new code is to remove the conditions CFI exists to mitigate. CFI is the safety net for the C/C++ you can't rewrite *yet*.

The architecture mindset: CFI makes the *control-flow* step expensive; MTE makes the *corruption* step fail early; sandboxing makes *success* cheap to contain; memory safety makes the *bug* not exist. You want as many of these as the platform and budget allow.

### 6. Communicating the Guarantee Without Overclaiming

A recurring professional failure is the security claim that outruns the mechanism. Precise framing:

- ✅ "Forward-edge CFI restricts indirect calls to type-compatible targets, and shadow stacks/PAC make return-address forgery infeasible, so classic ROP/vtable-hijack chains are blocked."
- ❌ "CFI protects us from memory-corruption exploits."
- ✅ "Residual exposure: data-only attacks, COOP-style composition within type classes, and any path our exemptions (JIT, FFI) open. We mitigate those with MTE/ASLR/sandboxing and are migrating the highest-risk parsers to a memory-safe language."

That paragraph is the deliverable. It states what's covered, what's not, and the plan for the gap.

---

## Code Examples

> Architectural/illustrative. The "attack shapes" are conceptual descriptions of *what CFI misses*, not exploits.

### 1. The shape CFI cannot see (data-only)

```c
struct session {
    bool   is_admin;      // <-- non-control data
    char   name[32];      // <-- overflow source
    void (*on_close)(void);
};

void handle(struct session *s, const char *input) {
    // Suppose a bug overflows s->name into s->is_admin (data, not a pointer).
    // CFI sees NOTHING wrong: no indirect branch was redirected.
    memcpy(s->name, input, attacker_len);   // BUG

    if (s->is_admin) {                       // legitimate branch, now true
        do_privileged_thing();               // reached via 100% valid control flow
    }
    s->on_close();   // CFI *does* guard this call — but the damage is already done
}
```

The lesson: lay out security-critical *data* (flags, roles, sizes) so it isn't corruptible from adjacent buffers, validate it independently, and don't rely on CFI to notice — it can't.

### 2. Why type-based forward CFI still leaves a class

```c
typedef void (*op_t)(void);   // permissive type

void a(void); void b(void); void c(void); /* ... 200 more void(void) ... */

void run(op_t op) {
    // cfi-icall confirms `op` is *some* void(void) function.
    // It cannot confirm it's THE one intended here -> 200-member class.
    op();
}
```

Mitigation pattern: give callbacks *distinct, specific* types so each call site's class is tiny.

### 3. Measuring the overhead you're buying

```bash
# Build two variants and benchmark the hot path honestly.
$ clang -O2 -flto              app.c -o app.base
$ clang -O2 -flto -fsanitize=cfi -fcf-protection=full app.c -o app.cfi

$ hyperfine './app.base bench' './app.cfi bench'   # report the delta
```

### 4. Stating the guarantee in a threat model (the real deliverable)

```text
Mitigation:  Forward-edge CFI (LLVM cfi-icall/cfi-vcall, LTO) +
             backward-edge integrity (CET shadow stack / PAC-ret) +
             IBT/BTI landing pads + Full RELRO + PIE/ASLR.

Blocks:      Classic stack-smash-to-shellcode, ROP `ret`-chaining,
             fake-vtable hijack, GOT overwrite.

Residual:    Data-only / DOP attacks (no branch redirected),
             COOP (composition of type-valid vcalls),
             info-leak-assisted attacks, exemptions (JIT, dlsym, longjmp).

Mitigated by: ARM MTE where available, renderer/parser sandboxing,
             least privilege, and migration of the JSON/media parsers
             to Rust (tracked: SEC-1421).
```

---

## Trade-offs

| Decision | In favor | Against |
|----------|----------|---------|
| **Enable fine-grained forward CFI** | Blocks fake-vtable / type-mismatched hijacks. | LTO/ABI friction; class-precision ceiling; COOP residual. |
| **Enable hardware backward edge (CET/PAC)** | Precise, cheap, kills ROP `ret`-chains. | Hardware gating; JIT/unwinding handling. |
| **Add MTE** | Catches the *bug* before the pointer is hijacked. | ARM-only, hardware-gated, tag-exhaustion/overhead nuances. |
| **Sandbox the component** | Contains even full code execution. | Architecture cost; IPC complexity. |
| **Rewrite in a memory-safe language** | Deletes the bug class entirely. | Cost/time; FFI boundary still unsafe; not always feasible. |
| **Do nothing more, "CFI is on"** | Cheap. | Overclaims; ignores data-only/COOP/info-leak residual. |

---

## Coding Patterns

**Pattern: Protect security-critical *data* independently of CFI.** Separate role/permission/size fields from attacker-reachable buffers (separate allocations, guard pages, redundant checks, canary-style validation of the field). CFI won't notice their corruption.

**Pattern: Tighten types to shrink forward-edge classes.** Specific function-pointer signatures and sealed class hierarchies reduce the equivalence class and the COOP/vfgadget surface.

**Pattern: Budget mitigations by attack surface.** Maximum hardening on untrusted-input boundaries (parsers, IPC, network); relax in trusted internals to spend the perf/complexity budget where it matters.

**Pattern: Make exemptions explicit and audited.** Every `no_sanitize`, JIT region, and FFI boundary is a documented hole with an owner and a compensating control.

**Pattern: Pair detection with containment.** MTE/ASAN-in-prod-where-feasible for early detection; sandboxing for late containment; CFI in the middle.

---

## Best Practices

1. **Enable both edges with fine granularity** *and* state the residual — never present CFI as a memory-corruption cure.
2. **Add MTE where available**; it attacks the bug class upstream of CFI and composes powerfully with it.
3. **Sandbox the components that parse untrusted input**, so a CFI bypass yields contained capability.
4. **Drive memory-safety migration for the highest-risk C/C++** (parsers, decoders); treat CFI as the net for what remains.
5. **Audit the full link closure and every CFI exemption.** The guarantee equals the weakest linked object.
6. **Measure overhead on real hot paths** and place protection by attack surface, not uniformly.
7. **Write the threat model as bounded statements** with explicit residual and a remediation plan.

---

## Edge Cases & Pitfalls

- **"CFI is on" in a binary linking an un-instrumented library** — the un-instrumented region is a CFI-free zone; an attacker pivots there.
- **Permissive callback types** (`void(void)` everywhere) collapse forward-edge precision; the class is huge.
- **Info leaks neutralize ASLR *and* enable many CFI-adjacent attacks** — yet CFI doesn't stop leaks. Treat read primitives as first-class threats.
- **COOP satisfies vtable CFI by construction** — counting on `cfi-vcall` to stop "vtable-based" attacks misreads the threat.
- **Data-only attacks leave perfect control flow** — no mitigation on this page (including CET/PAC) will fire.
- **JIT/`dlsym`/`longjmp` exemptions** are real holes; an attacker who can influence JIT'd code or FFI targets routes around CFI.
- **Performance-driven uniform CFI** wastes budget on cold paths while under-protecting hot, untrusted ones.

---

## Common Mistakes

- Claiming CFI defeats memory-corruption exploits (it raises cost; it doesn't delete the bug class).
- Forgetting data-only/DOP and COOP exist, then being blindsided by an exploit that "shouldn't have worked."
- Leaving callback types permissive and assuming forward-edge CFI is "fine-grained."
- Trusting ASLR without acknowledging the info-leak dependency.
- Treating MTE, sandboxing, and memory safety as alternatives to CFI rather than complements.
- Letting exemptions (JIT/FFI) accumulate unaudited.

---

## Tricky Points

- **Backward-edge CFI can be precise; forward-edge cannot** — single correct return vs an equivalence class of type-valid calls. This asymmetry explains where exploits concentrate.
- **COOP is to the forward edge what ROP is to the backward edge** — both reuse *legitimate* code; CFI raised the bar but the composition freedom remains.
- **CFI changes attacker behavior more than it changes outcomes for the most capable adversaries** — it prices out the cheap attacks, redirecting effort to data-only/COOP/leaks.
- **The strongest "CFI strategy" often isn't more CFI** — it's MTE (kill the bug earlier), sandboxing (contain success), or memory safety (delete the bug).
- **Every exemption is a deliberate hole** — the security of the whole equals the security of the least-protected reachable component.

---

## Apply it

1. Define the user or business outcome that **Control-Flow Integrity** should improve.
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

- Which measurable outcome justifies investing in Control-Flow Integrity?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
