# Dynamic Linking & Loading — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Dynamic Linking & Loading** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Your Compiler Leaves Holes; the Linker Fills Them

When the compiler turns `main.c` into `main.o`, it cannot know the address of `printf` — `printf` is not in your file. So it emits a *placeholder*: "here is a call to a symbol named `printf`, address to be determined." The object file carries a list of these undefined symbols.

**Linking** is the act of resolving every undefined symbol to a real definition. The question "where does the definition come from, and *when* is the address filled in?" is exactly what splits static from dynamic linking.

You can see the holes with `nm`:

```text
$ nm main.o
                 U printf      <- 'U' means UNDEFINED: we use it, we don't define it
0000000000000000 T main        <- 'T' means defined in the Text (code) section
```

### 2. Static Linking: Copy It All In

With static linking, the **static linker** (`ld`, invoked for you by `gcc`) finds the definition of `printf` inside `libc.a` (a static archive), copies that machine code into your executable, and patches the call to point at it. After linking, your binary contains everything. Run it on any compatible machine and there is nothing more to resolve.

```text
$ gcc -static hello.c -o hello_static
$ ./hello_static          # works with zero external dependencies
$ ldd hello_static
        not a dynamic executable
```

Result: a bigger file (it now contains a copy of every library function you used), but completely self-contained.

### 3. Dynamic Linking: Keep a Shopping List

With dynamic linking (the default on nearly every OS), the static linker does *not* copy `printf` in. Instead it records two things in the executable:

1. **A "needed" list:** the libraries this program requires (e.g. `libc.so.6`).
2. **A relocation list:** the symbols (`printf`, `malloc`, …) the loader must wire up at run time.

The executable is small. But it cannot run by itself — it needs the libraries *and* a helper to wire them in.

```text
$ gcc hello.c -o hello       # dynamic is the default
$ ldd hello
        linux-vdso.so.1 (0x00007ffc...)
        libc.so.6 => /lib/x86_64-linux-gnu/libc.so.6 (0x00007f...)
        /lib64/ld-linux-x86-64.so.2 (0x00007f...)   <- the loader itself
```

### 4. The Dynamic Loader Runs Before `main`

Here is the part that surprises most juniors: **your `main` is not the first thing that runs.** When you exec a dynamically linked program, the kernel notices it has an "interpreter" recorded inside it — the dynamic loader, `ld-linux.so` — and runs *that* first. The loader then:

1. Reads the "needed" list.
2. Finds each library on disk (using a search order — see below).
3. Maps each library into the process's memory.
4. Recursively loads *their* dependencies too.
5. Resolves the symbols — patches the addresses so `printf` points at the real `printf` in the now-loaded libc.
6. Runs library initializers (constructors).
7. *Finally* jumps to your `main`.

All of this happens in milliseconds, invisibly, every single time you run the program. The cost of all this work is the **startup cost** of dynamic linking — usually tiny, but it grows with the number of libraries.

### 5. How the Loader Finds Libraries (Linux, simplified)

When the loader needs `libfoo.so.2`, it searches, roughly in order:

1. Paths baked into the binary (`RPATH` / `RUNPATH` — think "a hint the build recorded").
2. The `LD_LIBRARY_PATH` environment variable (a colon-separated list of directories).
3. The system cache (`/etc/ld.so.cache`, built from `/etc/ld.so.conf` by `ldconfig`).
4. Default system directories (`/lib`, `/usr/lib`, and the multiarch variants).

If it finds the file, great. If not, you get the dreaded `cannot open shared object file: No such file or directory`. The fix is almost always "make the library findable" — install it, or add its directory to the search path.

### 6. Other Platforms, Same Idea

The concept is universal; the names differ:

- **Linux:** shared objects are `.so`; loader is `ld-linux.so` / `ld.so`; tools are `ldd`, `nm`, `objdump`, `readelf`.
- **Windows:** shared libraries are `.dll` (Dynamic-Link Libraries); the OS loader resolves them; tools are `dumpbin`, Dependency Walker / Dependencies. The classic error: "*X.dll was not found*."
- **macOS:** shared libraries are `.dylib`; the loader is `dyld`; the tool is `otool -L`. Frameworks are bundles of `.dylib` + headers + resources.

---

## Code Examples

### See the dependencies of a binary (Linux)

```text
$ ldd /usr/bin/git
        linux-vdso.so.1 (0x00007ffd...)
        libpcre2-8.so.0 => /usr/lib/.../libpcre2-8.so.0 (0x...)
        libz.so.1 => /usr/lib/.../libz.so.1 (0x...)
        libc.so.6 => /usr/lib/.../libc.so.6 (0x...)
        /lib64/ld-linux-x86-64.so.2 (0x...)
```

Each `=>` line is a dependency and where it was resolved. A line that says `=> not found` is a problem waiting to crash.

### Build the same program both ways and compare size

```text
$ gcc hello.c -o hello_dynamic
$ gcc -static hello.c -o hello_static
$ ls -l hello_*
-rwxr-xr-x  hello_dynamic   16312       # tiny: libc lives elsewhere
-rwxr-xr-x  hello_static    872400      # huge: contains a copy of libc
```

The dynamic binary is a few kilobytes; the static one drags in a copy of the C library. That size difference is the most visible trade-off of all.

### Make and use a shared library yourself (Linux)

