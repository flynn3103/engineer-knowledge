# Capability-Based Security — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Capability-Based Security** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Two Things a Reference Can Do: Name and Empower

When you say "the file `/etc/passwd`," you are doing **designation** — you are pointing at a resource. When the system then *lets you read it*, that is **authority**. In an ACL world these are split: anyone can *name* `/etc/passwd` (designation is free and universal), and a separate check decides authority.

A **capability fuses them**. The capability *is* the name *and* the permission. There is no separate name you could utter to reach a resource you have no capability for. This fusion is the entire idea. Everything else follows from it.

### 2. Ambient Authority — The Default Most Programs Live In

Run an ordinary program. It can `open("/anything")`, connect to any host, read any environment variable, delete files in `/tmp`. It did not have to be *handed* these abilities for the specific call — they hang in the air around it, inherited from the user who launched it. This is **ambient authority**.

Ambient authority is convenient. It is also the root of a surprising amount of insecurity, because **every line of code in the process has all of it**. A logging library you imported can read your SSH keys. A JSON parser can open a socket. None of them *need* to, but the ability is ambient, so nothing stops them.

### 3. The Confused Deputy — The Bug Ambient Authority Causes

This is the canonical story, from Norm Hardy (1988). A pay-for-use compiler runs on a shared system. It has two jobs and two authorities:

1. Compile the user's source file (it must be able to read the file the user names).
2. Write a billing record into a system file `BILL`, recording that the user owes money (it must be able to write `BILL` — an authority the *user* does not have).

The compiler accepts a command-line argument: *the name of the output file* to write the compilation results into. A clever user runs:

```text
compile  myprogram.src  -o BILL
```

The compiler, doing exactly what it was told, opens the user-named output file `BILL` and writes compiler output into it — **destroying the billing records**. The user could not write `BILL` directly; the system would have refused. But the compiler *could*, and the user **tricked the compiler into using its own authority on the user's behalf.** The compiler is the "deputy"; it is "confused" about whose authority it is exercising.

Why did this happen? Because the output file was *designated by a name* (`BILL`), and the authority to write it was *ambient* (the compiler had it for its own reasons). The two were separate. The compiler had no way, from the bare name `BILL`, to know that *the user* had no right to it.

### 4. How a Capability Structurally Prevents It

Now imagine the user does not pass a *name* but a **capability** — an already-opened, writable handle to the output file. To create that handle, the user had to *already hold* the authority to write there. The compiler simply writes through the handle it was given.

The user **cannot** produce a capability to `BILL`, because the user has no capability to `BILL` to begin with. There is no string they can type to conjure one. The attack evaporates — not because the compiler defended against it, but because **the bad request is unrepresentable.** Designation now *carries* authority, so the user can only designate what they were already allowed to touch.

This is the affirmative power of the model: it does not detect the confused deputy and reject it. It makes the confused deputy *impossible to express*.

### 5. POLA — The Principle of Least Authority

If authority only flows by being handed a capability, you naturally hand each component just the keys it needs. A PDF thumbnail generator gets a read handle to *one* PDF and a write handle to *one* output image — and nothing else. No filesystem, no network, no environment. If that library is malicious or compromised, the blast radius is two file handles. This is **POLA**: least authority, granted explicitly, per component.

POLA is the security payoff of capabilities, and it is why this topic is the *constructive* side of security: instead of listing everything an attacker might do and blocking each, you deny *all* authority by default and grant back the minimum.

### 6. Capabilities You Already Use

You have used capabilities for years without the name:

- **A Unix file descriptor.** `open("/etc/passwd", O_RDONLY)` checks the ACL *once*, then returns an `fd` — say `3`. From then on, `read(3, ...)` does **no path check**. Holding fd 3 *is* the authority to read that open file. You can even pass fd 3 to another process over a Unix socket, and now *it* can read the file with no path lookup. That is delegation of a capability.
- **An unguessable URL.** A "secret link" to a Google Doc, a Dropbox share link, a password-reset link. Anyone who holds the URL can act; there is no login. The unguessable string *is* the key. (This is why such links must be long and random — a forgeable capability is no capability.)
- **An OAuth bearer token.** Your app gets a token; every request carries it; the server honors whoever presents it. The token names a scope of access and grants it. A capability with an expiry.
- **An object reference in a memory-safe language.** If you hold a reference to a `BankAccount` object, you can call `.withdraw()`. If you were never given the reference, you cannot reach the object at all — there is no `findAccountByName()` available to you. This is the purest form: an **object capability**.

The lesson for a junior: capabilities are not exotic. They are *handles you were given*, and the security comes from controlling **who gets handed what**.

---

## Code Examples

We will contrast the two models with the **confused-deputy** scenario, then show capabilities as plain dependency injection. The point at this level is the *shape*, not a specific framework.

### The Ambient-Authority Version (the vulnerable shape)

