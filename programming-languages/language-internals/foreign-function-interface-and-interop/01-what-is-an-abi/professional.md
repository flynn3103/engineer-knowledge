# What Is an ABI — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **What Is an ABI** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### ABI Stability as a Production Contract

The headline use case for ABI stability: **upgrade a `.so` without recompiling its callers.** This is the entire reason shared libraries exist as a distribution mechanism. When a distro ships a security fix for `libssl.so.3`, it replaces one file on disk and every program linked against `libssl.so.3` — thousands of them, none of which the distro can recompile — picks up the fix on next launch. If that replacement preserves the ABI, the upgrade is invisible. If it does not, the system bricks.

For this to work, the new library must satisfy three guarantees toward existing callers:

1. **Every symbol the old library exported, the new one still exports**, with the same signature semantics (same calling convention, same argument layout, same return convention). Removing or changing a symbol an installed binary depends on is a break.
2. **Every public type's layout is unchanged** — struct sizes, field offsets, alignment, vtable layout, enum underlying types. An installed binary baked the offset of `cfg->timeout` into its machine code; if the new library moved that field, the old binary reads the wrong bytes.
3. **Behavioral contracts hold** — a function that returned an owned pointer still returns an owned pointer; error codes keep their meaning; a callback is still invoked under the same locking assumptions.

The professional posture is to treat the set of exported symbols and the layout of every public type as a **frozen surface**, and to do *all* evolution either underneath that surface (changing implementation, never layout) or by *adding* to it (new symbols, new functions) — never by mutating it. This is the "frozen core, versioned skin" model: the connections never move; the interior renovates freely.

The hardest part is that none of this is checked by the compiler. A struct layout change compiles cleanly on both sides. The break only appears when an *old* binary meets a *new* library at runtime — which is exactly the configuration your CI never tests, because CI rebuilds everything from source every time. Production does not rebuild from source. That asymmetry is the source of nearly every ABI incident.

### ABI Break vs API Break

These are independent axes, and conflating them is the single most common conceptual error at this level.

- **API (Application *Programming* Interface)** is the source-level contract: function names, signatures, types as the compiler sees them. An **API break** means existing *source code* no longer compiles or compiles with different meaning. Caught at build time, by the consumer's compiler, with a clear error.
- **ABI (Application *Binary* Interface)** is the binary-level contract: symbol names, calling convention, struct layout, vtable layout. An **ABI break** means existing *compiled binaries* no longer link or run correctly against the new build. Caught — if you are lucky — by the loader; if you are unlucky, by a crash deep in unrelated code; if you are very unlucky, by silent data corruption.

The four-quadrant truth table is what you must internalize:

| Change | API break? | ABI break? | Example |
|--------|-----------|-----------|---------|
| Rename a public function | Yes | Yes | `init()` → `initialize()` |
| Add a parameter with a default | Yes (source recompile needed) | Yes (mangled name / arg layout changes) | `f(int)` → `f(int, int = 0)` in C++ |
| Add a field to the **end** of an opaque struct | No | No (callers never see the layout) | grow a handle the caller only holds by pointer |
| Add a field to a struct callers allocate by value | No | **Yes** | `struct Config` grows; old callers allocate the old size |
| Add a non-virtual method to a C++ class | No | No | does not touch layout or vtable |
| Add a **virtual** method | No | **Yes** | shifts every later vtable slot |
| Change `int` return to `int64_t` | Yes | Yes | return register/width changes |
| Reorder struct fields | No (source still compiles) | **Yes** | offsets baked into old binaries are now wrong |
| Change function *body* only | No | No | the entire point of shared libraries |

The dangerous quadrant is **"ABI break without API break"** — reorder a struct, add a field consumers allocate by value, insert a virtual function. The consumer's code compiles without a single warning, links if they rebuild, and corrupts memory if they do *not* rebuild and instead drop in the new library against their old binary. There is no compiler on earth that will warn the end user. This is why the professional discipline is structural: opaque handles so consumers never learn a layout, `extern "C"` so signatures are stable, and `abidiff` in CI so *you* learn about the break before your customers do.

