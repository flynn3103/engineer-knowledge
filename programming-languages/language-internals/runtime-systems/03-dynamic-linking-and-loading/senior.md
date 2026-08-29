# Dynamic Linking & Loading — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Dynamic Linking & Loading** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Search Order Decides Who Wins

When the loader resolves a normal symbol reference, it searches loaded objects in a defined order and **takes the first definition it finds**. On Linux (ELF, flat namespace) that order is, roughly:

1. **Preloaded objects** (`LD_PRELOAD`), in listed order.
2. **The executable itself.**
3. **The needed libraries**, in breadth-first load order (the order they appear via `DT_NEEDED`, then their dependencies).

"First match wins" is the whole game. Two libraries both define `log`? Whoever is earlier in this order is the `log` everyone gets. This is *not* a link error on Linux — it's silent interposition, and it's the root of a category of surprising bugs.

### 2. Interposition: Deliberately Winning the Search

Because "first match wins," you can *insert* a definition earlier and override the real one. The canonical tool is `LD_PRELOAD`: a `.so` listed there is searched *before everything*, so its symbols win.

The most famous use is replacing `malloc`/`free`. jemalloc and tcmalloc ship as `.so`s you `LD_PRELOAD`; every `malloc` call in the program — including inside libc and third-party libraries — routes to the replacement, with no recompilation. Sanitizers (ASan), leak detectors, and allocation profilers all use the same lever.

A wrapper that *augments* rather than replaces uses `RTLD_NEXT` to reach the original:

```c
// malloc_count.so — counts allocations, then delegates to the real malloc
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>

static unsigned long count = 0;

void *malloc(size_t n) {
    static void *(*real_malloc)(size_t) = NULL;
    if (!real_malloc)                      // resolve the REAL malloc, after us
        real_malloc = dlsym(RTLD_NEXT, "malloc");
    __sync_fetch_and_add(&count, 1);
    return real_malloc(n);
}
```

`dlsym(RTLD_NEXT, "malloc")` means "find `malloc` *after me* in the search order" — i.e. the genuine libc one. This is the standard interposition idiom.

### 3. `RTLD_LOCAL` vs `RTLD_GLOBAL`: Who Can See a Plugin's Symbols

When you `dlopen` a plugin, its symbols default to **`RTLD_LOCAL`**: visible to the plugin and its own dependencies, but *not* added to the process-wide global scope. A *later*-loaded plugin therefore cannot accidentally resolve against the *earlier* plugin's symbols.

`RTLD_GLOBAL` does the opposite: it merges the plugin's symbols into the global scope, where they become visible to — and can interpose on — subsequently loaded objects. This is occasionally necessary (one plugin must expose symbols another plugin needs) but is a frequent source of cross-plugin contamination: two plugins each exporting a `init` or a `version` symbol globally will collide, and the first-loaded wins for everyone.

**Default to `RTLD_LOCAL` for plugins.** Reach for `RTLD_GLOBAL` only with a specific cross-plugin contract in mind, and keep exported surfaces tiny (`-fvisibility=hidden`).

### 4. macOS Two-Level Namespaces: A Different Default

