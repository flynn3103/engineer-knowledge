# The Big Picture (Compiler Architecture) — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **The Big Picture (Compiler Architecture)** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A compiler is a pipeline

Picture an assembly line. The program enters as raw text and exits as machine code, getting transformed at each station. The classic stations, in order:

```text
source text
   │  (lexer)
   ▼
tokens
   │  (parser)
   ▼
AST (parse tree)
   │  (semantic analysis: name resolution + type checking)
   ▼
checked AST + symbol table
   │  (IR generation)
   ▼
intermediate representation (IR)
   │  (optimization)
   ▼
optimized IR
   │  (code generation)
   ▼
assembly / machine code
   │  (assembler)
   ▼
object file(s)
   │  (linker)
   ▼
executable
```

Each arrow is a transformation. Each box is a *representation* of your program at a different level of detail. The program never changes meaning — it just changes form, getting lower-level at each step.

### 2. What each stage does, concretely

Take the line `x = a + 2;` and follow it down.

- **Lexer** turns the characters into tokens: `IDENT(x)`, `EQUALS`, `IDENT(a)`, `PLUS`, `NUMBER(2)`, `SEMICOLON`. It throws away spaces and comments. It does *not* understand structure — it just chops the text into words.
- **Parser** assembles those tokens into a tree according to grammar rules: an *assignment* node, whose left side is `x` and whose right side is an *addition* of `a` and `2`. Now we have structure.
- **Semantic analysis** checks meaning: Is `x` declared? Is `a` declared? Is `a` a number, so that `a + 2` makes sense? It records `x` and `a` in the **symbol table** with their types. If `a` were a string, this stage would reject the program.
- **IR generation** lowers the tree into simple, uniform instructions, something like: `t1 = a + 2; x = t1`. The IR looks the same whether the source was C, Rust, or Swift.
- **Optimization** improves the IR. If `a` were known to be `5`, it might fold `5 + 2` into `7`. If `x` were never used, it might delete the whole line.
- **Code generation** turns the IR into real CPU instructions: `mov eax, [a]; add eax, 2; mov [x], eax`.
- **Assembler + linker** turn that into bytes in an executable file.

### 3. The three big stages: front end, middle end, back end

The pipeline is grouped into three parts, and this grouping is the single most important architectural idea in compilers:

| Part | Stages | Depends on | Job |
|------|--------|-----------|-----|
| **Front end** | lexer, parser, semantic analysis | the **source language** | Understand the program. Catch syntax and type errors. Produce IR. |
| **Middle end** | IR optimization | **neither** language nor target | Improve the program. Make it faster/smaller. |
| **Back end** | code generation | the **target CPU/OS** | Emit machine code for a specific machine. |

The front end speaks your language. The back end speaks your CPU. The middle end speaks neither — it works only on the IR, which is the neutral meeting point.

### 4. Why this split saves enormous work: the M × N problem

Suppose you support **M** source languages (C, C++, Rust, Swift…) and **N** target CPUs (x86, ARM, RISC-V, WebAssembly…). If every language compiled directly to every CPU, you would need to write **M × N** separate compilers. Five languages and five CPUs would be twenty-five from-scratch back ends.

Instead, you funnel every language down to **one shared IR**, and translate that one IR to every CPU. Now you write **M** front ends (one per language) and **N** back ends (one per CPU), and they all meet at the IR. That is **M + N** pieces of work, not M × N. Add a new language, you write one front end and get every CPU for free. Add a new CPU, you write one back end and every language gets it for free.

This is the entire thesis of **LLVM**, and the reason Clang (C/C++), Rust, and Swift can all share the same back ends — they all emit **LLVM IR**, and LLVM takes it from there. We come back to this.

### 5. Compiler vs interpreter (and JIT, and transpiler)

These are different *architectures* for running code, and the line is blurrier than it looks:

- A **compiler** translates the whole program ahead of time into machine code, then you run that. (`gcc`, `go build`, `rustc`.)
- An **interpreter** reads your program and executes it directly, statement by statement, with no separate executable. (Classic Python, older Ruby, a calculator REPL.)
- A **JIT (Just-In-Time) compiler** is a hybrid: it starts by interpreting, watches which code runs a lot ("hot"), and compiles *that* to machine code while the program runs. (The JVM, V8 for JavaScript, .NET.)
- A **transpiler** is a compiler whose *target* is another high-level language, not machine code. (TypeScript → JavaScript, Babel, the C++-to-C compilers of the 1980s.)

All four share the same front end ideas (lex, parse, check). They differ in what they do with the result. We treat these in their own topics; here the point is that they are *variations on the same pipeline*.

### 6. Single-pass vs multi-pass

