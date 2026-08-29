# Sandboxing & Isolation — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Sandboxing & Isolation** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Spectrum Is a Cost Function, Not a Ladder to Climb

Lay out the options by **isolation strength vs cost**:

```text
in-process    OS-level       gVisor          microVM /        full VM /
isolate/Wasm  container      (userspace      Kata             separate host
              (ns+cgroup+    kernel)          (Firecracker)
              seccomp)
   │             │              │                │                  │
weakest       weak-ish       medium-strong    strong            strongest
fastest,      fast,          some syscall     ~125ms boot,      heavy
densest       shared kernel  overhead,        own kernel,       (full OS,
              (huge surface) smaller host     hypervisor        slow boot,
                             kernel surface   boundary          high RAM)
```

You don't always want the strongest — you want the **cheapest option whose residual risk you can accept for this threat**. A trusted internal batch job: a container is fine. Arbitrary code from anonymous users on shared hardware: you want a hardware boundary (microVM) or a drastically reduced host-kernel surface (gVisor). The senior skill is mapping *threat* → *acceptable residual risk* → *the cheapest rung that meets it*, and being explicit about what you're trading.

### 2. The Shared-Kernel Problem ("Containers Are Not a Security Boundary")

A container shares the host's **single kernel**. The guest reaches that kernel through the syscall interface — hundreds of syscalls, each a path into millions of lines of privileged, memory-unsafe C. **Any** exploitable kernel bug reachable from the container is a full host compromise, and from the host, every co-tenant. seccomp shrinks *which* syscalls are reachable, which genuinely helps, but a kernel that large will always have undiscovered bugs in the reachable set. That's the precise, defensible meaning of "containers are not a security boundary": **the boundary is the kernel, and the kernel is too big and too unsafe to be a strong wall against a determined, hostile guest.** Containers are an excellent *deployment* and *resource* boundary; they are a *weak security* boundary for hostile multi-tenancy without help.

### 3. Two Answers: Shrink the Surface (gVisor) or Move the Boundary (microVM)

The industry's two main responses attack the shared-kernel problem from opposite directions:

- **gVisor — shrink the host-kernel surface.** gVisor runs a **userspace kernel** (Sentry) that *implements* the syscall interface itself, in a memory-safe language (Go), and itself runs heavily seccomp-confined. When the guest makes a syscall, Sentry handles it; only a small, tightly filtered set of operations ever reach the real host kernel. The guest's reachable host-kernel surface shrinks from "hundreds of syscalls" to "a handful, behind a strict filter." Cost: real syscall-heavy workloads slow down, because syscalls now cross into Sentry instead of straight to the kernel.

- **Firecracker / Kata — move the boundary to hardware.** Each guest gets its **own real kernel** inside a **microVM**, isolated from the host by **hardware virtualization**. The boundary is no longer the host kernel's syscall surface but the **hypervisor + the emulated device model** — a much smaller, more auditable surface. Firecracker minimizes that surface further by emulating only a tiny set of devices (no BIOS, no PCI, minimal virtio). Cost: ~tens-to-hundreds of milliseconds to boot, more memory per guest, an extra OS to manage. Firecracker's design point — fast boot, minimal devices, one microVM per function — is exactly what makes per-tenant hardware isolation viable at serverless scale.

Both are "stronger than a plain container." They differ in *what* the residual TCB is (Sentry + a tiny host filter vs hypervisor + device emulation) and in *what they cost*.

### 4. Escape Classes (Conceptual, Defensive)

You can't enumerate every bug, but you *can* enumerate the **classes** of escape and design against each:

| Class | What it is | Defensive response |
|-------|-----------|--------------------|
| **Syscall-surface / kernel bug** | Guest exploits a bug in a host-kernel syscall handler reachable from the sandbox. | Shrink the surface: tight seccomp, gVisor (userspace kernel), or move to a microVM so the guest never calls the host kernel. |
| **Emulated-device / hypervisor bug** | (VM case) Guest exploits the virtual hardware emulation or the VMM. | Minimize the device model (Firecracker's tiny virtio set), keep the VMM small and in a memory-safe language, sandbox the VMM itself. |
| **Misconfiguration / leaky boundary** | A mounted host path, an unshared namespace, a too-broad capability, a passed-in handle that reaches more than intended. | Deny-by-default, audit every mount/handle/capability, fail closed, test the boundary. |
| **Logic / confused-deputy** | Guest tricks a privileged broker into doing something on its behalf (see below). | Capability-based design; the broker authorizes by token, never by ambient identity. |
| **Resource exhaustion / DoS** | Guest doesn't escape but degrades or denies service to host/co-tenants (noisy neighbor). | cgroups, quotas, rate limits, per-tenant accounting. |
| **Side channel** | Guest infers another tenant's data through shared hardware (cache, timing, speculation) without "breaking" any wall. | See below — the hardest class. |

The point of classifying is that **each class has a different defense**, and a sandbox strong against one class can be wide open to another. A microVM crushes the kernel-bug class but does nothing about Spectre-class side channels.

### 5. Side Channels: Escapes That Don't Break the Wall

The most unsettling escapes never cross the explicit boundary at all. **Side channels** leak information through a *shared physical resource*: two tenants on the same core share CPU caches, branch predictors, and execution units, and one can infer the other's secrets by measuring timing. **Spectre/Meltdown** showed that **speculative execution** can be coaxed into accessing memory across a security boundary and leaving a measurable microarchitectural trace, even when the architectural boundary is intact. Crucially, *stronger logical isolation (a VM, even a separate kernel) does not necessarily stop a side channel* if the two guests share the same physical core/cache. Defenses live below the OS sandbox: core/cache partitioning, not co-scheduling distrusting tenants on sibling hyperthreads (disabling SMT for sensitive workloads), microcode mitigations, and constant-time code in the secret-handling components. For the strongest guarantees, you stop sharing hardware: dedicated cores or dedicated hosts per trust domain. A senior recognizes side channels as a *distinct axis* the OS/VM sandbox does not, by itself, close.

### 6. The Confused Deputy and Ambient Authority — The Root Cause

Most non-kernel sandbox escapes are some flavor of the **confused-deputy problem**: a privileged component (the "deputy" — a broker process, a host function, a setuid helper) is tricked by a less-privileged caller (the guest) into using *its* authority to do something the guest couldn't do directly. The classic example is a compiler with permission to write to a billing file being asked by a user to "write output to" that file path — it does, abusing its own authority on the user's behalf.

The *root cause* is **ambient authority**: the deputy acts using *who it is* (its identity, its ambient permissions) rather than *what token the request carried*. Because authority is ambient, the deputy can't tell "authority I should use for *this* request" from "authority I happen to possess." The structural fix is **capability security**: requests carry **capabilities** — unforgeable tokens that simultaneously *name* the resource and *authorize* it. A capability can't be confused with ambient power because the only authority in play is the one the caller actually presented. WASI's preopened-directory handles, passed file descriptors, and object-capability languages are all instances of this fix. This is *why* the whole field keeps returning to capabilities: they structurally eliminate the confused-deputy class, which ambient-authority designs can only patch case by case.

### 7. Threat-Modeling the Boundary: Inside, Outside, and the Interface

Designing a sandbox is mostly **drawing the boundary correctly**:

- **What's inside** (untrusted): the guest code, the data it generates, anything it can write.
- **What's outside** (protected): host memory, secrets, other tenants, the network, the control plane.
- **The interface**: every syscall allowed, every host function imported, every mounted path, every passed handle, every shared file/region/clipboard. *This is the attack surface.* Threat modeling is the discipline of enumerating the interface and asking, for each element, "what could a maximally hostile guest do with this?"

Two things bite seniors specifically. First, **the interface is wider than the obvious API** — error messages, timing, log files, shared temp directories, and metadata all cross the boundary and can leak or be abused. Second, **outputs are inputs in disguise**: data flowing *out* of the sandbox (return values, files, rendered content) is attacker-controlled and must be validated before the host trusts it, or you've moved the vulnerability outside the box.

### 8. TOCTOU at the Boundary

A specific, recurring boundary bug is **Time-Of-Check-To-Time-Of-Use**. The host checks a property of something the guest can influence — a path, a symlink, a file's permissions, a length field — and then *acts* on it a moment later. In the gap, the guest changes it. Classic forms: the host validates that `path` points inside the sandbox directory, then opens `path`, but the guest swaps it for a symlink to `/etc/shadow` in between; or a host function reads a length from guest memory, validates it, then re-reads it (now larger). The defense is to **eliminate the gap**: operate on the object you already resolved (open the file descriptor first, then validate the *fd*, then use the *same fd*), copy guest-supplied values into host memory once and validate the copy, and never re-resolve names you already checked. TOCTOU is why "validate then use the handle, not the name" is a security rule, not just hygiene.

### 9. Defense in Depth as the Operating Assumption

Because every single wall has a class of escape it doesn't cover — kernel bugs (containers), VMM/device bugs (VMs), engine memory bugs (in-process), side channels (everything sharing hardware), confused-deputy logic (any broker) — the senior posture is **never rely on one layer**. Combine: a memory-safe language for the guest runtime + an in-process boundary + an OS sandbox or microVM + minimal exposed interface + side-channel hardening for the most sensitive data. The goal isn't a perfect wall (there is none); it's making the cheapest escape path expensive enough, and the blast radius small enough, that the *expected* loss is acceptable for the threat you actually face.

---

## Code Examples

These are conceptual sketches; the lessons are architectural.

### Picking a Rung by Threat (decision sketch)

```text
function choose_isolation(workload):
    if workload.code is fully trusted and inputs are controlled:
        return PROCESS_OR_CONTAINER        # cheap, blast radius low by trust

    if workload is untrusted but you control the tenants (known accounts):
        return CONTAINER + tight seccomp + dropped caps + cgroups
        # acceptable if you can also detect/respond; document residual kernel risk

    if workload is arbitrary code from anonymous / mutually-distrusting tenants:
        if latency budget tolerates ~100ms cold start and per-VM RAM:
            return MICROVM (Firecracker/Kata)   # hardware boundary, small VMM TCB
        else:
            return GVISOR                       # smaller host-kernel surface, in-between cost

    if the data is so sensitive that side channels matter (crypto keys, multi-tenant secrets):
        return DEDICATED_HARDWARE per trust domain   # stop sharing cores/caches
```

The decision is driven by *who the tenant is* and *how sensitive the data is*, not by what's fashionable.

### Confused Deputy: the Bug and the Capability Fix

```text
// VULNERABLE (ambient authority): the broker acts using ITS OWN permissions,
// trusting a path the untrusted guest supplied.
host_broker.write_output(path = guest_supplied_path, data):
    open(path, "w")          # broker can write ANYWHERE it has permission,
    write(data)              # including /etc or another tenant's file.
// Guest passes "/var/lib/billing/records" -> broker dutifully corrupts billing.

// FIXED (capability): the guest can only reference resources it was GRANTED.
host_broker.write_output(handle = capability_token, data):
    // 'handle' is an unforgeable token the host issued for ONE specific file
    // inside the guest's sandbox. There is no way for the guest to name
    // /var/lib/billing/records, because it was never granted a capability to it.
    write_via(handle, data)
```

The fix removes the broker's ability to be *confused*: it acts only on the authority the request literally carried.

### TOCTOU at the Boundary: Check-Then-Use vs Use-the-Handle

```text
// VULNERABLE (TOCTOU): validate a NAME, then use the NAME later.
if is_inside_sandbox(path):     # check: looks safe now
    // ... guest swaps 'path' to a symlink -> /etc/shadow ...
    fd = open(path)             # use: opens the swapped target. ESCAPE.

// SAFE: resolve ONCE to a handle, validate the HANDLE, use the SAME handle.
fd = open(path, O_NOFOLLOW)     # resolve once, don't follow symlinks
if fd_is_inside_sandbox(fd):    # validate the thing we actually hold
    read(fd) / write(fd)        # use the same fd; nothing to swap
```

Operate on the resolved object, not the re-resolvable name. The gap is the bug.

### gVisor vs Firecracker: Where the Guest's Syscalls Go (conceptual)

```text
PLAIN CONTAINER:
   guest ── syscall ──────────────────────────────► HOST KERNEL (huge surface)

gVisor:
   guest ── syscall ──► Sentry (userspace kernel, memory-safe, seccomp'd)
                          └─ only a tiny, filtered set ──► host kernel

FIRECRACKER microVM:
   guest ── syscall ──► GUEST's OWN kernel (inside the VM)
                          └─ hardware-virtualized I/O ──► tiny VMM device model ──► host
```

In all three the guest "makes syscalls," but *what those syscalls reach* — and thus the reachable TCB — is radically different.

---

## Coding Patterns

### Pattern 1: Match the Rung to the Threat, Document the Residual Risk

```text
threat -> acceptable residual risk -> cheapest rung that meets it.
Write down what you are NOT protected against (e.g., "shared-host side
channels; kernel 0-days reachable through gVisor's filter"). An undocumented
residual risk becomes someone's surprise breach.
```

### Pattern 2: Interpose a Small Component Between Guest and Big Component

```text
Don't harden the kernel; stop the guest from calling it (gVisor, microVM).
Don't trust the engine alone; wrap it. The strong move is interposition of a
small, auditable shim, not perfection of a large shared dependency.
```

### Pattern 3: Capabilities Instead of Ambient Authority at Every Broker

```text
Any host function / broker that acts on guest-supplied references:
  pass an unforgeable handle that NAMES + AUTHORIZES one resource.
  never act on a path/ID/name using the broker's own ambient permissions.
This is the only structural cure for the confused-deputy class.
```

### Pattern 4: Resolve-Then-Hold to Kill TOCTOU

```text
Resolve the object ONCE (open the fd, with O_NOFOLLOW where relevant),
validate the OBJECT you hold, then use the SAME object. Copy guest-supplied
scalars into host memory once and validate the copy. Never re-resolve names.
```

### Pattern 5: Treat Side Channels as a Separate Axis

```text
For data where cross-tenant inference is in scope:
  - don't co-schedule distrusting tenants on sibling hyperthreads
  - partition or flush caches at trust-domain boundaries
  - constant-time the secret-handling code
  - escalate to dedicated hardware when the stakes justify it
Logical isolation (even a VM) does not, by itself, close this axis.
```

---

## Best Practices

- **Choose isolation by threat model, not by default or fashion.** Map tenant trust and data sensitivity to the cheapest rung whose residual risk you accept — and write that residual risk down.
- **For hostile multi-tenancy, don't lean on plain containers.** Use gVisor or microVMs; treat containers as a deploy/resource boundary, not the security boundary.
- **Minimize the reachable TCB.** Tight seccomp, minimal device models, minimal host imports — every removed interface is removed attack surface.
- **Design brokers and host functions around capabilities,** never ambient authority. This eliminates the confused-deputy class structurally.
- **Eliminate TOCTOU at the boundary:** resolve-then-hold, validate the handle not the name, copy-and-validate guest scalars once.
- **Validate everything flowing *out* of the sandbox.** Outputs are attacker-controlled inputs to the host.
- **Stack independent layers (defense in depth)** and label each layer's blind spot so you know which class is still open.
- **Address side channels separately** when cross-tenant inference is in scope — partitioning, no-SMT-sharing, dedicated hardware, constant-time code.
- **Fail closed and test the boundary by attacking it:** confirm the kernel surface is what you think, that escapes you expect to fail actually fail.
- **Keep the VMM / runtime small and memory-safe,** and sandbox *it* too — the enforcer is itself attack surface.

---

## Edge Cases & Pitfalls

- **"We use containers, so tenants are isolated."** False for hostile multi-tenancy: the shared kernel is the boundary, and it's a weak one. Quantify and address it.
- **A microVM that still shares a core leaks via side channels.** Hardware isolation of memory doesn't imply hardware isolation of caches/branch predictors.
- **gVisor compatibility gaps.** It reimplements the syscall surface; an app relying on an unimplemented or subtly different syscall behaves differently or breaks. Test your actual workload.
- **The VMM is attack surface too.** A device-emulation bug in the hypervisor is a VM escape. Minimal device models exist precisely to shrink this.
- **Capabilities leaked by accident.** Passing a too-broad handle (a directory fd that reaches more than intended, an fd that can be `openat`'d upward) recreates ambient authority. Scope handles tightly.
- **Outputs trusted as safe.** Rendering sandbox output into HTML, a SQL query, or a shell command moves the exploit *outside* the box.
- **TOCTOU in "obviously safe" checks.** Path-prefix checks, symlink assumptions, and re-read length fields are classic gaps.
- **Side-channel mitigations that don't compose.** Disabling SMT on some hosts but co-scheduling distrusting tenants elsewhere in the fleet leaves the weakest host as the breach point.
- **Blast radius underestimated.** Escaping one guest often means reaching the host control plane and thus *every* guest — model the worst case, not the first hop.
- **Over-trusting a memory-safe runtime's host functions.** Wasm's core is safe, but a buggy host import that trusts a guest index reintroduces a memory bug at the boundary.

---

## Common Mistakes

1. **Using plain containers as the security boundary for untrusted, mutually-distrusting tenants.**
2. **Believing a VM/microVM closes side channels** — it doesn't, if hardware is shared.
3. **Building brokers on ambient authority,** then patching confused-deputy bugs one at a time forever.
4. **Check-then-use (TOCTOU) on guest-controlled names** instead of resolve-then-hold on handles.
5. **Trusting sandbox outputs** as if they were the host's own data.
6. **Treating one strong layer as sufficient,** ignoring the class it doesn't cover.
7. **Leaving the VMM/runtime large and unsandboxed,** so the enforcer is itself an easy target.
8. **Not documenting residual risk,** so an accepted trade-off becomes an unexpected breach.
9. **Passing over-broad capabilities/handles** that quietly restore ambient reach.
10. **Choosing isolation strength by habit** rather than by an explicit threat model and cost trade-off.

---

## Tricky Points

- **Stronger logical isolation can still share hardware.** Two Firecracker VMs on one core are *memory*-isolated but *cache*-adjacent — side channels don't respect the VM boundary.
- **gVisor isn't "a smaller kernel" exposed to the guest — it's a *different* kernel (in user space).** The guest's syscalls hit Sentry; the host kernel sees only Sentry's tightly filtered, small set. The win is *which* kernel is reachable.
- **Capabilities don't fix every escape — they fix the *confused-deputy* class.** Kernel bugs, device bugs, and side channels are orthogonal and need their own answers.
- **Shrinking the syscall surface helps containers but can't make the kernel safe;** it reduces *reachable* bugs, not *existing* bugs. The kernel stays a large memory-unsafe TCB.
- **"No ambient authority" (Wasm) is about the *core*; the host imports are where authority comes back in.** A capability-clean core with a sloppy import set is not capability-clean overall.
- **TOCTOU is a property of the *interface*, not the *check*.** Even a correct check is unsafe if the checked thing can change before use. The cure is structural (hold the resolved object), not "check more carefully."
- **The cheapest escape, not the average one, defines your security.** An attacker takes the weakest path — the in-process engine bug, the leaky mount, the side channel — regardless of how strong the headline boundary is.

---

## Apply it

1. State the system invariant that **Sandboxing & Isolation** must protect.
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

- Which invariant must remain true when Sandboxing & Isolation fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