macOS `dyld` (by default) uses a **two-level namespace**: each undefined symbol an object imports records *which library* it expects to find it in (`libSystem`'s `malloc`, specifically). Resolution isn't a flat global search; it's "get `malloc` *from libSystem*." Consequences:

- The same symbol name in two libraries does **not** collide — each importer is bound to a specific provider.
- `LD_PRELOAD`-style interposition doesn't work the same way; macOS uses `DYLD_INSERT_LIBRARIES` plus an interpose table (`__interpose` section) for explicit interposition.
- You can opt into a **flat namespace** (`-flat_namespace` / `DYLD_FORCE_FLAT_NAMESPACE`) to get Linux-like behavior, but it reintroduces collisions.

This is a major portability gotcha: code that relies on flat-namespace interposition on Linux behaves differently on macOS, and vice versa.

### 5. Symbol Versioning and ABI Compatibility

glibc must ship a `memcpy` that behaves the new way for new binaries and the old way for binaries compiled years ago — in *one* `libc.so.6`. It does this with **symbol versioning**: the library defines `memcpy@GLIBC_2.2.5` (old) and `memcpy@@GLIBC_2.14` (new default, note `@@`). A binary compiled today records that it wants `memcpy@GLIBC_2.14`; an old binary recorded `memcpy@GLIBC_2.2.5`. The loader binds each to the version it asked for. Same name, two behaviors, ABI preserved.

This is also the mechanism behind the infamous `version 'GLIBC_2.34' not found` error: you built against a newer glibc and tried to run on an older one that simply doesn't *have* that version of the symbol. The fix is to build against the *oldest* glibc you must support (or static-link, or use `musl`).

`readelf --dyn-syms ./bin` shows the versions a binary requires; `readelf -V` shows version definitions and needs.

### 6. The Diamond / Duplicate-Symbol Problem

A depends on C, B depends on C, your program depends on A and B. With *shared* C, there's **one** copy of C — one set of its globals, one allocator arena, one logging singleton. Good.

But if A and B each *statically* link C (or `dlopen` private copies), there are now **two** copies of C's code and, critically, **two copies of its global state**. Objects allocated by A's copy and freed by B's copy corrupt the heap; a "singleton" exists twice; a registry initialized in one copy is empty in the other. This is the duplicate-symbol / diamond problem, and it's why mixing static and dynamic copies of the same library is dangerous.

On Linux's flat namespace, if both copies export the symbols *globally*, interposition may accidentally "merge" them (first wins) — sometimes masking the bug, sometimes creating a worse one. The disciplined fixes: link C *once* as a shared library that both A and B use; or hide C's symbols (`-fvisibility=hidden`, version scripts) so the two copies can't see each other; or, for plugins, `RTLD_LOCAL` so each keeps its own.

### 7. `dlopen`/`dlsym`/`dlclose`: Runtime Plugins

`dlopen` loads a library *while the program runs*; `dlsym` looks up a symbol by name and returns a pointer you cast and call; `dlclose` unloads. This is how editors load language servers, how databases load extensions, how media players load codecs. The plugin's constructors (`DT_INIT_ARRAY`) run during `dlopen`; its destructors run during the matching `dlclose` (or at exit).

The portable contract is a small, C-linkage **entry point** the host looks up by a known name, returning a vtable of function pointers — never relying on the C++ ABI across the boundary (name mangling and ABI differences make C++ plugin interfaces fragile).

---

## Code Examples

### Interpose `malloc` with `LD_PRELOAD` (count allocations system-wide)

```text
$ gcc -shared -fPIC -D_GNU_SOURCE malloc_count.c -o malloc_count.so -ldl
$ LD_PRELOAD=./malloc_count.so ls            # ls's mallocs now route through ours
# (the wrapper counts and forwards via dlsym(RTLD_NEXT, "malloc"))
```

No recompilation of `ls`; every `malloc` in the process — libc's own included — passes through your code. This is the entire basis of allocator replacement and many profilers.

### A plugin host with `dlopen`/`dlsym`

```c
// plugin API (shared header): host and plugins agree on this
typedef struct { const char *name; int (*run)(int); } Plugin;

// plugin.c
#include "plugin_api.h"
static int run(int x){ return x * 2; }
// Exported entry point the host looks up by name:
Plugin *plugin_entry(void) {
    static Plugin p = { .name = "doubler", .run = run };
    return &p;
}
```

```c
// host.c
#include <dlfcn.h>
#include <stdio.h>
#include "plugin_api.h"
int main(int argc, char **argv) {
    void *h = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);   // local: no global pollution
    if (!h) { fprintf(stderr, "dlopen: %s\n", dlerror()); return 1; }

    Plugin *(*entry)(void) = (Plugin *(*)(void)) dlsym(h, "plugin_entry");
    char *err = dlerror();                                // ALWAYS check via dlerror, not NULL
    if (err) { fprintf(stderr, "dlsym: %s\n", err); return 1; }

    Plugin *p = entry();
    printf("plugin '%s': run(21) = %d\n", p->name, p->run(21));
    dlclose(h);                                          // runs the plugin's destructors
    return 0;
}
```

```text
$ gcc -shared -fPIC plugin.c -o doubler.so
$ gcc host.c -o host -ldl && ./host ./doubler.so
plugin 'doubler': run(21) = 42
```

Note: check `dlsym` errors via `dlerror()`, not a NULL return — a symbol can legitimately resolve to address `NULL`. Default to `RTLD_LOCAL`.

### Observe symbol versions and a version mismatch

```text
$ readelf --dyn-syms /bin/ls | grep -i memcpy
   ... FUNC GLOBAL DEFAULT UND memcpy@GLIBC_2.14 (2)

# The dreaded mismatch when running a new binary on an old system:
$ ./app
./app: /lib/.../libc.so.6: version `GLIBC_2.34' not found (required by ./app)
# -> built against a newer glibc than the target has. Build against the oldest
#    supported glibc, or static-link, or use musl.
```

### Resist interposition for a library's internal calls

```text
# Make libfoo prefer its OWN definitions for internal references,
# so an LD_PRELOAD can't accidentally hijack libfoo's internal helpers:
$ gcc -shared -fPIC -Wl,-Bsymbolic foo.c -o libfoo.so
```

`-Bsymbolic` binds intra-library references to the library's own symbols at link time. Use with care: it *also* prevents legitimate interposition of those symbols.

---

## Coding Patterns

### Pattern 1: Wrapper-with-`RTLD_NEXT` for augmentation

To *observe or modify* a function without replacing it, define your version, resolve the real one via `dlsym(RTLD_NEXT, name)`, and forward. This is the standard, safe interposition shape (cache the resolved pointer in a `static`).

### Pattern 2: C-linkage vtable entry point for plugins

Expose one `extern "C"` function returning a struct of function pointers (and a version field). Never expose a C++ class across the `dlopen` boundary. This isolates the host from the plugin's compiler/ABI and is the only portable contract.

### Pattern 3: `RTLD_LOCAL` + hidden visibility for plugin isolation

`dlopen(..., RTLD_LOCAL)` plus building plugins with `-fvisibility=hidden` and exporting only the entry point keeps each plugin's symbols from colliding with the host's or with other plugins'. Make global visibility a deliberate, documented exception.

### Pattern 4: Build against the oldest supported runtime

To avoid `version not found`, build on (or target via toolchain) the oldest glibc / oldest macOS deployment target you must support. ABI floors are a property of *where you build*, not where you run.

---

## Best Practices

1. **Default plugins to `RTLD_LOCAL`; reach for `RTLD_GLOBAL` only with a contract.** Treat global scope as shared mutable state.
2. **Shrink your exported symbol surface** with `-fvisibility=hidden` and explicit version scripts. Every export is interposable and collidable.
3. **Check `dlsym` via `dlerror()`, not NULL.** And `dlerror()` is one-shot — call it immediately after the `dl*` call.
4. **Never share one C library as two copies.** Link it once as a `.so`; don't statically embed the same library into multiple components that interact.
5. **Treat `LD_PRELOAD` as a privileged input.** Strip it for setuid/privileged processes (the loader does, for security); never trust attacker-controllable preload paths.
6. **Document and test your ABI floor.** Know the minimum glibc/macOS/Windows runtime you support and CI against it.
7. **Cross the plugin boundary in C, with a versioned vtable.** Spare yourself C++ name-mangling and ABI breakage.

---

## Edge Cases & Pitfalls

**Pitfall: silent interposition on Linux.** Two libraries defining `read_config` is *not* an error on Linux — first in search order silently wins, and the loser's callers may end up in the winner's function with mismatched expectations. macOS's two-level namespace would have caught this. Hide internal symbols to avoid it.

**Pitfall: `dlclose` doesn't always unload.** If anything still references the library (another `dlopen` with the same path, a `RTLD_NODELETE` flag, an in-flight callback, a thread running its code), `dlclose` decrements a refcount but does *not* unmap. Calling into a function pointer from a "closed" library that's actually been unloaded is a use-after-unload crash; calling one you *thought* was unloaded but wasn't can leak. Treat unload as best-effort and never call into a plugin after closing it.

**Pitfall: destructor ordering at exit.** `DT_FINI_ARRAY` destructors run in reverse load order, but if a destructor in library A touches state owned by library B that's already been finalized, you crash *during shutdown*. Keep destructors minimal and self-contained; don't reach across libraries on the way down.

**Pitfall: `RTLD_GLOBAL` + duplicate symbol = action at a distance.** Loading plugin B globally can interpose a symbol that plugin A was already using, silently changing A's behavior mid-run. The crash appears in A; the cause is B's load. Local scope prevents this.

**Pitfall: versioned-symbol "downgrade."** A binary that records `memcpy@GLIBC_2.14` will *refuse* to bind to an older libc lacking that version — even if the older `memcpy` would work fine. The version request is a hard floor, not a preference.

**Pitfall: C++ across `dlopen`.** Throwing an exception across a `dlopen` boundary, passing `std::string` between objects built with different standard-library versions, or relying on RTTI across the boundary are all ways to get crashes that depend on compiler flags. Keep the boundary C and POD.

**Pitfall: `LD_PRELOAD` and static linking don't mix.** Interposition works because calls go through the dynamic symbol resolution machinery. A statically linked binary has already resolved its `malloc` internally — `LD_PRELOAD` can't touch it. This is why you can't easily ASan/profile a fully static binary via preload.

---

## Apply it

1. State the system invariant that **Dynamic Linking & Loading** must protect.
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

- Which invariant must remain true when Dynamic Linking & Loading fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