```python
# AMBIENT AUTHORITY: any code in this process can open any path.
import os

BILLING_FILE = "/var/lib/compiler/BILL"

def record_charge(user):
    with open(BILLING_FILE, "a") as f:        # the deputy's own authority
        f.write(f"{user} owes $5\n")

def compile_source(src_path, out_path):
    record_charge(current_user())
    source = open(src_path).read()            # reads whatever path it's told
    result = do_compile(source)
    with open(out_path, "w") as f:            # writes whatever path it's told
        f.write(result)

# The attack: the user controls out_path.
compile_source("myprogram.src", "/var/lib/compiler/BILL")
# -> compiler output overwrites the billing file. Confused deputy.
```

`open()` is **ambient** — it reaches the whole filesystem. The user supplied a *name*, and the deputy's own authority did the rest. Nothing in the type signature reveals that `out_path` is dangerous.

### The Capability Version (the safe shape)

```python
# CAPABILITY STYLE: authority arrives as handles, not names.
# The function can ONLY write through the handle it was given.

def compile_source(source_text, out_file, charge_fn):
    """
    source_text : already-read string (no path, no read authority)
    out_file    : an OPEN writable file object (a capability)
    charge_fn   : a closure that records a charge (a capability to bill)
    """
    charge_fn()                      # can bill, because it was handed that power
    result = do_compile(source_text)
    out_file.write(result)           # can ONLY write where out_file points

# The caller decides what authority to hand in:
with open("myprogram.src") as src, open("out.o", "w") as dst:
    def charge():
        with open("/var/lib/compiler/BILL", "a") as b:  # caller holds BILL authority
            b.write("alice owes $5\n")
    compile_source(src.read(), dst, charge)
```

Now `compile_source` has **no `open`, no path, no filesystem.** It cannot touch `BILL` even if it wanted to, because it holds no handle to it. The authority to write `BILL` lives only in `charge`, which the *caller* (who legitimately has it) constructed. The malicious "`-o BILL`" trick has nothing to attack: there is no path argument to poison. The bug is now **unrepresentable**.

> **Note:** This is "just" passing arguments instead of importing `os`. That is the whole secret. Capability security at the language level is **disciplined dependency injection of authority**, where the discipline is: *never import ambient power; always receive it.*

### A File Descriptor Is a Capability (C)

```c
// open() checks the ACL ONCE, here:
int fd = open("/etc/hosts", O_RDONLY);   // path -> authority check -> handle

// From now on, NO path, NO recheck — the fd IS the authority:
char buf[256];
read(fd, buf, sizeof buf);               // uses the held capability

// You can DELEGATE it to another process over a Unix socket:
send_fd_over_socket(peer, fd);           // the peer can now read the file,
                                         // with no path lookup of its own
```

