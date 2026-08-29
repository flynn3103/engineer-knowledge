# Name Mangling & Linking — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Name Mangling & Linking** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Itanium mangling grammar, decoded by hand

Every Itanium-mangled name starts with `_Z`. After that, the scheme is a small grammar. Learn these building blocks and you can decode most real symbols:

```text
_Z   <- "this is a mangled C++ name"

Names:
  3foo            <length><identifier>   →  foo  (3 chars)
  N ... E         nested (qualified) name: foo::bar
  St              std::

Type codes (parameters):
  i   int            l   long       x   long long    s   short
  c   char           b   bool       f   float        d   double
  v   void           Pi  pointer to int (P = pointer)
  Ri  reference to int (R = reference)
  Ki  const int      (K = const qualifier)
```

Now decode the canonical example, `_ZN3foo3barEi`:

```text
_Z          mangled C++ name
N           start of nested name
  3foo      "foo"   (3 letters)
  3bar      "bar"   (3 letters)
E           end of nested name  →  foo::bar
i           one parameter: int
                                  →  foo::bar(int)
```

So `_ZN3foo3barEi` = **`foo::bar(int)`**. Verify it:

```text
$ echo _ZN3foo3barEi | c++filt
foo::bar(int)
```

A few more, worked:

```text
_Z3addii            add  + i + i              →  add(int, int)
_ZN5audio7processEv N 5audio 7process E + v    →  audio::process()
_ZNK6Vector4sizeEv  NK 6Vector 4size E + v     →  Vector::size() const   (K after N = const member)
_Z3maxIiET_S0_S0_   max + I i E (template <int>) →  int max<int>(int, int)  (templates get hairy)
```

The pattern: **`N…E` wraps a qualified name; the letters after it are the parameter types; `K`/`R`/`P` are qualifiers and indirection.** You won't decode every template by sight — those get genuinely complex — but plain functions and methods become readable fast.

### 2. Why `const` and references change the symbol

Because the symbol *is* the signature, anything the overload-resolution rules consider part of the signature gets encoded:

- `void f(int)` → `_Z1fi`
- `void f(const int&)` → `_Z1fRKi` (`R` ref, `K` const)
- `void f(int*)` → `_Z1fPi` (`P` pointer)
- A `const` member function gets `K` right after the `N`.

This is *why* changing a parameter from `int` to `long`, or adding `const`, silently produces a *different symbol* — and why a caller compiled against the old header gets `undefined reference` when the definition's signature changed. The symbol mismatch is the signature mismatch, made mechanical.

### 3. Substitutions: the compression you'll see in real output

Real mangled names contain `S_`, `S0_`, `St`, etc. These are **substitutions** — back-references to previously-seen name components, so a long type isn't repeated. `St` is the special abbreviation for `std::`. You don't need to fully decode substitutions to read a symbol (let `c++filt` expand them), but recognize that `S...` is *compression*, not a separate function — it's why `std::string` appears as cryptic `NSt7__cxx1112basic_string...`.

### 4. Static archives are pulled in member-by-member

A `.a` file is just a bundle of `.o` files with an index. When the linker processes an archive, it does **not** include the whole thing. It includes *only the member object files that define a currently-undefined symbol*. This has two big consequences:

- **Link order matters (classic `ld`).** The linker walks the command line left to right. When it reaches an archive, it only pulls members satisfying symbols that are *undefined so far*. So a library must appear *after* the object that needs it: `gcc main.o -lfoo`, not `gcc -lfoo main.o`.
- **Unused members are dropped.** Code in an archive that nothing references doesn't bloat your binary — which is one reason static linking can produce a *smaller* binary than you'd expect.

### 5. Shared objects resolve at load time

A shared object (`.so`/`.dylib`) is different. At *link* time, the linker only checks that the symbol *exists* in the `.so` and records a dependency. The actual binding happens at *load* time (or lazily on first call) by the dynamic loader. Consequences:

- The symbol's code is **not copied** into your executable; it's shared in memory across processes.
- The whole `.so` is loaded if you use *any* symbol from it — there's no member-by-member pull.
- A symbol that exists at link time but is *missing or renamed at runtime* gives a *runtime* error (`symbol not found`), not a link error. This is the source of "compiled fine, crashes on the user's machine with a different library version." (The deep runtime-loading mechanics are a topic of their own; here we just note the link-time vs load-time split.)

