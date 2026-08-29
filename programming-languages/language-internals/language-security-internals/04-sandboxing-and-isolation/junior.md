# Sandboxing & Isolation — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Sandboxing & Isolation** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Trusted vs Untrusted Code

The first question to ask about any code is: **do I trust it?** Trust here is binary in spirit: either you wrote/audited it and will give it power, or you didn't and you won't. The danger zone is the huge amount of code in between — dependencies, plugins, user input that gets executed, scripts from the internet. The default professional stance is: **code I didn't write is untrusted until contained.**

A sandbox is the tool for the untrusted column. You run trusted code normally; you run untrusted code in a box.

### 2. Least Privilege

**Least privilege** means a program should have exactly the permissions it needs and not one more. A function that resizes images needs to read the input image and write the output image. It does **not** need network access, the ability to read your password file, or permission to launch other programs. If you grant it only "read this file, write that file," then even a malicious image-resizer is harmless — it has no power to misuse.

Least privilege is the *goal*; a sandbox is the *enforcement mechanism*. The sandbox is where you actually take away everything the code doesn't need.

### 3. Ambient Authority — The Root Problem

Here's the uncomfortable default of normal programs: when you run a program, it inherits *your* power. It can open any file your user account can open, connect to any server, spawn any process. It has this power **automatically, without asking** — that's called **ambient authority**. The program didn't request file access; it just *has* it, in the air around it, like ambient light.

Ambient authority is why a single malicious script can do so much damage: it starts the game with all of your permissions already in hand. Sandboxing is largely about **removing ambient authority** — taking away the automatic power and forcing code to use only the specific permissions you handed it.

### 4. The Boundary: Inside vs Outside

Every sandbox has a **boundary** — a wall separating "inside the box" from "the host." The entire job of the sandbox is to make sure that:

- Code inside cannot read or write memory outside.
- Code inside cannot perform sensitive actions (file, network, process) except through doors you opened.
- Even if the code inside is fully malicious, the damage is confined to the box.

The boundary is where security lives. A **sandbox escape** is what we call it when code crosses that boundary it wasn't supposed to. Designing a sandbox is largely designing a boundary that is hard to cross.

### 5. The Simplest Sandbox: A Separate Process

The OS already gives you a basic, free isolation boundary: the **process**. Each process has its own memory; one process cannot directly read another process's memory. So the first, cheapest sandboxing move is: **run the untrusted code in a separate process.** If it crashes, only that process dies — your main program survives. If it corrupts memory, it corrupts *its own* memory, not yours.

A separate process alone is weak (the untrusted process still has your file and network access), but it's the foundation that everything else builds on. Strong sandboxes start with "separate process" and then *add restrictions* on top: no network, restricted filesystem, limited syscalls.

### 6. The Three Big Things to Restrict

When you sandbox code, you're usually limiting three categories of power:

| Resource | What unrestricted code can do | What a sandbox does |
|----------|-------------------------------|---------------------|
| **Filesystem** | Read/write/delete any file you can. | Allow only a specific directory, or nothing at all. |
| **Network** | Open connections anywhere. | Block all sockets, or allow only specific hosts. |
| **Process / system** | Spawn shells, run other programs, read system info. | Forbid creating new processes; block dangerous syscalls. |

A fourth, quieter one is **resources** — CPU time, memory, disk space — so that buggy or malicious code can't simply hog the machine (a denial-of-service). Limiting these is also part of isolation.

### 7. The Spectrum: Weak/Cheap to Strong/Expensive

There is no single "the sandbox." There's a **spectrum**, trading isolation strength against performance cost:

```text
WEAKER, CHEAPER  ◄──────────────────────────────────────►  STRONGER, COSTLIER

in-process    →   OS-level     →   WebAssembly   →   containers   →   microVMs / full VMs
language          sandbox          sandbox            (OS features)     (hardware virtualization)
sandbox           (seccomp,        (Wasm/WASI)
(V8 isolate)      namespaces)
```

- **In-process** (e.g., a JavaScript engine running untrusted JS): fast, lightweight, but fragile — a single memory-safety bug in the engine can let the guest reach into the host.
- **OS-level** (restricting syscalls and visible resources): stronger, still cheap, shares the kernel.
- **WebAssembly**: designed from scratch to be a sandbox — no ambient authority, isolated memory.
- **Containers**: convenient packaging + some isolation, but famously "not a security boundary" on their own.
- **microVMs / VMs**: each guest gets its own kernel and hardware-enforced boundary — strongest, but heavier to start and run.

The right point on this spectrum depends on *how much you distrust the code* and *how much performance you can spend*. Running your own helper script? A process limit is fine. Running arbitrary code uploaded by anonymous strangers on a shared server? You want something near the strong end.

### 8. Sandboxing Is One Layer, Not the Whole Story