```c
// greet.c
#include <stdio.h>
void greet(const char *name) {
    printf("Hello, %s!\n", name);
}
```

```c
// main.c
void greet(const char *name);   // declaration only; definition is elsewhere
int main(void) {
    greet("world");
    return 0;
}
```

```text
# Build greet.c into a shared library:
$ gcc -fPIC -shared greet.c -o libgreet.so

# Build main, telling the linker we need libgreet from the current dir:
$ gcc main.c -L. -lgreet -o app

# Run it — but the loader can't find libgreet.so in standard paths:
$ ./app
./app: error while loading shared libraries: libgreet.so: cannot open shared object file

# Tell the loader where to look:
$ LD_LIBRARY_PATH=. ./app
Hello, world!
```

That sequence — *build fine, run fails to find the .so, fix the search path* — is the single most common dynamic-linking experience you will have. Note `-fPIC`: shared libraries must be position-independent (see "PIC" below).

### Diagnose a missing library

```text
$ ldd ./app
        libgreet.so => not found        <- there's your bug
        libc.so.6 => /lib/.../libc.so.6 (0x...)
```

`ldd` told you exactly which dependency the loader cannot find. Fix the path, re-run `ldd`, confirm it now resolves.

### macOS equivalent

```text
$ otool -L /bin/ls
/bin/ls:
        /usr/lib/libutil.dylib (compatibility version 1.0.0, current version 1.0.0)
        /usr/lib/libSystem.B.dylib (...)
```

`otool -L` is macOS's `ldd`. `libSystem` is the macOS equivalent of "the system C library + friends."

---

## Coding Patterns

### Pattern 1: Always run `ldd` (or `otool -L`) on a binary that won't start

Before guessing, *look*. `error while loading shared libraries` → run `ldd` → find the `not found` line → that's the answer. This is a reflex, not a debugging session.

### Pattern 2: Don't ship secret dependencies on `LD_LIBRARY_PATH`

`LD_LIBRARY_PATH=. ./app` is fine for a quick test, but baking it into a launch script is a smell. The right fix is to install the library in a standard place, or to record a proper run-time path in the binary at build time (covered in `senior.md`). Relying on an environment variable is fragile and a known source of security issues.

### Pattern 3: Pick the linking mode deliberately

For a CLI tool you'll distribute widely, consider static (or Go/Rust which make it easy). For a desktop app on a managed OS, dynamic is natural. Don't let it be an accident — know which you're shipping and why. Check with `ldd`/`file`.

---

## Best Practices

1. **Make `ldd`/`otool -L`/`dumpbin /dependents` a habit.** Inspect what your binary actually requires before deploying it.
2. **Install libraries properly instead of fighting `LD_LIBRARY_PATH`.** Use the package manager, or place them in standard directories and run `ldconfig`.
3. **Match library versions to what your binary expects.** A binary built against `libssl.so.3` won't run with only `libssl.so.1.1` present. The version in the dependency name matters.
4. **Prefer static linking for distributable, single-file tools** when the language makes it cheap (Go, and Rust with `musl`).
5. **Keep your build's link step visible.** Read the `-l` flags; know what you're pulling in.
6. **Never copy a single `.dll`/`.so` between machines and hope.** Dependencies are recursive — a library has its own dependencies. Copy the whole set or install properly.

---

## Edge Cases & Pitfalls

**Pitfall: "It compiles and links, so it'll run."** Linking succeeds at *build* time; the loader does its work at *run* time, possibly on a different machine with different libraries. A clean build does not guarantee a clean start. Always test on a representative target.

**Pitfall: Forgetting `-fPIC` when building a shared library.** Shared libraries must be **position-independent** — they can be loaded at any address (different processes, ASLR). On most modern toolchains it's the default for `-shared`, but if you build a `.o` without `-fPIC` and then try to make a `.so` from it, you'll get a relocation error. Fix: recompile with `-fPIC`.

**Pitfall: The version number in the soname.** `libfoo.so`, `libfoo.so.2`, and `libfoo.so.2.3.1` are usually *symlinks* pointing at one real file. The loader matches on the **soname** (`libfoo.so.2`), and the bare `libfoo.so` is typically a build-time-only link. Deleting the "extra" symlinks breaks things — they're load-bearing.

**Pitfall: Missing the loader itself.** On exotic or stripped systems you can get `No such file or directory` when running a *present, executable* binary. The "file" the kernel can't find is the **interpreter** — the dynamic loader recorded inside the binary (e.g. a binary built for `ld-musl` run on a `glibc`-only system). The binary is there; its loader isn't.

**Pitfall: Windows DLL "not found" at the worst time.** A Windows app can launch fine and then crash much later when it first tries to use a missing DLL (delay loading) or a DLL of the wrong architecture (32-bit DLL, 64-bit process). The error mentions a `.dll` you've never heard of — it's a dependency-of-a-dependency. Use a dependency-walker tool to see the full tree.

**Pitfall: Assuming `ldd` is safe on untrusted binaries.** On some systems `ldd` works by *running* the program under the loader, which can execute code. Don't `ldd` a binary you don't trust; use `objdump -p` / `readelf -d` to read its dependencies *without* running it.

---

## Apply it

1. Choose one small, known input for **Dynamic Linking & Loading**.
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

- What problem does Dynamic Linking & Loading solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