### The libstdc++ Dual-ABI std::string Saga

This is the canonical industrial ABI break, and you should be able to recount it from memory because variants of it land on senior engineers' desks constantly.

C++11 imposed two requirements that the existing `std::string` could not satisfy: it banned copy-on-write strings (a thread-safety hazard) and it required `std::list::size()` to be O(1) (the old implementation walked the list). Both demanded a **change to the in-memory layout** of standard-library types. But libstdc++ could not simply change `std::string`'s layout: every C++ binary in existence that passed a `std::string` across a shared-library boundary baked in the old layout. Flipping it would have been an industry-wide flag day — every binary recompiled simultaneously or corruption everywhere.

GCC's solution was the **dual ABI**: ship *both* layouts in the same `libstdc++.so`, under different mangled names, and select between them at compile time with the macro `_GLIBCXX_USE_CXX11_ABI`.

- `_GLIBCXX_USE_CXX11_ABI=1` (the modern default) gives you the C++11-conformant string, which lives in an inline namespace and mangles as `std::__cxx11::basic_string<...>`.
- `_GLIBCXX_USE_CXX11_ABI=0` (legacy) gives you the old layout, mangling as plain `std::basic_string<...>`.

Because the two strings have *different mangled names*, the linker treats them as different types. That is the mechanism — and the footgun. The classic symptom is a link error that reads like a riddle:

```text
undefined reference to `foo(std::__cxx11::basic_string<char, ...>)'
```

What it actually means: one translation unit was compiled with the new ABI and emitted a call to `foo` taking a `std::__cxx11::string`, while the object file defining `foo` was compiled with the old ABI and exported `foo` taking a plain `std::string`. Same source, same header, different macro value, irreconcilable symbols. The fix is invariably "compile *everything* in the program — every object, every static library, every third-party prebuilt — with the same `_GLIBCXX_USE_CXX11_ABI` value." When you depend on a prebuilt binary blob (a vendor SDK, a proprietary `.a`) compiled against the *other* ABI, you are stuck: you must match its setting or get a new build from the vendor.

The lesson the saga teaches, beyond the macro: **never expose standard-library types across a binary boundary you do not control.** A `std::string` parameter in a public API is a promise that both sides agree, byte for byte, what a `std::string` is — and that agreement is exactly what compiler upgrades and the dual ABI broke.

### glibc Symbol Versioning in Production

How does glibc fix or change the behavior of `memcpy`, `realpath`, or `pow` across two decades without breaking the billions of binaries already linked against it? **Symbol versioning** — an ELF feature that lets a single shared object export *multiple versioned definitions of the same symbol name*.

```text
memcpy@GLIBC_2.2.5      # the old definition, frozen for old binaries
memcpy@@GLIBC_2.14      # the new default (@@ marks the default version)
```

When you link a binary today, the linker records that it needs `memcpy@@GLIBC_2.14` and stamps that requirement into the binary. A binary linked in 2009 recorded a need for `memcpy@GLIBC_2.2.5`. At load time, the dynamic loader binds each binary to the *exact versioned symbol it recorded*, so both run against the implementation they were built for — out of one `libc.so.6` file. This is how glibc maintains backward compatibility forever while still improving and fixing functions.

The practical consequences a professional manages:

- **Binaries built on a newer distro often will not run on an older one**, because they recorded dependencies on symbol versions (`GLIBC_2.34`, etc.) that the old system's libc does not provide. The runtime error is `version 'GLIBC_2.34' not found`. This is *why* release engineering builds shippable Linux binaries on the *oldest* glibc they intend to support — you can run against a newer libc, but not an older one.
- You inspect what a binary requires with `readelf -V yourbinary` (the `.gnu.version_r` requirements section) and what a library *provides* with `readelf -V libfoo.so` (the `.gnu.version_d` definitions). The mismatch between "requires" and "provides" is exactly the diagnosis for a `version not found` failure.
- The famous 2011 `memcpy` regression — new glibc's `memcpy` copied in a different direction and broke programs (including Flash Player) that illegally passed *overlapping* buffers to `memcpy` instead of `memmove` — was navigated partly through this machinery, with a versioned `memcpy@GLIBC_2.14` and a compatibility symbol so old binaries kept the forgiving behavior.

Symbol versioning is also a tool you can wield in your *own* libraries via a linker version script, letting you ship a fixed-behavior `myfunc@@MYLIB_2.0` while keeping `myfunc@MYLIB_1.0` alive for installed binaries. It is the most powerful in-place-evolution tool ELF gives you, and the most underused.

### LP64 vs LLP64: long Is 32-Bit on Win64

A data model defines the size of the C integer types on a platform, and the 64-bit world split into two incompatible camps:

| Type | LP64 (Linux, macOS, BSD, most Unix) | LLP64 (Windows 64-bit) |
|------|-------------------------------------|------------------------|
| `int` | 32 | 32 |
| `long` | **64** | **32** |
| `long long` | 64 | 64 |
| pointer | 64 | 64 |

The names encode it: **LP64** = **L**ong and **P**ointer are 64-bit; **LLP64** = **L**ong **L**ong and **P**ointer are 64-bit (but plain `long` stays 32). The single most consequential difference: **on 64-bit Windows, `long` is 32 bits**, while on every 64-bit Unix it is 64 bits.

This bites in exactly the places you would expect a cross-platform binary or interface to bite:

- A struct shared between platforms with a `long` field has a *different size and field layout* on Windows versus Linux. A serialization format or shared-memory layout that uses `long` is silently non-portable.
- Code that assumed `sizeof(long) == sizeof(void*)` — a safe bet on LP64 — truncates pointers stored in `long` on Win64. This was a widespread porting bug when 64-bit Windows arrived; the canonical fix is `intptr_t`/`uintptr_t`, which are pointer-sized on *both* models.
- A function `f(long)` in a cross-platform FFI passes a 32-bit value on Windows and a 64-bit value on Unix — different register/stack footprint, an ABI mismatch waiting to corrupt.

The professional rule: **never put a bare `long` in any interface that crosses a platform boundary.** Use the fixed-width types from `<stdint.h>` — `int32_t`, `int64_t` — which mean the same thing everywhere, and `intptr_t`/`size_t` for pointer- and size-shaped quantities. The data model is part of the platform ABI; `long` is the trap door between the two models.

### Shipping a Stable Plugin ABI by Flattening to C

When you ship an SDK that third parties build plugins against — and those plugins are compiled by *their* toolchain, on *their* compiler version, possibly in a *different language* — you have no control over the binary on the other side of the boundary. The only contract you can rely on is the one every compiler on the platform honors identically: **the C ABI.** So you flatten your interface to C.

A production plugin ABI is a versioned struct of C function pointers — a hand-rolled vtable — plus opaque handles for all state:

```c
/* plugin_abi.h — the entire contract, frozen */
#define PLUGIN_ABI_VERSION 3

typedef struct PluginContext PluginContext;   /* opaque: caller never sees fields */

typedef struct {
    int32_t abi_version;                       /* host checks this FIRST */
    PluginContext* (*create)(const char* config);
    int32_t        (*process)(PluginContext*, const uint8_t* in, size_t len);
    void           (*destroy)(PluginContext*);
} PluginVTable;