### 6. Visibility: not everything should be exported

By default on most Unix toolchains, **every global (non-`static`) symbol in a shared object is exported** into the dynamic symbol table. That is almost always wrong for a real library:

- It **bloats `.dynsym`**, slowing the dynamic loader (more symbols to hash and relocate at load time).
- It **freezes internals into your ABI** — anyone can link against `internal_helper`, so you can't change it without breaking them.
- It risks **symbol collisions** with other libraries that happen to use the same internal name.

The fix is to compile with `-fvisibility=hidden` (everything internal by default) and explicitly mark the public API:

```cpp
#define API __attribute__((visibility("default")))

API int  lib_public_function(void);   // exported
       int internal_helper(void);     // hidden (not exported)
```

Now only `lib_public_function` appears in `.dynsym`. This is the first step toward *designing* an ABI surface rather than leaking one.

### 7. `static` and anonymous namespaces make symbols local

Independently of visibility, `static` at file scope (C and C++) and the **anonymous namespace** (C++) give a symbol *internal linkage* — it's *local* to its object file, invisible to the linker for cross-file resolution:

```cpp
static int helper(int x) { ... }   // C-style internal linkage
namespace { int helper2(int x); }  // C++ anonymous-namespace internal linkage
```

Local symbols (`nm` shows them lowercase: `t`, `d`, `b`) never participate in cross-object resolution and never collide. Use them for everything that doesn't need to be seen outside the file.

---

## Code Examples

### Decoding by hand, then checking

```text
$ echo _ZN3foo3barEi | c++filt
foo::bar(int)

$ echo _ZNK6Vector4sizeEv | c++filt
Vector::size() const

$ echo _Z3addii | c++filt
add(int, int)

$ echo _Z1fRKi | c++filt
f(int const&)
```

Practice: cover the right column, decode the left by hand using the type-code table, then reveal.

### Generating real symbols and inspecting them

```cpp
// lib.cpp
namespace net {
    class Socket {
    public:
        int  send(const char* data, unsigned len);
        void close();
    };
    int  Socket::send(const char* d, unsigned l) { return 0; }
    void Socket::close() {}
}
```

```text
$ g++ -c lib.cpp -o lib.o
$ nm lib.o
0000000000000000 T _ZN3net6Socket4sendEPKcj
0000000000000020 T _ZN3net6Socket5closeEv

$ nm -C lib.o          # -C demangles inline
0000000000000000 T net::Socket::send(char const*, unsigned int)
0000000000000020 T net::Socket::close()
```

Decode `_ZN3net6Socket4sendEPKcj` by hand: `N` `3net` `6Socket` `4send` `E` `PKc` (pointer-to-const-char) `j` (unsigned int) → `net::Socket::send(const char*, unsigned int)`. It matches.

### Archive link order, demonstrated

```text
$ ar rcs libmath.a math.o          # build a static archive

# WRONG order — library before the object that needs it (classic ld):
$ gcc -L. -lmath main.o -o app
main.o: undefined reference to `add'

# RIGHT order — object first, library after:
$ gcc main.o -L. -lmath -o app
$ ./app
5
```

When the linker reached `-lmath` in the wrong-order case, *nothing was undefined yet* (it hadn't seen `main.o`), so it pulled in no members. Then `main.o` introduced an undefined `add` that was never satisfied.

### Visibility: before and after

```cpp
// shared.cpp
int public_api(int x)    { return x * 2; }
int internal_helper(int x){ return x + 1; }
```

```text
# Default: BOTH symbols exported
$ g++ -shared -fPIC shared.cpp -o libshared.so
$ nm -D libshared.so | c++filt
0000000000001119 T internal_helper(int)
0000000000001109 T public_api(int)
```

Now mark only the public API and hide the rest:

```cpp
// shared2.cpp
#define API __attribute__((visibility("default")))
API int public_api(int x)     { return x * 2; }
    int internal_helper(int x){ return x + 1; }
