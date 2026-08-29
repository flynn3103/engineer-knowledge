# Dynamic Linking & Loading — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Dynamic Linking & Loading** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why the GOT Exists: PIC Needs Indirection

A shared library can be loaded at a *different address* in every process (and at a random address every run, thanks to ASLR). So its code cannot contain hard-coded absolute addresses for external functions and globals — those addresses aren't known until load time and differ per process.

The solution is **one layer of indirection**: instead of "jump to the absolute address of `printf`," position-independent code does "load the pointer from *my* GOT slot for `printf`, then jump there." The *code* (in the read-only, shareable `.text`) stays identical in every process. Only the *GOT* (a small, writable, per-process table) gets patched with the addresses that vary. This is the central trick that makes code sharing and ASLR both possible.

So: **the GOT is the one writable place where per-process, resolved-at-load-time addresses live.** The code is constant; the GOT is the variable part.

### 2. The PLT: A Stub Per Function

For *function* calls there's a second table, the PLT, because of lazy binding. Each imported function gets:

- A **PLT stub** (in `.plt`, read-only, shared): a few instructions.
- A **GOT slot** (in `.got.plt`, writable, per-process): a pointer.

Your code calls `printf@plt` (the stub), not `printf` directly. The stub's job is: "jump to wherever my GOT slot points." Initially that slot points *back into the PLT* at the resolver trampoline — so the first call detours into the loader. After resolution the slot points at real `printf`, and the same stub now jumps straight there.

A classic PLT stub (x86-64, simplified):

```asm
printf@plt:
    jmp   *printf@got(%rip)     ; jump to whatever the GOT slot holds
    ; --- first time, the GOT slot points HERE, at the lazy trampoline: ---
    push  $relocation_index     ; which symbol? push its index
    jmp   PLT0                  ; jump to the common resolver trampoline

PLT0:                           ; the shared "go ask the loader" stub
    push  GOT[1]                ; loader's bookkeeping (link_map)
    jmp   *GOT[2]               ; jump to _dl_runtime_resolve
```

### 3. The First-Call Resolution Dance

Walk through the *first* call to `printf` with lazy binding on:

1. Your code executes `call printf@plt`.
2. The PLT stub does `jmp *printf@got`. But the GOT slot still holds its *initial* value — the address of the `push $index; jmp PLT0` sequence right below.
3. So control falls to `push $relocation_index; jmp PLT0`.
4. `PLT0` pushes the loader's bookkeeping pointer and jumps to `_dl_runtime_resolve`.
5. `_dl_runtime_resolve` looks up symbol number `index` (`printf`), searches the loaded libraries for its definition, and finds its real address.
6. **It writes that real address into `printf`'s GOT slot** — the patch.
7. It then jumps directly to `printf` (so this first call still completes normally).

Now the *second* call to `printf`:

1. `call printf@plt`.
2. `jmp *printf@got` — and the GOT slot now holds the real address of `printf`.
3. Straight to `printf`. No loader, no resolution. Just one indirect jump.

That's the whole magic. **First call: detour through the loader, patch the GOT. Every later call: one indirect jump.**

### 4. Lazy vs Eager (Now) Binding

**Lazy binding (default for functions):**

- *Pro:* You only resolve symbols you actually call. A program that imports 2,000 functions but uses 50 pays for 50. Startup is faster.
- *Con:* The first call to each function carries a one-time latency spike. Bad for latency-sensitive paths and for predictability.
- *Con (security):* The GOT is writable for the program's lifetime, so an attacker who can overwrite a GOT slot can hijack a call ("GOT overwrite"). This is the classic motivation for **RELRO**.

**Eager / now binding (`-z now`, `LD_BIND_NOW=1`):**

- The loader resolves *everything* at load time, before `main`.
- *Pro:* No first-call spikes; fully deterministic latency. Combined with **full RELRO** (`-z now -z relro`), the GOT can be made *read-only* after relocation, defeating GOT-overwrite attacks.
- *Con:* Slower startup if you import a lot and use a little — you pay to resolve symbols you may never call.

The rule of thumb: **lazy for fast startup, eager+RELRO for security and latency determinism.** Security-hardened distros increasingly default to full RELRO.

### 5. The ELF Dynamic Section: the Loader's Instruction Sheet

How does the loader know which libraries to load, where the relocations are, where the GOT is? It reads the **`.dynamic`** section — an array of `(tag, value)` entries. Key tags:

| Tag | Meaning |
|-----|---------|
| `DT_NEEDED` | Name of a required library. One per dependency. |
| `DT_SONAME` | This library's own soname. |
| `DT_RPATH` / `DT_RUNPATH` | Extra search paths baked in. |
| `DT_JMPREL` / `DT_PLTRELSZ` / `DT_PLTREL` | The PLT relocations (the `JUMP_SLOT`s). |
| `DT_RELA` / `DT_RELASZ` | The non-PLT relocations (data, `GLOB_DAT`). |
| `DT_SYMTAB` / `DT_STRTAB` | The dynamic symbol and string tables. |
| `DT_HASH` / `DT_GNU_HASH` | The symbol hash table — for fast lookup by name. |
| `DT_INIT` / `DT_INIT_ARRAY` | Initializer (constructor) functions to run before `main`. |
| `DT_FINI` / `DT_FINI_ARRAY` | Finalizer (destructor) functions to run at unload/exit. |
| `DT_FLAGS` (`DF_BIND_NOW`) | Request eager binding. |

`readelf -d ./app` prints exactly this. When you debug a linking problem at this level, you're often reading the dynamic section to confirm what the binary actually asks for.

### 6. Initializers Run Before `main` (and via the dynamic section)

`DT_INIT_ARRAY` lists functions the loader calls *after* relocation but *before* `main`. This is how C++ runs constructors for global objects, how `__attribute__((constructor))` functions fire, and how some libraries set themselves up. The mirror, `DT_FINI_ARRAY`, runs at process exit or library unload. Knowing this explains "why is code running before `main`?" — the loader is executing the init array.

---

## Code Examples

### See the PLT and GOT in a real binary

```text
$ cat > prog.c <<'EOF'
#include <stdio.h>
int main(void){ puts("a"); puts("b"); return 0; }
EOF
$ gcc prog.c -o prog -no-pie -fno-stack-protector

$ objdump -d -j .plt prog        # the PLT stubs
0000000000401020 <puts@plt>:
  401020: ff 25 e2 2f 00 00     jmp    *0x2fe2(%rip)   # GOT slot for puts
  401026: 68 00 00 00 00        push   $0x0            # relocation index 0
  40102b: e9 e0 ff ff ff        jmp    401010 <PLT0>

$ readelf -r prog | grep puts    # the relocation that fills the GOT slot
000000404018  ...  R_X86_64_JUMP_SLOT  0000000000000000 puts@GLIBC_2.2.5
```

`R_X86_64_JUMP_SLOT` is the lazily-resolved kind. The GOT slot at `0x404018` starts as a pointer back into the PLT and becomes `puts`'s real address after the first call.

### Watch lazy resolution happen, then watch it not happen again

```text
$ LD_DEBUG=bindings ./prog 2>&1 | grep puts
   <pid>: binding file ./prog to /lib/.../libc.so.6: normal symbol `puts'
   # printed ONCE — the first call. The second call to puts produces no
   # binding line, because the GOT slot is already patched.
```

`LD_DEBUG` is the loader's verbose mode and a superb teaching/debugging tool. `LD_DEBUG=help ./prog` lists categories.

### Force eager binding and confirm the difference

```text
$ LD_BIND_NOW=1 LD_DEBUG=bindings ./prog 2>&1 | grep -c "symbol"
   # Now ALL symbols bind at startup, before main runs — many lines,
   # all emitted before the program's own output.

# Build with eager binding + full RELRO baked in:
$ gcc prog.c -o prog_hard -Wl,-z,relro,-z,now
$ readelf -d prog_hard | grep -E "BIND_NOW|FLAGS"
   0x...  (FLAGS)    BIND_NOW
$ readelf -l prog_hard | grep RELRO
   GNU_RELRO  ...
```

With `-z now -z relro` the loader resolves everything up front and then remaps the GOT read-only — a GOT-overwrite exploit now hits a write fault.

### Read the dynamic section directly

```text
$ readelf -d ./prog
 Tag        Type            Name/Value
 0x0001 (NEEDED)            Shared library: [libc.so.6]
 0x000c (INIT)              0x401000
 0x0019 (INIT_ARRAY)        0x403e10
 0x0017 (JMPREL)            0x4005a0
 0x0007 (RELA)              0x400540
 0x0005 (STRTAB)            0x400400
 0x0006 (SYMTAB)            0x400320
 ...