The integer `fd` behaves exactly like a capability: unforgeable (you can't invent a valid fd for a file you never opened), transferable (SCM_RIGHTS over a Unix socket), and it fuses designation (which open file) with authority (read it).

### Object Capability in a Memory-Safe Language (Java-ish)

```java
// You can act on an account ONLY if you hold its reference.
final class Account {
    private long cents;
    void deposit(long c)  { cents += c; }
    void withdraw(long c) { if (c <= cents) cents -= c; }
}

// A function that receives the capability:
void payRent(Account tenant, Account landlord, long rent) {
    tenant.withdraw(rent);
    landlord.deposit(rent);
}
// payRent can touch EXACTLY these two accounts. It has no registry,
// no "lookup account by name", no ambient list of all accounts.
// If it was never handed your account, it can never reach it.
```

There is no `AccountRegistry.find("alice")` here. The *absence* of an ambient lookup is the security. Authority is the reference itself.

---

## Coding Patterns

### Pattern 1: Inject authority, never import it

```python
# BAD (ambient): the module reaches the world by itself
import requests
def fetch(url): return requests.get(url)

# GOOD (capability): the caller hands in the power to do HTTP
def fetch(http_client, url): return http_client.get(url)
```

The rule: a module's import list should contain *no* sources of authority (`os`, `socket`, `requests`, `open`). All authority arrives as parameters.

### Pattern 2: Hand a narrow handle, not a broad one (attenuation)

```python
# Instead of passing the whole filesystem or a directory:
process_upload(open(user_file, "rb"))   # one read handle, nothing else
```

Give the callee the *least* it needs: one open file, not a directory; a read handle, not read-write; one bucket prefix, not the bucket.

### Pattern 3: Wrap to attenuate rights

```python
class ReadOnly:
    def __init__(self, f): self._f = f
    def read(self, n=-1): return self._f.read(n)
    # deliberately no write(): the wrapper REMOVES authority

process(ReadOnly(open("data.bin", "rb")))
```

A wrapper that exposes a *subset* of the underlying capability's methods is the simplest attenuation device.

### Pattern 4: Create-then-hand (parenthood)

```python
sandbox_dir = make_temp_dir()             # you create the resource
plugin.run(workspace=sandbox_dir)         # and hand the plugin ONLY that
# the plugin can scribble in its sandbox and reach nothing else
```

The component that *creates* a resource holds its capability and decides who else gets it.

### Pattern 5: Token as capability (across a network)

```text
# A signed, expiring URL is a remote capability:
https://files.example.com/d/9f3a...e1?sig=...&exp=1719300000
# Whoever holds it may download THAT object until it expires.
# Unguessable + signed = unforgeable. Expiry = built-in revocation.
```

---

## Best Practices

- **Default to no authority.** A new component starts with zero capabilities. Grant back only what a task provably needs.
- **Pass handles, not names.** If an API takes a *path* or an *account id and looks it up*, it is ambient. Prefer an already-opened handle or an already-resolved object.
- **Keep the authority-holding surface small.** The fewer places that hold the powerful keys (the real `open`, the network), the smaller your trusted base.
- **Make capabilities unguessable when they're tokens.** Long, random, signed. A guessable URL or token is a forgeable capability — i.e., not a capability at all.
- **Attenuate on delegation.** When you pass a capability onward, pass the *weakest* sufficient version (read-only, single-resource, time-limited).
- **Design revocation in from the start.** Decide *how* a handed-out capability gets disabled before you hand it out. (The pattern for this — a revocable forwarder — is `senior.md` material.)
- **Audit by following references, not by reading policy.** "What can this module touch?" is answered by listing the capabilities it was given.

---

## Edge Cases & Pitfalls

- **One ambient import undoes everything.** A module that receives a tidy set of capabilities but *also* does `import os` has full ambient authority again. The discipline is only as strong as its weakest module.
- **A capability you can't revoke is a capability forever.** Hand someone a raw file handle and you can never take it back. If you may need to revoke, hand a *wrapper* you control, not the raw thing.
- **Forgeable "capabilities" aren't.** A short, guessable URL or a sequential token is something an attacker can manufacture. Designation-equals-authority only holds if the token is unforgeable.
- **Leaking a capability = leaking authority.** Logging a signed URL, putting a token in an error message, or storing a handle where untrusted code can read it hands out the key.
- **Bearer tokens have no identity, by design.** That is the point *and* the risk: whoever steals one *is* authorized. Treat them like keys, not like passwords.
- **Ambient authority hides in "helpful" globals.** A logger that writes to a fixed file, a config that reads env vars, a singleton database connection — all are ambient authority smuggled in through the back door.
- **Amplification surprises.** Some systems let two weak capabilities *combine* into a stronger one ("rights amplification"). Convenient, but it means "what can this hold?" is not always just the union of its keys.

---

## Common Mistakes

1. **Passing a name and "checking permission separately."** That *is* the ACL model and *is* the confused-deputy setup. Pass the handle instead.
2. **Calling it capabilities while keeping ambient `open`/`socket`.** If the module can still reach the world on its own, you have an ACL system wearing a costume.
3. **Treating a guessable URL/token as secure.** Forgeable tokens give attackers free capabilities.
4. **Handing out raw handles when you'll need to revoke.** Always wrap if revocation might be required.
5. **Logging or serializing capabilities.** Tokens in logs, handles in dumps — you just published the keys.
6. **Granting a directory when one file would do.** Over-broad authority defeats POLA; the blast radius is everything you handed, not everything that was used.
7. **Assuming the OS does this for you.** Mainstream Unix/Windows are ACL-based with heavy ambient authority. Capability discipline is something *you* impose in your design.
8. **Conflating identity with authority.** "Who is the caller?" is the wrong question in this model; "what handle did they pass?" is the right one.

---

## Tricky Points

- **The check moves from *use-time* to *grant-time*.** An ACL checks every access; a capability checks once, when it is created/granted, and never again. That is faster *and* it is what makes the confused deputy impossible — but it means **getting the grant right is everything.**
- **Designation = authority is the whole theorem.** Every property (no confused deputy, easy POLA, follow-the-references auditing) is a corollary of fusing the name and the right. If you ever split them again, you lose the guarantees.
- **A capability system can *emulate* an ACL, but not vice versa cheaply.** You can build identity checks on top of capabilities (hand each user a personalized facet). Going the other way — getting confused-deputy safety out of an ambient-ACL system — requires bolting on capabilities (like file descriptors already are).
- **"No ambient authority" is a property of the *whole* environment, not one function.** A pure function in an impure language still lives in a process with ambient `open`. True ocap requires the *language/runtime* to deny ambient access (no global `import os`), which is why dedicated ocap languages exist.
- **Bearer tokens prove the model is everywhere.** Every "secret link" and OAuth token is a capability. The web reinvented capabilities because, across a trust boundary with no shared identity, *holding the secret* is the only thing that scales.

---

## Apply it

1. Choose one small, known input for **Capability-Based Security**.
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

- What problem does Capability-Based Security solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
