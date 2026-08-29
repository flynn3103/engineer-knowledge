# The Big Picture (Compiler Architecture) — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **The Big Picture (Compiler Architecture)** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Phases vs passes: the conceptual and the concrete

A **phase** is a *responsibility* (lexing, parsing, type-checking). A **pass** is a *traversal* — one walk over the data structure. The mapping is not one-to-one:

- The lexer is usually one pass, on demand (the parser pulls tokens as it needs them).
- Parsing is typically one pass.
- Semantic analysis is often *several* passes: one to collect all top-level declarations (so functions can call each other regardless of order), then one to resolve names and check types.
- Optimization is *many* passes — constant folding, then dead-code elimination, then inlining, then constant folding again because inlining exposed new constants.

This is the line between a **single-pass** and **multi-pass** compiler. Single-pass compilers (classic Pascal, Go's front end is famously fast) fuse phases to read the source once. The cost is power: you can't optimize across the whole program if you've already emitted code for the first half of it. Multi-pass trades compile time for the ability to see the whole program before committing.

### 2. Each phase establishes an invariant for the next

The pipeline works because each phase *guarantees something* its successor can rely on:

| After this phase... | ...the next phase can assume: |
|---------------------|-------------------------------|
| Lexing | The input is a clean stream of tokens; no stray characters, comments stripped. |
| Parsing | The token stream was grammatically valid; we have a well-formed tree. |
| Name resolution | Every identifier points at a real declaration; no "undeclared variable" remains. |
| Type checking | Every operation is type-correct; no "can't add a string to an int" remains. |
| IR generation | The program is in a uniform, simple form; high-level sugar (for-loops, ternaries) is desugared into primitives. |
| Optimization | The IR is semantically equivalent but improved; the back end need not re-optimize. |

This is why **order matters and is not arbitrary**: you cannot type-check a name you haven't resolved; you cannot resolve a name in a tree you haven't built; you cannot build a tree from tokens you haven't lexed. Each phase *depends on the invariant the previous one established*.

### 3. Why the IR — not the AST — is the front/back boundary

You might think the AST is the natural meeting point: it's already language-structured. But the AST is the *wrong* boundary, for three reasons:

1. **The AST is too language-specific.** A Rust AST has `match` and lifetimes; a C AST has `goto` and pointer arithmetic. A back end shouldn't have to understand every language's syntax tree. The IR is *deliberately impoverished* — a small, uniform instruction set that all front ends lower into.
2. **The AST is too high-level for optimization.** Optimizations want simple, explicit operations (one operation per instruction, explicit temporaries, explicit control flow as a graph). The AST hides control flow inside nested nodes. The IR makes it a flat **control-flow graph** that algorithms can walk.
3. **The IR is where the M + N reuse pays off.** If the boundary were the AST, every back end would need M parsers' worth of knowledge. By lowering all languages to one IR, the back end learns *one* thing. This is the entire reason LLVM IR exists as a first-class, documented, stable artifact.

So the IR sits *below* the AST and *above* machine code. It is the **narrow waist** of the system.

### 4. What makes a good IR: the "narrow waist" principle

A good IR is a careful balance:

- **Low enough** that the back end can generate efficient machine code without re-deriving the program's structure.
- **High enough** that it's still target-independent — no x86-specific registers, no ARM-specific addressing modes leaking in.
- **Uniform and small** — few instruction kinds, explicit and regular, so optimization passes are simple to write.
- **Typed and verifiable** — LLVM IR carries types (`i32`, `i8*`) and can be *verified* for internal consistency, catching front-end bugs.

The "narrow waist" metaphor (borrowed from the way IP is the narrow waist of the internet protocol stack) captures it: a *single, stable, narrow* interface that everything above and below agrees on. Many things plug in above (languages); many things plug in below (targets); the waist itself stays small and stable. The narrower and more stable the waist, the more reuse you get.

### 5. The three real architectures, mapped to the abstract pipeline

The abstract pipeline is the same everywhere, but the famous systems instantiate it differently:

**LLVM (Clang, Rust, Swift, Julia, …).**
```text
source ─[Clang/rustc/swiftc front end]→ LLVM IR ─[opt passes]→ LLVM IR ─[target backend]→ asm
        └─────── front end ──────────┘ └──────── middle end ────────┘ └──── back end ────┘
```
One IR, deliberately the product. Any front end that emits valid LLVM IR gets every back end. This is why three different languages, written by three different teams, share the same optimizer and code generators.

**GCC.** GCC predates LLVM's "single IR" philosophy and uses *three* IRs at descending levels:
```text
source ─[front end]→ GENERIC ─→ GIMPLE ─[tree opts]→ RTL ─[RTL opts + codegen]→ asm
        front end    (lang-       (SSA-      middle      (register-     back end
                      neutral      able 3-     end         transfer)
                      tree)        address)
```
- **GENERIC** — a language-neutral tree all GCC front ends produce.
- **GIMPLE** — a simplified, three-address form (max one operation per statement) where most middle-end optimization happens.
- **RTL (Register Transfer Language)** — a low-level form close to the machine, where the back end does its work.

GCC reaches the same goal (language- and target-independent middle) by a staircase of IRs rather than one.

**The JVM (javac + HotSpot).** Here the architecture is *split across two programs and two times*:
```text
.java ─[javac, AOT]→ JVM bytecode (.class) ─[ship it] ─[HotSpot at runtime]→ interpret → JIT → machine code
       front+IR-gen   the IR you distribute              back end happens AT RUNTIME, on hot code
```
`javac` is a small AOT compiler that targets **bytecode** — a portable IR. The real back end (the optimizing compiler) lives inside the JVM and runs **just in time**, only on code that proves hot. The "compiler" here is two compilers in two architectural positions.

**V8 (JavaScript).** Similar split, JS-flavored:
```text
JS source ─[parser]→ AST ─[Ignition]→ bytecode ─[interpret]→ ...hot?... ─[TurboFan]→ optimized machine code
```
Ignition is a bytecode interpreter; TurboFan is the optimizing JIT that kicks in for hot functions. Same shape: front end → bytecode IR → interpret → JIT the hot paths.

**rustc.** Lowers through *its own* IRs before handing off to LLVM:
```text
Rust ─[parse]→ AST ─→ HIR ─→ MIR ─[borrow-check, MIR opts]→ LLVM IR ─[LLVM]→ asm
                    (desugared) (borrow-check IR)            └── reuses LLVM's middle+back end ──┘
```
rustc does Rust-specific analysis (borrow checking) on its own **MIR**, then lowers to LLVM IR to reuse LLVM's optimizer and back ends. It is a front end (plus extra middle-end analysis) bolted onto LLVM.

The lesson: **one abstract pipeline, many concrete embodiments.** Where you place the back end (AOT vs JIT), how many IRs you use, and whether you reuse someone else's middle/back end are all engineering choices.

### 6. AOT vs JIT as an architectural decision

The pipeline's *stages* are fixed; *when and where* you run the back end is the architecture:

- **AOT (Ahead-Of-Time):** run the whole pipeline before the program ships. The user runs pure machine code. Pros: fast startup, no runtime compile cost, smaller runtime. Cons: can't use runtime information (actual types, hot paths), must commit to one target. (gcc, clang, rustc, go build.)
- **JIT (Just-In-Time):** ship an IR (bytecode), run an interpreter, and compile hot code to machine code *at runtime*, using profiling data. Pros: can specialize to actual runtime behavior, portable artifact (bytecode runs anywhere the VM does). Cons: warm-up cost, runtime memory and CPU overhead, harder to reason about. (JVM, V8, .NET CLR.)
- **Hybrid / tiered:** modern VMs run several tiers — interpreter → quick baseline JIT → aggressive optimizing JIT — promoting code up the tiers as it gets hotter. (HotSpot's C1/C2, V8's Ignition/Sparkplug/Maglev/TurboFan.)

This is one of the most consequential architecture decisions a language makes, and it's invisible in the source code.

### 7. The toolchain and the driver, more precisely

The **driver** (`gcc`, `clang`, `cc`) is itself just an orchestrator. For one `.c` file it typically runs:

1. **Preprocessor** (`cpp`, or built into `cc1`) — text substitution: `#include`, `#define`, conditional compilation. Output is still C source.
2. **Compiler proper** (`cc1` for C, `cc1plus` for C++) — the front/middle/back-end pipeline. Output is assembly text.
3. **Assembler** (`as`) — assembly text → object file (`.o`), a binary container of machine code plus relocation info.
4. **Linker** (`ld`, invoked via `collect2`) — combines object files and libraries, resolves cross-references, lays out the final executable.

The crucial mental separation: the "compiler" is step 2. Steps 1, 3, 4 are *other tools*. "Compiler error," "assembler error," and "linker error" are three different things, and conflating them sends you debugging in the wrong place. Separate compilation works because each translation unit becomes an independent `.o`, and the linker stitches them at the end — which is why editing one file recompiles only that file.

### 8. Error reporting and recovery as a cross-cutting concern

Notice that *every* phase can produce errors, and good diagnostics are not an afterthought — they are a product feature. The lexer reports illegal characters; the parser reports syntax errors; semantic analysis reports type and name errors; the linker reports unresolved symbols. Two design pressures cut across all phases:

- **Error recovery:** a good front end doesn't stop at the first syntax error — it recovers and keeps parsing to report *several* errors per run, so you fix many at once. This requires the parser to guess where the next valid construct starts.
- **Source location tracking:** to point at the right line and column, *every* token, AST node, and IR instruction must carry a source location. This metadata threads through the entire pipeline. The reason Rust and Clang have famously good errors is that they invested heavily in carrying precise spans and in clear recovery — it is engineering, not luck.

---

## Code Examples

These show the *same program* through different real compilers' representations, so you can see the abstract pipeline in concrete output.

### One C function through Clang's IR pipeline

```c
// sq.c
int square(int n) {
    return n * n;
}
```

```bash
# Unoptimized LLVM IR — close to a literal lowering of the AST:
clang -O0 -S -emit-llvm sq.c -o -
```
```llvm
define i32 @square(i32 %n) {
entry:
  %n.addr = alloca i32
  store i32 %n, i32* %n.addr
  %0 = load i32, i32* %n.addr
  %1 = load i32, i32* %n.addr
  %mul = mul i32 %0, %1
  ret i32 %mul
}
```
```bash
# Optimized — the middle end removed the redundant memory traffic:
clang -O2 -S -emit-llvm sq.c -o -
```
```llvm
define i32 @square(i32 %n) {
entry:
  %mul = mul i32 %n, %n
  ret i32 %mul
}
```

Same program, same IR *language*, but the optimizer (middle end) collapsed the `alloca`/`store`/`load` shuffle into a single `mul`. This is the middle end doing its job on a target-neutral form, before any CPU is chosen.

### The same program through GCC's GIMPLE

```bash
# Dump GCC's GIMPLE — its three-address middle-end IR:
gcc -O1 -fdump-tree-gimple -S sq.c
cat sq.c.*.gimple
```
```text
square (int n)
{
  int D.1234;
  D.1234 = n * n;
  return D.1234;
}
```

GIMPLE is GCC's analogue of LLVM IR: three-address, simplified, language-neutral. Note the temporary `D.1234` — GIMPLE enforces "at most one operation per statement," exactly the uniformity that makes optimization passes simple.

### The same logic as JVM bytecode

```java
// Square.java
class Square {
    static int square(int n) { return n * n; }
}
```
```bash
javac Square.java
javap -c Square          # disassemble the bytecode
```
```text
static int square(int);
  Code:
     0: iload_0          // push n
     1: iload_0          // push n
     2: imul             // multiply
     3: ireturn          // return
```

This bytecode is the **IR that javac ships**. The JVM will interpret it, and if `square` runs hot, HotSpot's JIT will compile it to machine code at runtime — the back end deferred to runtime.

### Watching the driver run the toolchain

```bash
clang -v -c sq.c -o sq.o 2>&1 | head
```
You'll see the driver invoke the internal front-end/codegen step and then the integrated assembler, with the exact flags. `-###` shows the commands *without* running them:
```bash
clang -### -c sq.c
```

### Cross-compilation: same front/middle end, different back end

```bash
# Same source, two targets — only the back end differs:
clang --target=x86_64-linux-gnu  -S sq.c -o sq.x86.s
clang --target=aarch64-linux-gnu -S sq.c -o sq.arm.s
diff sq.x86.s sq.arm.s     # totally different instructions, same logic
```

The front end and middle end produced identical IR; only the **back end** (selected by `--target`) changed. This is cross-compilation in one command, and it's possible *only* because the target is an isolated, swappable stage.

---

## Coding Patterns

### Pattern 1: Stage isolation — never let a phase peek ahead

When building any pipeline tool, keep each phase's output a *self-contained data structure* the next phase consumes, with no back-references:

```text
tokens   = lex(source)         # lexer knows nothing about grammar
ast      = parse(tokens)       # parser knows nothing about types
checked  = analyze(ast)        # semantic analysis adds symbol table
ir       = lower(checked)      # IR-gen knows nothing about the target CPU
asm      = codegen(ir, target) # back end is the ONLY target-aware stage
```

If your back end needs to know something about the source language, your IR boundary is in the wrong place.

### Pattern 2: Carry source spans end-to-end

Every node — token, AST node, IR instruction — should hold a `(file, line, col)` span. This is what lets a back-end error (e.g., "this would overflow") point at the original source line. Add the span *at creation* and propagate it through every lowering.

### Pattern 3: Make the IR verifiable

Give the IR an explicit `verify()` that checks its invariants (types match, every block ends in a terminator, no use-before-def). Run it after every pass in debug builds. LLVM's `-verify` pass exists precisely to catch front-end bugs at the IR boundary instead of as mysterious miscompiles later.

### Pattern 4: Separate compilation by translation unit

Compile each unit to an object file independently, link at the end:

```bash
clang -c parser.c -o parser.o
clang -c lexer.c  -o lexer.o
clang parser.o lexer.o -o tool   # link step resolves cross-references
```

This is the pattern `make`/Bazel exploit: a changed unit recompiles alone, and only the fast link step runs over the rest.

### Pattern 5: Choose the lowering depth deliberately

If you're building a simple language, a *tree-walking interpreter* (no IR, just walk the AST) may be enough. If you need speed, lower to a bytecode IR and interpret that. If you need native speed, lower further or emit LLVM IR and reuse LLVM. Pick the rung of the staircase that matches your performance budget.

---

## Best Practices

- **Pin down the IR contract first.** In any multi-stage tool, the interface between stages (the IR/data structure) is the most important design decision. Get it right and stages become swappable; get it wrong and everything is coupled.
- **Verify the IR after every transformation in debug builds.** Catch the bug at the boundary, not three passes downstream.
- **Keep the back end the *only* target-aware stage.** The moment x86 knowledge leaks into the middle end, you've lost portability.
- **Track source locations religiously.** Good diagnostics are a feature; they require spans threaded through the whole pipeline. Add them early, never strip them.
- **Recover from errors; report many.** A front end that stops at the first error wastes the user's time. Recover and continue parsing.
- **Dump intermediate forms when debugging.** `-emit-llvm`, `-fdump-tree-*`, `javap -c`, `--emit=mir` (rustc) — each lets you inspect the program between phases.
- **Match architecture to constraints.** AOT for startup-critical and offline; JIT for long-running and adaptive; tree-walk for simplicity; LLVM-backed for native performance with low effort.

---

## Edge Cases & Pitfalls

- **The AST is not the parse tree.** The parse tree (CST) mirrors the grammar literally, including every `(` and `;`. The AST throws that noise away. Tools that need exact source (formatters, refactoring) sometimes need the CST, not the AST.
- **Forward references break single-pass designs.** If function A calls B but B is defined later, a single-pass compiler hasn't seen B yet. C solved this with forward declarations; multi-pass compilers solve it with a declaration-collection pass first.
- **A "language-independent" IR can still leak target details.** Pointer size, integer width, struct layout, and endianness are easy to bake in accidentally. LLVM IR carries an explicit *data layout* string to keep this honest.
- **Bytecode is not machine code.** A `.class` or `.pyc` is IR for a VM; it still needs the VM (and its JIT) to run. People conflate "compiled to bytecode" with "compiled to native."
- **Optimization can change observable behavior if your program has undefined behavior.** The optimizer assumes your program is well-defined; UB (signed overflow, out-of-bounds) lets it do surprising things. The bug is in the source, but it *surfaces* in the optimizer.
- **`-O3` is not strictly faster than `-O2`.** Aggressive inlining and unrolling can bloat code and thrash the instruction cache. Measure, don't assume.
- **Linker errors masquerade as compiler errors to beginners.** "Undefined reference" is a *linker* failure; the compiler was happy. Fixing it means linking the right object/library, not editing the source.
- **JIT warm-up skews benchmarks.** Benchmarking a JIT'd language without warming it up measures the interpreter, not the optimized code. Always warm up before timing.

---

## Common Mistakes

1. **Drawing the front/back boundary at the AST.** The AST is too language-specific and too high-level. The IR is the boundary precisely because it's neither.
2. **Assuming one compiler = one IR.** GCC has three (GENERIC/GIMPLE/RTL); rustc has HIR/MIR before LLVM IR. Multiple IRs at descending levels is normal.
3. **Believing JIT and AOT compile *differently*.** They run the *same pipeline*; they differ in *when* and *where* the back end runs. The phases are identical.
4. **Thinking the linker is part of "the compiler."** It's a separate tool the driver invokes. Treating it as part of the compiler hides where build failures come from.
5. **Stripping source locations during lowering.** Then your back-end errors point at nothing, and your diagnostics are useless.
6. **Letting the middle end know the target.** This couples the neutral stage to one CPU and kills cross-compilation.
7. **Optimizing source code the compiler already optimizes.** Read the `-O2` IR first; the middle end probably did it for you.
8. **Treating GENERIC/GIMPLE/RTL or HIR/MIR as trivia.** They're the concrete answer to "how do real compilers lower in steps" — they make the abstract staircase real.

---

## Tricky Points

- **The IR is both a data structure and a *language*.** LLVM IR has an in-memory form, a text form (`.ll`), and a binary form (`.bc`) — all the same thing. Treating it as a first-class, serializable language (not just an internal struct) is what enabled link-time optimization and a whole ecosystem of tools.
- **GCC and LLVM reach the same goal differently.** GCC's staircase of IRs and LLVM's single IR both achieve language- and target-independence. There is no one right number of IRs.
- **rustc is "a front end on LLVM," but does serious middle-end work itself.** Borrow checking happens on MIR, *before* lowering to LLVM IR — because borrow checking is Rust-specific and LLVM knows nothing about lifetimes. The phase boundary is "Rust-specific analysis on MIR, then reuse LLVM."
- **The JVM splits the pipeline across compile time and run time.** `javac` (AOT) does the front end + IR generation; HotSpot (JIT) does the back end at runtime. "The Java compiler" is genuinely two compilers in two architectural positions.
- **Tiered JITs run several back ends at once.** V8 has Ignition (interpreter), Sparkplug/Maglev (fast JITs), and TurboFan (optimizing JIT). A hot function is re-compiled at higher tiers while older versions still run. The architecture is dynamic.
- **The preprocessor is a separate language.** C's `#include`/`#define` is text substitution that runs *before* the compiler sees real C. It has its own bugs and its own error class, distinct from the compiler proper.
- **"Compile to native" can still mean "via LLVM IR."** rustc, Swift, and Clang all produce native code, but route through LLVM IR. "Native" describes the output, not the absence of an IR.

---

## Apply it

1. Find a real component where **The Big Picture (Compiler Architecture)** affects an interface or dependency.
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

- Which boundary is most affected by The Big Picture (Compiler Architecture)?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