A crucial early lesson: **a sandbox is one layer of defense, not a magic force field.** Good security uses **defense in depth** — multiple independent layers, so that breaking one doesn't break everything. A sandbox plus memory-safe code plus careful design is far stronger than any single one. Never think "it's sandboxed, so it's safe." Think "it's sandboxed, which is one of several reasons it's hard to abuse."

---

## Code Examples

These examples are intentionally simple and conceptual — they show the *shape* of sandboxing ideas, not production-grade enforcement. (Real OS enforcement is in `middle.md`.)

### The Problem: Running Untrusted Code With Full Power (don't do this)

```python
# DANGEROUS: this hands untrusted code ALL of your ambient authority.
untrusted_code = get_code_from_user()   # could be anything
exec(untrusted_code)                     # runs with full access to files, network, OS
```

`exec` runs the string as Python *inside your process*, with everything your program can do. The untrusted code can `import os; os.system("rm -rf ~")`, read your secrets, or open network connections. This is the *anti-pattern*: untrusted code + full ambient authority + same process. Every concept below is about removing pieces of that danger.

### Step 1: Run It In a Separate Process

```python
import subprocess

# At least now a crash or memory corruption is confined to a child process,
# and we can kill it, time-limit it, and (later) strip its permissions.
result = subprocess.run(
    ["python3", "untrusted_script.py"],
    timeout=2,                 # resource limit: don't let it run forever
    capture_output=True,       # we read its output rather than letting it touch ours
)
```

This is weak — the child still has your file and network access — but it's the foundation. We now have a *boundary* (the process) and we've added a *resource limit* (timeout). Next steps add real restrictions.

### Step 2: Take Away the Network (conceptual)

```text
Idea: launch the untrusted process in an environment where the network
simply does not exist for it.

  - No network interface is visible to it.
  - Any attempt to open a socket fails immediately, because there is
    nothing to connect through.

On Linux this is done with a "network namespace" (covered in middle.md):
the child sees an empty network — not even localhost — so even fully
malicious code cannot phone home. The point: we removed the *ability*,
not just forbade the *intent*.
```

### Step 3: Restrict the Filesystem to One Directory (conceptual)

```text
Idea: make the untrusted code see ONLY a small directory as its whole world.

  /sandbox/
    input.txt      <- the one file it may read
    output.txt     <- the one file it may write

It cannot see /etc, /home, your SSH keys, or anything else — those paths
simply do not exist from inside the box. If it tries to open
"/home/you/.ssh/id_rsa", the open fails with "no such file".

This is "least privilege" applied to the filesystem: one input door,
one output door, no others.
```

### A Real In-Process Sandbox: JavaScript in the Browser

The most widely deployed sandbox on earth is the one running JavaScript on web pages. When you visit a site, its JavaScript runs in a heavily restricted environment:

```javascript
// JavaScript running on a web page CANNOT do these:
//   - read arbitrary files on your disk
//   - open a raw TCP socket to any server
//   - read another website's data (the "same-origin policy")
//   - launch a program on your computer
//
// It CAN only do what the browser explicitly exposes, e.g.:
fetch("/api/data");            // network, but only to allowed origins (rules apply)
localStorage.setItem("k","v"); // a tiny key-value store scoped to this site
document.querySelector("h1");  // the page's own content, nothing else
```

Every website is untrusted code, yet you run thousands of them a day without disaster — because the browser sandbox removes ambient authority by default. JavaScript starts with *almost no* power and is handed specific, narrow capabilities.

### WebAssembly: A Sandbox By Design

WebAssembly (Wasm) is a portable binary format built to run untrusted code safely. Its key property: **it has no ambient authority at all.** A Wasm module cannot, on its own, touch files, network, or the host's memory.

```text
A WebAssembly module by itself can ONLY:
  - do math and logic
  - read/write its OWN isolated block of memory ("linear memory")

It CANNOT, on its own:
  - read host files
  - open network connections
  - call host functions

The host must EXPLICITLY hand the module specific functions to call.
If the host gives it nothing, the module is a pure calculator with no
way to affect the outside world. This is "capability-based": the module
has exactly the powers it was handed, and nothing more.
```

This is why Wasm is increasingly used to run untrusted plugins, edge functions, and serverless code: the safe default ("can do nothing") is built into the design, not bolted on.

---

## Coding Patterns

### Pattern 1: Deny-by-Default (allowlist, not blocklist)

```text
WRONG (blocklist):  allow everything, then forbid the dangerous syscalls/paths.
                    -> you will forget one; attacker uses the one you forgot.

RIGHT (allowlist):  forbid everything, then permit only the few things needed.
                    -> the unknown/forgotten stays forbidden, which is safe.
```

Every good sandbox is an allowlist. If you catch yourself listing things to *block*, stop and invert it.

### Pattern 2: Separate Process First, Then Restrict

```text
1. Move untrusted code into its own process.   (boundary)
2. Strip its network.                          (remove a power)
3. Confine its filesystem to one directory.    (remove a power)
4. Limit CPU/memory/time.                       (anti-DoS)
5. (Advanced) restrict its syscalls.           (shrink attack surface)
```