A **pass** is one walk over the program. Early compilers (and some modern ones, like Go's gc and many Pascal compilers) are designed to be fast and do as few passes as possible. A **single-pass** compiler reads the source once and emits code as it goes. This is fast but limiting — you can't optimize something you've already emitted, and you must declare things before you use them (which is why old C required forward declarations).

A **multi-pass** compiler walks the program several times: once to parse, once to resolve names, once or many times to optimize, once to generate code. Multi-pass is slower but far more powerful — each optimization pass can assume the previous one already ran. Almost every serious optimizing compiler today is multi-pass.

### 7. The compiler vs the toolchain (the driver)

When you type `gcc hello.c -o hello`, you think you ran "the compiler." You actually ran a **driver**. `gcc` is a conductor that runs, in order:

1. The **preprocessor** (`cpp`) — handles `#include`, `#define`.
2. The actual **compiler** (`cc1`) — source → assembly.
3. The **assembler** (`as`) — assembly → object file.
4. The **linker** (`ld`) — object files + libraries → executable.

The "compiler" is really just step 2. The **toolchain** is all four working together, and the **driver** is the program that orchestrates them. This distinction matters: a "linker error" is *not* a compiler error — a different tool, at a different stage, failed.

---

## Code Examples

You can *watch* the pipeline happen with command-line flags. None of this requires writing a compiler — just running one and asking it to stop early or dump an intermediate form. Try these yourself.

### See the preprocessor output (the very first step)

```bash
# hello.c with an #include and a #define, after the preprocessor runs:
gcc -E hello.c | tail -20
```

`-E` says "stop after preprocessing." You'll see your file with every `#include` expanded inline and every macro substituted. This is the *input* to the actual compiler stage.

### See the generated assembly (front + middle + back end, stopping before the assembler)

```bash
# Compile to assembly text instead of an object file:
gcc -S hello.c -o hello.s     # GCC
clang -S hello.c -o hello.s   # Clang

cat hello.s
```

`-S` says "stop after code generation, before assembling." `hello.s` is human-readable assembly — the output of the **back end**. This is the moment your program first becomes CPU-specific.

### See the LLVM IR (the famous "narrow waist")

```bash
# Clang can dump LLVM IR — the language-neutral middle representation:
clang -S -emit-llvm hello.c -o hello.ll

cat hello.ll
```

For this tiny C program:

```c
int add(int a, int b) {
    return a + b;
}
```

`clang -S -emit-llvm` produces LLVM IR roughly like:

```llvm
define i32 @add(i32 %a, i32 %b) {
entry:
  %sum = add i32 %a, %b
  ret i32 %sum
}
```

This `.ll` file is the **IR** — the meeting point. Rust and Swift produce IR in this same language. That is why they can share LLVM's back ends.

### Stop the driver at each stage

```bash
gcc -E hello.c -o hello.i     # preprocess only  → hello.i
gcc -S hello.i -o hello.s     # compile only     → hello.s (assembly)
gcc -c hello.s -o hello.o     # assemble only    → hello.o (object file)
gcc    hello.o -o hello       # link only        → hello   (executable)
```

These four commands do, separately, exactly what `gcc hello.c -o hello` does in one shot. Running them by hand is the clearest possible demonstration that `gcc` is a **driver** orchestrating four tools.

### See which tools the driver actually runs

```bash
gcc -v hello.c -o hello
```

`-v` (verbose) prints the real commands `gcc` issues: you'll see `cc1`, `as`, and `collect2`/`ld` invoked one after another. This is the toolchain, exposed.

### Watch a JIT vs an interpreter (no compiler internals needed)

```bash
# Python: an interpreter. No separate executable produced.
python3 hello.py        # runs directly

# Java: compile to bytecode (javac), then a JIT runs it (java).
javac Hello.java        # produces Hello.class — bytecode, not machine code
java Hello              # the JVM interprets, then JIT-compiles hot code
```

`javac` is an **ahead-of-time** compiler that targets **bytecode** (a portable IR), not your CPU. The `java` command runs a virtual machine that interprets the bytecode and **JIT-compiles** the hot parts to machine code at runtime. Two different architectures, side by side.

---

## Coding Patterns

These are patterns for *interacting with* compilers as a junior, not for building one.

### Pattern 1: Bisect the pipeline to locate an error

When a build fails confusingly, stop the driver at each stage to find where it breaks:

```bash
gcc -E file.c > /dev/null   # did preprocessing succeed?
gcc -S file.c               # did the compiler (front+middle+back) succeed?
gcc -c file.c               # did assembly succeed?
gcc    file.o               # did linking succeed?
```

The first command that fails tells you the failing stage.

### Pattern 2: Read the IR/assembly to understand "what did the compiler do?"

```bash
clang -O2 -S -emit-llvm file.c -o -   # IR after optimization, to stdout
gcc   -O2 -S            file.c -o -    # assembly after optimization
```

This is how you answer "did my optimization actually get applied?" — you look at the lowered form, not the source.

### Pattern 3: Separate compile, then link (translation units)

```bash
gcc -c a.c -o a.o    # compile each file independently
gcc -c b.c -o b.o
gcc a.o b.o -o app   # link them together at the end
```

Each `.c` file is a **translation unit**, compiled in isolation. The **linker** resolves references between them at the end. This is why changing one file only recompiles that file (the basis of `make`).

### Pattern 4: Pick the AOT-vs-interpreted tool deliberately

- Long-running server where peak speed matters → AOT (Go, Rust, C++) or JIT (JVM).
- Quick script, glue code, fast iteration → interpreted (Python).
- "Compile once, run anywhere" → bytecode + VM (Java, C#).

---

## Best Practices

- **Name the failing stage before you debug.** "Linker error" and "parser error" call for completely different fixes. The error *category* is half the diagnosis.
- **Use `-S` and `-emit-llvm` to learn.** When you wonder how something compiles, dump the assembly or IR. It is the single best way to build intuition about what the compiler really does.
- **Trust optimization, then verify.** Modern compilers optimize aggressively. Don't hand-optimize source for speed before checking the generated code at `-O2` — the compiler probably already did it.
- **Keep translation units small and independent.** Faster incremental builds, clearer linker errors.
- **Read warnings, not just errors.** Warnings come from semantic analysis catching *suspicious-but-legal* code — they catch real bugs before runtime.
- **Match the architecture to the workload.** Don't reach for a heavy AOT toolchain for a throwaway script, or an interpreter for a hot inner loop.
- **Learn your driver's verbose flag.** `gcc -v` / `clang -v` demystifies the toolchain by showing the real commands.

---

## Edge Cases & Pitfalls

- **"It compiled but won't link."** Compilation (per-file) and linking (combining files) are *different stages*. A missing function body is a *link* error, not a *compile* error. Don't search the compiler stage for a linker problem.
- **"Undefined reference to `foo`."** The compiler trusted that `foo` exists somewhere (you declared it); the linker looked for the actual code and didn't find it. You forgot to link a library or a `.o` file.
- **Confusing the preprocessor with the compiler.** A bad `#include` path fails at preprocessing, *before* the compiler ever sees your real code. The error mentions a header, not your logic.
- **Assuming an interpreter "doesn't compile."** Most modern interpreters (CPython) still *parse* and *compile to bytecode* internally; they just don't write a separate executable. The front-end stages still run.
- **Thinking `javac` produces machine code.** It produces **bytecode** — a portable IR for the JVM. The JVM (with its JIT) produces machine code, later, at runtime.
- **Believing `-O3` is always faster than `-O2`.** More optimization can bloat code, hurt the instruction cache, or expose latent undefined-behavior bugs. "More passes" ≠ "always faster."
- **Forgetting that warnings are real.** Semantic analysis emits warnings for code that is legal but probably wrong (unused variable, implicit conversion). Ignoring them is ignoring free bug reports.
- **Expecting the same binary to run anywhere.** An executable is **target-specific** — built by a back end for one CPU/OS. An x86 Linux binary won't run on an ARM Mac. (Bytecode + a VM is the portable alternative.)

---

## Common Mistakes

1. **Calling every build failure a "compiler error."** Half of them are *linker* errors. Learn to tell them apart from the message.
2. **Not knowing what stage a tool is.** `cpp`, `cc1`, `as`, `ld` are four different tools; `gcc` just runs them in order.
3. **Believing the compiler runs your source as-is.** It transforms your program through several representations; the machine code may look nothing like your source (especially at `-O2`).
4. **Thinking the AST is the source text.** The AST is a *tree* the parser builds; it has thrown away whitespace, comments, and exact formatting.
5. **Assuming "interpreted = no compilation."** Interpreters lex and parse too; many compile to bytecode internally.
6. **Confusing AOT and JIT.** AOT compiles before you run; JIT compiles *while* you run. The JVM and V8 are JIT; `gcc` is AOT.
7. **Ignoring the order of stages.** A type error is caught in semantic analysis, *after* parsing — so if parsing fails, you never even reach the type check. Fix the earlier error first.
8. **Hand-optimizing source the compiler already optimizes.** Check the `-O2` output before twisting your code into knots for speed.

---

## Tricky Points

- **The "compiler" is just one tool in the toolchain.** When you say "the compiler did X," you may actually mean the preprocessor, the assembler, or the linker. Precision here saves debugging time.
- **An interpreter and a compiler share a front end.** Both lex, parse, and often type-check. They diverge only at the back: one emits machine code, the other walks the tree (or bytecode) and *does* the work.
- **The IR is where the magic of reuse lives.** It's easy to skip past "intermediate representation" as jargon. It is the single design choice that makes LLVM, GCC, and the JVM possible. The IR is the product; the front and back ends are adapters.
- **Multi-pass is the norm, but Go is proudly fast and minimal.** Don't assume every compiler is a 30-pass behemoth. Go's compiler prioritizes *compile speed* and keeps its pass count low on purpose. Architecture is a trade-off, not a fixed recipe.
- **Bytecode is an IR you can ship.** Java's `.class` files and Python's `.pyc` files are IR that gets distributed and run later by a VM. "IR" and "the thing you ship" are sometimes the same thing.
- **Cross-compilation is just swapping the back end.** Building for ARM on an x86 laptop sounds exotic; architecturally it's "use the ARM back end instead of the x86 one." The front and middle ends don't change at all.

---

## Apply it

1. Choose one small, known input for **The Big Picture (Compiler Architecture)**.
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

- What problem does The Big Picture (Compiler Architecture) solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