```

```text
$ g++ -shared -fPIC -fvisibility=hidden shared2.cpp -o libshared2.so
$ nm -D libshared2.so | c++filt
0000000000001109 T public_api(int)
# internal_helper is gone from .dynsym — hidden, not exported.
```

The dynamic symbol table shrank to exactly the intended interface.

### Local symbols never collide

```cpp
// a.cpp
static int helper() { return 1; }   // local to a.o
int from_a() { return helper(); }
```

```cpp
// b.cpp
static int helper() { return 2; }   // local to b.o — same name, no clash
int from_b() { return helper(); }
```

```text
$ g++ -c a.cpp b.cpp
$ nm a.o b.o
a.o:
0000000000000000 t _ZL6helperv     ← lowercase 't' = local symbol
0000000000000010 T _Z6from_av
b.o:
0000000000000000 t _ZL6helperv     ← same name, but local: no conflict
0000000000000010 T _Z6from_bv
```

Two `helper`s, no multiple-definition error, because internal linkage keeps each one private to its object file. (Note `_ZL` — the `L` marks internal linkage in the mangling.)

---

## Coding Patterns

### Pattern 1: Decode-then-verify

When you see a mangled symbol in an error, decode the *structure* by eye to understand the shape (function? method? what parameters?), then confirm with `c++filt`. Over time the eye-decode becomes instant for the common cases.

### Pattern 2: Export-macro for the public API

```cpp
#if defined(_WIN32)
#  define API __declspec(dllexport)
#else
#  define API __attribute__((visibility("default")))
#endif

API int  lib_init(void);
API void lib_shutdown(void);
```

A single `API` macro marks every public symbol, compiled with `-fvisibility=hidden`. Everything else is hidden automatically. (The Windows half previews `senior.md`.)

### Pattern 3: Internal linkage by default for file-local helpers

```cpp
namespace {                 // anonymous namespace: internal linkage
    int compute_checksum(...);
    struct ParseState { ... };
}
```

Put every helper that doesn't need cross-file visibility in an anonymous namespace (C++) or mark it `static` (C). Smaller global symbol table, zero collision risk.

### Pattern 4: Libraries after objects on the link line

```text
$(CC) $(OBJECTS) $(LDLIBS) -o $@      # objects first, -l... last
```

Make it a habit in every Makefile/build script: objects and their consumers come first, the `-l` libraries that *satisfy* them come last.

---

## Best Practices

- **Learn the type-code table** (`i l c b f d v`, `P` pointer, `R` ref, `K` const, `N…E` nested). It pays for itself the first time you read a link error without tooling.
- **Always prefer `nm -C` / `nm --demangle`** for inspection, but understand the raw form so the demangled output makes sense.
- **Compile shared libraries with `-fvisibility=hidden`** and explicitly export only the public API. Treat every exported symbol as a permanent promise.
- **Mark file-local helpers `static` or put them in an anonymous namespace.** Smaller symbol tables, no collisions, faster links.
- **Put libraries after the objects that use them** on the link command line.
- **Remember the link-time/load-time gap for shared objects.** A clean link is necessary but not sufficient; test against the actual runtime library versions.
- **Use `readelf --dyn-syms` (or `nm -D`) to audit exactly what your `.so` exports.** Surprises in that list are bugs waiting to bite.

---

## Edge Cases & Pitfalls

- **A signature change makes the symbol change, so a stale object can't link.** If you change `f(int)` to `f(long)` in the definition but a caller still has the old header, you get `undefined reference to f(int)` — the symbols `_Z1fi` and `_Z1fl` differ. Rebuild the caller.
- **Link order with archives.** A library before its consumer pulls in nothing. Objects first, `-l` after.
- **Visibility hides a symbol you needed.** Compile with `-fvisibility=hidden` but forget to mark a public function `default` → callers get `undefined symbol` at load time. Audit `.dynsym` after enabling hidden visibility.
- **`static` in a header.** A `static` function defined in a header gives *each* including translation unit its *own private copy* — usually not what you want, and it bloats the binary. Headers should declare, not define (except `inline`/templates).
- **Substitutions make symbols longer than the source.** `std::string` parameters explode into `NSt7__cxx11...` — don't panic; that's compression artifacts plus the real `std` type name, not a bug.
- **Demangling the wrong scheme.** `c++filt` decodes Itanium by default. Feed it an MSVC-mangled name and it returns garbage or the input unchanged. Know which compiler produced the symbol (that's `senior.md`).
- **`nm` vs `nm -D` confusion.** Plain `nm` reads the *static* symbol table (often stripped in shipping `.so`s); `nm -D` reads the *dynamic* one. If `nm` shows "no symbols," try `nm -D`.

---

## Apply it

1. Find a real component where **Name Mangling & Linking** affects an interface or dependency.
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

- Which boundary is most affected by Name Mangling & Linking?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