Build the sandbox in layers, each removing one category of power.

### Pattern 3: Pass Capabilities, Don't Grant Authority

```text
WRONG: untrusted code can open ANY file it wants (ambient authority).
RIGHT: the host opens the one allowed file and hands the OPEN HANDLE in.
       The code can use that handle, but cannot name or open any other file.
```

Instead of giving the code the *power to open files*, give it *the one file*. This is the core of capability thinking.

### Pattern 4: Set a Hard Resource Budget

```text
Always cap: wall-clock time, CPU time, memory, output size.
A sandbox that perfectly blocks files and network but lets code run an
infinite loop or allocate all RAM is still a denial-of-service waiting
to happen. "Can't do harm" includes "can't hog the machine."
```

### Pattern 5: Validate at the Boundary, Not Inside

```text
Anything crossing from inside the sandbox to outside (return values,
file contents, messages) is UNTRUSTED OUTPUT. Validate and sanitize it
on the OUTSIDE before trusting it. The boundary is a checkpoint in both
directions.
```

---

## Best Practices

- **Treat any code you didn't write as untrusted until contained.** Dependencies and plugins included.
- **Start from zero permissions and add the minimum.** Deny-by-default, always.
- **Sandbox risky *parsers* of untrusted *data*, not just untrusted *code*.** The hostile thing is often the input.
- **Always set resource limits.** Time, CPU, memory, output. Prevent denial-of-service, not just data theft.
- **Use the strongest isolation the performance budget allows for code you distrust most.** Anonymous, arbitrary code → lean toward VMs/microVMs.
- **Don't rely on a single layer.** Combine sandbox + memory-safe languages + minimal granted powers. Defense in depth.
- **Prefer purpose-built sandboxes over hand-rolled ones.** Browsers, Wasm runtimes, and established container/microVM tools have had far more scrutiny than anything you'll write in an afternoon.
- **Remember containers are packaging, not a hard security wall.** Add real isolation (seccomp, user namespaces, or a microVM) when running untrusted tenants.
- **Validate everything that crosses the boundary outward.** The sandbox's output is still untrusted.
- **Keep the sandboxed code's interface tiny.** The fewer functions you expose to the guest, the smaller the attack surface.

---

## Edge Cases & Pitfalls

- **"It's sandboxed, so it's safe."** No sandbox is perfect. Treat the sandbox as risk *reduction*, not risk elimination. Keep other layers.
- **Forgetting resource limits.** A perfectly file/network-isolated process can still freeze your machine with an infinite loop or memory bomb.
- **In-process sandboxes and memory bugs.** If untrusted code runs *inside your process* (like a scripting engine), a memory-safety bug in the engine can let the guest read or corrupt the host's memory. This is why in-process sandboxes are inherently fragile.
- **Blocklist thinking.** Trying to enumerate and block "the dangerous things" instead of allowing only the safe few. You'll always miss one.
- **Leaky boundaries.** Handing the sandbox a file handle, an environment variable, or a callback that quietly exposes more than you intended. Every door you open is part of the attack surface.
- **Trusting sandbox output.** Data coming *out* of the sandbox is still attacker-controlled. Don't paste it straight into a database query, HTML page, or shell command.
- **Assuming containers isolate like VMs.** Containers share the host kernel; a kernel bug can let a container escape. They're great for packaging, weaker as a security boundary.
- **The shared component.** If the host and guest share something — a clipboard, a temp directory, a cache, a kernel — that shared thing is a path the attacker will probe.
- **Time-of-check vs time-of-use.** Checking a permission and then acting on it leaves a gap where things can change between the check and the use. (Explored more at higher levels.)

---

## Common Mistakes

1. **Running untrusted code with `exec`/`eval` in your own process.** Maximum danger, zero isolation. Almost never acceptable.
2. **Granting broad permissions "to make it work," then never tightening them.** The temporary `allow all` becomes permanent.
3. **Blocking known-bad instead of allowing known-good.** Blocklists leak.
4. **Skipping resource limits.** Forgetting that hogging the machine is also an attack.
5. **Treating a container as a strong security boundary for hostile tenants.** It isn't, by itself.
6. **Forgetting that the *input data* is the threat.** Sandboxing the code but feeding it a malicious file that exploits the parser.
7. **Trusting whatever comes back out of the sandbox.** Output is still untrusted.
8. **Hand-rolling a sandbox.** Custom sandboxes are notoriously leaky; use battle-tested ones.
9. **One layer only.** Relying solely on the sandbox with no memory safety, no input validation, no monitoring.
10. **Confusing "we scanned it and it looked clean" with "it can't do harm."** Detection is not containment.

---

## Apply it

1. Choose one small, known input for **Sandboxing & Isolation**.
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

- What problem does Sandboxing & Isolation solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