/* The one symbol the host resolves with dlsym. Plain C name, no mangling. */
const PluginVTable* plugin_entry(void);
```

The discipline this encodes:

- **Opaque handles everywhere.** The plugin and host exchange `PluginContext*` and never agree on its layout, so the host can grow its internal struct in any future version without an ABI break — the plugin only ever holds a pointer.
- **Only C primitives and fixed-width integers cross the line.** No `std::string`, no `std::vector`, no exceptions, no C++ classes by value. Every rich type is marshaled to bytes plus length.
- **A version field checked before anything else.** The host reads `abi_version` and *refuses* a plugin it does not understand, turning a future ABI break into a clean rejection message instead of a crash.
- **Never throw across the boundary.** A C++ exception unwinding through a C frame, or into a foreign-compiler frame, is undefined behavior. The implementation catches everything at the seam and returns an error code.

Inside, the plugin and host can be as rich C++ as they like. The *seam* is C, because C is the only thing both compilers agree on. Every successful cross-compiler, cross-language, long-lived plugin system — from VST audio plugins to browser extensions' native components — is built this way.

### C++ Has No Stable ABI Across Compilers

This is the hard constraint behind the previous section, and it is permanent. **There is no single C++ ABI that all compilers agree on**, so a C++ library built by one compiler will not reliably interoperate with code built by another. The incompatibility is not one problem but a stack of independent ones:

- **Name mangling differs.** The Itanium C++ ABI (used by GCC and Clang on Linux/macOS) mangles `int foo(int)` as `_Z3fooi`; MSVC mangles it as `?foo@@YAHH@Z`. The symbol one exports is invisible to the other.
- **Vtable layout differs.** Where the vtable pointer sits in the object, the slot order of virtual functions, the placement of RTTI/typeinfo, and how multiple/virtual inheritance arranges sub-vtables all differ between Itanium and MSVC. Calling a virtual through a mismatched layout dispatches to the wrong slot.
- **Exception handling differs.** Itanium uses table-driven DWARF unwinding (`__cxa_throw`, `.eh_frame`); MSVC uses an SEH-based model. An exception thrown in one cannot be caught in the other.
- **Standard-library type layout differs** — across libstdc++, libc++, and the MSVC STL, a `std::string` or `std::vector` has different internal layout, even before the dual-ABI complication.

The "Itanium ABI" name is a historical accident — it was specified for the long-dead Itanium architecture and then adopted as the de-facto cross-Unix C++ ABI. The salient fact is that the Unix world (GCC, Clang) standardized on *it*, while the Windows world (MSVC) standardized on something entirely different and undocumented for years. The two families agree on *none* of the four points above. Even within one family, a compiler *upgrade* can change library-internal ABI details — which is why GCC and Clang publish a target C++ ABI version and try to keep it stable, but only try.

The practical takeaway is brutally simple: **assume the C++ ABI holds only within a single toolchain you fully control.** Across compilers, across compiler major versions you do not pin, across languages — assume only the C ABI holds. This is not pessimism; it is the documented reality, and it is *why* `extern "C"` exists and why every interop boundary in the industry is a C boundary.

### Versioning Discipline

Operationalizing all of the above is a matter of disciplined versioning, and the rules are mechanical.

**Soname encodes ABI compatibility.** An ELF library carries a *soname* — `libfoo.so.1` — baked into the binary. The convention, enforced by the loader: the *major* number changes when and only when the ABI breaks. A binary linked against `libfoo.so.1` will load any `libfoo.so.1.x.y` (a compatible point release) but the loader refuses `libfoo.so.2`. This is the mechanism that turns "ABI break = incompatible" into "the loader physically won't pair them." Bumping the soname when nothing broke forces needless mass rebuilds; *failing* to bump it when the ABI did break causes silent corruption in the field. Both are serious bugs in the build, not just the code.

**SemVer maps onto this if you let it.** A clean policy: MAJOR = ABI break (soname bump, recompile required), MINOR = additive (new symbols, fully backward-compatible), PATCH = implementation-only (bug fix, behavior preserved). The discipline is to *map your version numbers to actual binary compatibility*, not to marketing.

**`abidiff` removes the guesswork.** Eyeballing a header diff to decide "did I break the ABI" is error-prone — the dangerous changes (a reordered field, an inserted virtual) look innocuous. `abidiff` (from libabigail) mechanically compares two builds of a library and reports exactly which symbols and which type layouts changed. Empty output means ABI-compatible; you can ship without a soname bump. Run it in CI against the last released build, and gate the merge: if `abidiff` reports a change and the soname did not bump, fail the build. This single CI gate prevents the entire category of "we shipped an ABI break in a point release" incident.

**Reserve growth room.** When you must expose a struct by value, add reserved padding fields up front (`uint8_t _reserved[16];`), and a `size` field the caller fills in so the library can detect which version it was handed. This lets you grow the struct later by consuming reserved space without changing its size — controlled evolution baked into the layout from day one.

### Compiled but Crashes: ABI Mismatch in the Field

The signature ABI incident has a recognizable shape, and the professional learns to pattern-match it instantly: **it compiled cleanly, it links, it crashes at runtime — usually far from the real cause.** The compiler validated the *source* contract (the API) and never had the chance to validate the *binary* contract (the ABI), because the two halves were compiled at different times, by different toolchains, or against different versions of a header.

The diagnostic mental model: a crash with these properties is ABI-mismatch until proven otherwise —

- It appears only after upgrading *one* component (a library, the compiler, a vendor SDK) and not rebuilding the others.
- The crash site is nonsensical — a null deref reading a field that "can't be null," garbage in a string, a vtable call jumping into hyperspace.
- It is configuration-dependent: works on the dev box (everything rebuilt from one source tree), crashes on the customer's box (mixed binaries).
- A full clean rebuild of *everything* makes it vanish — which is both the fix and the confirmation of the diagnosis.

The mechanisms behind it are the ones above: a struct whose layout diverged between the header used to compile the caller and the header used to compile the library (the caller writes field `B`, the library reads where `B` *used to be*); a `std::string` passed across a dual-ABI boundary; a virtual function inserted into a base class so every later slot shifted; a `long` that is 32 bits on one side and 64 on the other. None of these are compiler-detectable, all of them produce "compiled but crashes," and every one of them is prevented by the same disciplines — opaque handles, `extern "C"` seams, fixed-width types, soname-and-`abidiff` gating.

The reason this category is so dangerous is that the crash's *symptom* and its *cause* are decoupled in both space and time. The cause was a layout change three releases ago; the symptom is a crash in a customer's logging callback today. The professional skill is to stop debugging the symptom and start asking "what binary met what other binary at runtime, and did they actually agree on the contract."

---

## Code Examples

### See an ABI-vs-API break in a struct layout

```c
/* v1 header the CALLER was compiled against */
typedef struct { int id; int flags; } Widget;

