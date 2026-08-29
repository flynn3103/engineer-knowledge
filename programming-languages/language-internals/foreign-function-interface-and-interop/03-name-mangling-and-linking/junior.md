# Name Mangling & Linking — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Name Mangling & Linking** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A program is built in two phases: compile, then link

When you run `gcc main.c math.c -o app`, two distinct things happen:

```text
  main.c  ──compile──►  main.o   (machine code + symbol list)
  math.c  ──compile──►  math.o   (machine code + symbol list)
                           │
                           ▼
              ──link──►  app    (one executable, all symbols resolved)
```

The **compiler** works on *one file at a time*. It never sees the other files. The **linker** works on *all the object files at once* and is the only stage that can connect a call in `main.o` to a function defined in `math.o`.

This split is why "it compiles but won't link" is a thing. Compiling checks one file's syntax and types. Linking checks that every name you *used* actually *exists* somewhere.

### 2. A symbol is just a name with an address (eventually)

Inside an object file there is a **symbol table**: a list of names. Each name is either:

- **Defined** — "I have the code/data for this; it lives at offset X in my code section."
- **Undefined** — "I use this name but I don't have it; somebody please supply it."

When `main.c` calls `add(2, 3)`, the compiler emits a `call` instruction with a *blank* destination and records an **undefined** symbol `add`. When `math.c` compiles `add`, it records a **defined** symbol `add`. The linker's whole job is matching the blanks to the definitions.

### 3. What the linker actually does

The linker performs three core jobs:

1. **Symbol resolution.** For every undefined symbol, find the one object file or library that defines it. If none defines it → *undefined reference*. If two define it → *multiple definition*.
2. **Relocation.** Once it knows the final address of `add`, it goes back and patches the blank in `main.o`'s `call` instruction to point there.
3. **Section merging.** It concatenates all the code sections, all the data sections, etc., into one layout, then writes the final executable.

That's it. Linking feels mysterious until you see it's just "match names, then patch addresses."

### 4. C does not mangle (much)