```

This is the literal instruction sheet the loader follows. `NEEDED` is the shopping list; `JMPREL` points at the PLT relocations; `INIT_ARRAY` lists pre-`main` constructors.

### A constructor that runs before main

```c
#include <stdio.h>
__attribute__((constructor)) static void setup(void) {
    puts("[ctor] runs before main, via DT_INIT_ARRAY");
}
int main(void){ puts("[main]"); return 0; }
```

```text
$ gcc ctor.c -o ctor && ./ctor
[ctor] runs before main, via DT_INIT_ARRAY
[main]
```

The loader executed `setup` from the init array before transferring control to `main`.

---

## Coding Patterns

### Pattern 1: Use `LD_DEBUG` to teach yourself what the loader did

`LD_DEBUG=libs` (search), `LD_DEBUG=bindings` (symbol resolution), `LD_DEBUG=reloc` (relocations), `LD_DEBUG=statistics` (timing). This is the highest-signal way to learn and debug at this level. No code changes needed.

### Pattern 2: Choose binding mode at link time, deliberately

For a server where tail latency matters, `-Wl,-z,now,-z,relro` removes first-call spikes and hardens the GOT. For a short-lived CLI launched millions of times, lazy may start fractionally faster. Measure, don't guess.

### Pattern 3: Read `readelf -d` before blaming your code

Surprising pre-`main` behavior, a missing dependency, or an unexpected search path all show up in the dynamic section. Read it first.

---

## Best Practices

1. **Prefer `-z relro -z now` for production servers and security-sensitive binaries.** The hardening usually outweighs the startup cost; profile the startup if it's a hot loop.
2. **Don't fight the GOT/PLT — understand it.** A one-time first-call cost is normal and expected; don't "optimize" it away by accident with brittle hacks.
3. **Build shared libraries with `-fPIC`** (and prefer `-fvisibility=hidden` to export only what you mean to — fewer exported symbols means faster resolution and fewer interposition surprises).
4. **Use `readelf`/`objdump`/`LD_DEBUG` to verify, not assume.** The dynamic linker's behavior is fully observable; observe it.
5. **Keep your exported symbol surface small.** Every exported symbol is a GOT/PLT/hash-table entry and a potential interposition target.

---

## Edge Cases & Pitfalls

**Pitfall: assuming the GOT/PLT is thread-safe to resolve concurrently.** Lazy resolution in glibc *is* made thread-safe by the loader, but custom or older loaders, and certain `dlopen` patterns, can race. If two threads make the first call simultaneously, the loader must serialize the resolution. Usually handled for you; worth knowing exists.

**Pitfall: lazy binding hides errors until first call.** If a symbol is unresolvable (a missing function in a present library), lazy binding doesn't fail at startup — it fails at the *first call*, possibly deep in production, with `symbol lookup error`. Eager binding (`-z now`) surfaces the same problem at startup, which is often what you want for fail-fast behavior.

**Pitfall: confusing `.got` and `.got.plt`.** Data symbols (`GLOB_DAT`) resolve at load time into `.got`; function jump-slots (`JUMP_SLOT`) resolve lazily via `.got.plt`. Full RELRO makes `.got` read-only after load but, with lazy binding still on, `.got.plt` stays writable — which is why *full* hardening needs `now` too.

**Pitfall: stripping the wrong thing.** You can strip a lot from a binary, but the *dynamic* symbol table (`.dynsym`) and the dynamic section are load-bearing — strip them and the loader can't resolve anything. `strip` knows this and leaves `.dynsym` alone; hand-rolled stripping might not.

**Pitfall: thinking PIE and PIC are the same.** PIC is position-independent *library* code (always required for `.so`). PIE is a position-independent *executable* — the main program itself is built like a shared object so it too can be ASLR'd. Both rely on GOT-style indirection; PIE extends ASLR to the executable's own code, not just its libraries.

**Pitfall: `-no-pie` "fixing" an address-related bug.** If a bug "goes away" when you disable PIE/ASLR, you almost certainly have undefined behavior (an uninitialized pointer, a stale address) that randomization merely *exposes*. The fix is the bug, not the flag.

---

## Apply it

1. Find a real component where **Dynamic Linking & Loading** affects an interface or dependency.
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

- Which boundary is most affected by Dynamic Linking & Loading?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