/* v2 header the LIBRARY was compiled against — a field inserted in the middle */
typedef struct { int id; int generation; int flags; } Widget;
```

The caller, compiled against v1, writes `w.flags` at offset 4. The library, compiled against v2, reads `flags` at offset 8 and reads `generation` at offset 4. No compile error on either side. The caller's `flags` lands in the library's `generation`; the library reads garbage as `flags`. This is an ABI break with no API break — and exactly the "compiled but crashes" shape. Appending the field at the *end* (and only ever appending) would have kept old callers' offsets valid.

### Watch the C++ symbol differ from its C twin

```cpp
int  cpp_add(int a, int b)         { return a + b; }   // mangled, compiler-specific
extern "C" int c_add(int a, int b) { return a + b; }   // plain, universal
```

```bash
g++ -c add.cpp -o add.o
nm add.o | grep add
#   _Z7cpp_addii    <- Itanium mangling; MSVC would emit ?cpp_add@@YAHHH@Z
#   c_add           <- the same name under every compiler on the platform
```

`c_add` is the only one another compiler — or `dlsym("c_add")` — can reliably find. That two-line difference is the entire reason interop boundaries are C.

### Reproduce the dual-ABI link error on purpose

```bash
g++ -D_GLIBCXX_USE_CXX11_ABI=1 -c provider.cpp   # exports foo(std::__cxx11::string)
g++ -D_GLIBCXX_USE_CXX11_ABI=0 -c consumer.cpp   # calls   foo(std::string)
g++ provider.o consumer.o -o app
#   undefined reference to `foo(std::__cxx11::basic_string<...>)'
```

Recompiling both translation units with the *same* macro value resolves it. In the field, the "other side" is often a prebuilt vendor blob you cannot recompile — then you must match *its* setting.

### Read symbol versions and the data model

```bash
# What versioned glibc symbols does this binary REQUIRE?
readelf -V ./app | sed -n '/Version needs/,/^$/p'