In C, a function name maps almost directly to its symbol name. `int add(int, int)` produces the symbol `add`. (On some older platforms a leading underscore is added — `_add` — but that's a platform convention, not encoding of types.)

This works because **C has no function overloading**. You cannot have two functions named `add` in one program. One name, one function, one symbol. The symbol name carries *no type information* because it doesn't need to.

The price: the linker cannot tell if you call `add` with the wrong arguments. If `main.c` thinks `add` takes two `int`s and `math.c` actually defined it to take two `double`s, the symbol `add` matches, the link succeeds, and you get *silent garbage at runtime*. C trades safety for simplicity.

### 5. C++ must mangle

C++ has features C lacks, and every one of them creates a "two things spelled the same" problem the linker can't handle with plain names:

- **Overloading:** `add(int,int)` and `add(double,double)` are different functions, same source name.
- **Namespaces:** `audio::process` and `video::process` are different functions, same source name.
- **Member functions:** `Vector::size()` and `String::size()` are different functions, same source name.
- **Templates:** `max<int>` and `max<double>` are different *instantiations*, same source name.

The compiler resolves all of this by **mangling**: it builds a symbol name that encodes the function's *full identity*. So:

```text
   add(int, int)             →  _Z3addii
   add(double, double)       →  _Z3adddd
   audio::process()          →  _ZN5audio7processEv
   Vector::size() const      →  _ZNK6Vector4sizeEv
```

Now every distinct function gets a distinct symbol, and the linker can keep them apart. You don't have to *read* these yet — `middle.md` decodes the grammar. For now, just internalize: **the ugly name is the compiler encoding the signature into the symbol.**

### 6. `extern "C"` turns mangling off

Because C symbols are simple and stable, C is the **lingua franca of FFI** — every language knows how to call a C function. So when you want a C++ function to be callable from C (or Python, or Rust, or anything), you tell the C++ compiler: *don't mangle this one*:

```cpp
extern "C" int add(int a, int b) {
    return a + b;
}
```

Now the symbol is plain `add`, not `_Z3addii`, and any C-aware tool can find and call it. The cost: an `extern "C"` function *cannot be overloaded* (there's only one symbol name to go around). That's the whole trade — you give up C++ features at the boundary in exchange for a stable, callable name.

### 7. The One Definition Rule (ODR), briefly

Every function and global must be **defined exactly once** across the whole program. Define it twice → *multiple definition* error. Define it zero times but use it → *undefined reference*. This is why putting a non-`inline` function body in a header that's `#include`d by two `.c` files breaks the build: now two object files define the same symbol.

---

## Code Examples

We'll use C and C++ and inspect real symbols with `nm` and `c++filt`. Run these yourself — seeing the actual symbols is the whole lesson.

### The classic two-file C program

```c
/* math.c */
int add(int a, int b) {
    return a + b;
}
```

```c
/* main.c */
#include <stdio.h>
int add(int a, int b);   /* declaration only — no body */

int main(void) {
    printf("%d\n", add(2, 3));
    return 0;
}
```

Compile each to an object file *without linking* and inspect symbols:

```text
$ gcc -c math.c -o math.o
$ gcc -c main.c -o main.o

$ nm math.o
0000000000000000 T add        ← 'T' = defined, in text (code) section

$ nm main.o
                 U add         ← 'U' = undefined (needs it from elsewhere)
                 U printf      ← also undefined; comes from libc
0000000000000000 T main
```

`main.o` has `U add` (it *needs* `add`); `math.o` has `T add` (it *provides* `add`). Linking matches them:

```text
$ gcc main.o math.o -o app
$ ./app
5
```

Note the C symbol is just `add`. No types. That's no-mangling in action.

### The undefined-reference error, on purpose

Link `main.o` *alone* and the linker can't find `add`:

```text
$ gcc main.o -o app
main.o: in function `main':
main.c: undefined reference to `add'
```

Read it literally: *"`main` uses a symbol `add` and nobody supplied it."* The fix is to provide the definition — link `math.o` too. This is the most common beginner link error, and now you can read it.

### C++ mangling, made visible

```cpp
// shapes.cpp
namespace geo {
    double area(double r)        { return 3.14159 * r * r; }
    double area(double w, double h) { return w * h; }   // overload
}
```

```text
$ g++ -c shapes.cpp -o shapes.o
$ nm shapes.o
0000000000000000 T _ZN3geo4areaEd      ← geo::area(double)
0000000000000018 T _ZN3geo4areaEdd     ← geo::area(double, double)
```

Two functions named `area`, two distinct symbols. Notice the single `d` vs double `dd` — that's the parameter list encoded. Now demangle them:

```text
$ nm shapes.o | c++filt
0000000000000000 T geo::area(double)
0000000000000018 T geo::area(double, double)
```

`c++filt` reverses the mangling. The encoding round-trips perfectly because it's a precise scheme, not a hash.

### Making a C++ function callable from C

```cpp
// lib.cpp
extern "C" int add(int a, int b) {   // C linkage: do NOT mangle
    return a + b;
}

int add(int a, int b, int c) {       // normal C++ linkage: WILL mangle
    return a + b + c;
}
```

```text
$ g++ -c lib.cpp -o lib.o
$ nm lib.o
0000000000000000 T add              ← extern "C": plain symbol
000000000000001a T _Z3addiii        ← C++ overload: mangled
```

The `extern "C"` function exposes the plain symbol `add`, which a C program (or any FFI caller) can link against. The C++ overload keeps its mangled name. This is exactly how you build a C-callable wrapper around a C++ library.

### The header pattern that wraps a C++ API for C

```cpp
// engine.h — included by both C and C++ code
#ifdef __cplusplus
extern "C" {
#endif

int engine_start(void);
void engine_stop(void);

#ifdef __cplusplus
}
#endif
```

The `#ifdef __cplusplus` guard means: *when a C++ compiler reads this header, wrap the declarations in `extern "C"` so the symbols stay unmangled; when a C compiler reads it, the guard is invisible and it's plain C.* This is the standard idiom you'll see at the top of nearly every C-facing header in the world (look at any system header).

### Demangling a crash, in practice

When a C++ program crashes, the stack trace often shows mangled names:

```text
#3  0x0000abcd in _ZN6Parser5parseERKNSt7__cxx1112basic_stringIcEE
```

Pipe it through `c++filt` and it becomes readable:

```text
$ echo '_ZN6Parser5parseERKNSt7__cxx1112basic_stringIcEE' | c++filt
Parser::parse(std::__cxx11::basic_string<char> const&)
```

Suddenly the crash is in `Parser::parse(const std::string&)`. Many debuggers demangle automatically, but when you're staring at a raw log, `c++filt` is the tool.

---

## Coding Patterns

### Pattern 1: Guard C-facing headers with `extern "C"`

```cpp
#ifdef __cplusplus
extern "C" {
#endif
    /* declarations usable from both C and C++ */
#ifdef __cplusplus
}
#endif
```

The one idiom to memorize. It makes a header safe to include from either language and keeps the symbols unmangled.

### Pattern 2: Inspect before you guess

When a link error appears, don't randomly add flags. Look:

```text
$ nm yourfile.o | c++filt | grep theFunction
```

If the symbol shows `U` (undefined) you forgot to link its definition. If you expected `extern "C"` and see a mangled name, your guard didn't apply.

### Pattern 3: Prefix C symbols to avoid collisions

Because C has no namespaces, give every public C function a library prefix:

```c
int  png_read_header(...);
void png_destroy(...);
```

Not `read_header` / `destroy` — those will collide with someone else's symbols at link time.

### Pattern 4: Declare in a header, define in exactly one `.c`

```c
/* widget.h */ int widget_count(void);          /* declaration */
/* widget.c */ int widget_count(void) { ... }   /* the single definition */
```

The header *declares* (creates an undefined reference wherever included); one `.c` *defines* (satisfies it). One definition, ODR happy.

---

## Best Practices

- **Read the linker error literally.** "undefined reference to `X`" means *nobody defined `X`* — find or link `X`'s definition. "multiple definition of `X`" means *two files defined it* — make one of them `static`, `inline`, or remove the duplicate.
- **Use `nm` as your first move on any symbol problem.** `nm file.o` shows defined (`T`/`D`) vs undefined (`U`) symbols. It answers "is it there?" instantly.
- **Always demangle C++ symbols.** Pipe through `c++filt` or use `nm -C` / `nm --demangle`. Reading raw mangled names by hand is for `middle.md`, not for debugging.
- **Guard every header that C might include** with the `extern "C"` / `__cplusplus` idiom.
- **Never put a non-`inline` function body in a header.** It causes multiple-definition errors when the header is included by more than one `.c`. Bodies go in `.c`/`.cpp`; only declarations (and `inline`/templates) go in headers.
- **Prefix your public C symbols** with a library name to avoid global namespace collisions.
- **Link the libraries that define your undefined symbols, in the right order** (with classic `ld`, libraries that *provide* a symbol must come *after* the object that *needs* it on the command line).

---

## Edge Cases & Pitfalls

- **Forgetting `extern "C"` when calling C++ from C.** The C side looks for `add`; the C++ side defined `_Z3addii`. Symbols don't match → `undefined reference to add`. Add `extern "C"` on the C++ definition.
- **Forgetting the `extern "C"` guard in a header.** A C++ caller mangles the declaration, the C library defines the plain name, they don't match. The guard fixes it.
- **Putting a function body in a header.** Two `.c` files include it → two definitions of the same symbol → multiple-definition error. Use a declaration in the header, definition in one `.c`.
- **Mismatched declaration and definition in C.** Because C doesn't encode types in the symbol, declaring `int add(int,int)` while the real `add` takes `double`s *links fine* and corrupts at runtime. The symbol matched; the types didn't. This is the dark side of no-mangling.
- **Library order on the link line (classic `ld`).** `gcc -lmath main.o` can fail where `gcc main.o -lmath` succeeds, because the old linker only pulls symbols a library needs *as of the point it appears*. Put libraries after the objects that use them.
- **Assuming `nm` shows everything.** Stripped binaries and some dynamic symbols won't show with plain `nm`; you may need `nm -D` for dynamic symbols. (More in `professional.md`.)
- **Confusing "compiles" with "links."** A missing definition is a *link* error, not a *compile* error. If the message mentions `undefined reference`, look at linking and symbols, not at your syntax.

---

## Apply it

1. Choose one small, known input for **Name Mangling & Linking**.
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

- What problem does Name Mangling & Linking solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