# What versioned symbols does the library PROVIDE?
readelf -V /lib/x86_64-linux-gnu/libc.so.6 | grep -A1 'memcpy'
#   memcpy@@GLIBC_2.14 and memcpy@GLIBC_2.2.5 coexist in one file

# Confirm the data model: prints 8 on LP64 (Linux), 4 on LLP64 (Win64)
echo 'int main(){return sizeof(long);}' | cc -x c - -o /tmp/l && /tmp/l; echo $?
```

### Gate ABI breaks in CI

```bash
# Compare the just-built library against the last released one.
abidiff libfoo.so.1.released  libfoo.so.1.candidate
# Empty output  => ABI-compatible: safe to ship as a point release.
# Non-empty     => ABI changed: REQUIRES a soname major bump, or fail the build.
```

Wiring this into the merge gate is the difference between learning about a break from `abidiff` and learning about it from a customer.

---

## Best Practices

- **Treat the exported-symbol set and every public type's layout as a frozen surface.** Evolve underneath it (implementation) or by adding to it (new symbols) — never by mutating layout or signatures.
- **Expose only an `extern "C"` ABI across any boundary you do not fully control** — different compiler, different language, long support window. It is the only universally honored contract.
- **Use opaque handles for any state you might ever grow.** Once a struct's fields are public and allocated by value by callers, its layout is frozen forever.
- **Never put a bare `long` in a cross-platform interface.** Use `int32_t`/`int64_t` and `intptr_t`/`size_t`. `long` is 32-bit on Win64 (LLP64) and 64-bit on Unix (LP64).
- **Never pass standard-library types across a binary boundary** (`std::string`, `std::vector`). Marshal to bytes-plus-length. The dual-ABI saga is the cost of forgetting this.
- **Pin `_GLIBCXX_USE_CXX11_ABI` (and equivalents) project-wide** and document it; one value for every object, static lib, and prebuilt dependency.
- **Bump the soname major version on every ABI break, and never on a compatible change.** Run `abidiff` in CI against the last release to know mechanically which it is, and gate the merge on it.
- **Catch all exceptions at every C boundary** and convert to error codes; never let a C++ exception unwind across a C or foreign-compiler frame.
- **Build shippable Linux binaries on the oldest glibc you support**, so recorded symbol-version requirements stay satisfiable downlevel.
- **Reserve struct padding and a `size` field up front** when a by-value struct is unavoidable, so it can grow later without a layout break.

---

## Edge Cases & Pitfalls

- **Inserting a field in the middle of a public struct** is an invisible ABI break — old callers' field offsets are now wrong. Only ever *append*, and only to structs callers hold by pointer or that carry a `size` field.
- **Adding a virtual function to a base class** shifts every later vtable slot — an ABI break with no API break. Adding a *non-virtual* method does not.
- **Changing an `enum`'s underlying type, or a default argument value**, is part of the C++ ABI surface; it can break binary compatibility while source still compiles.
- **`version 'GLIBC_2.34' not found` at startup** means the binary was built on a newer glibc than the target system provides — a symbol-versioning mismatch, fixed by building on the oldest supported glibc, not by the customer.
- **Mixing libstdc++ and libc++ in one process** is generally undefined: two incompatible STL implementations means two incompatible `std::string` layouts at the boundary.
- **`long double` differs across ABIs** — 80-bit on x86 System V, 64-bit on Windows and some AArch64 — never put it in a cross-ABI interface.
- **Static linking does not fully escape the C++ ABI problem**: two `.a` archives built with different ABIs still produce ODR violations at link or run time.
- **Relying on a vendor's prebuilt C++ blob** ties you to *its* compiler, *its* STL, and *its* `_GLIBCXX_USE_CXX11_ABI` setting; demand a C interface or a matching build.
- **A `size`-field versioning scheme that the library forgets to check** is no protection at all — the check must actually branch on the value.

---

## Apply it

1. Define the user or business outcome that **What Is an ABI** should improve.
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

- Which measurable outcome justifies investing in What Is an ABI?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
