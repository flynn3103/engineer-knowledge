# Intermediate Representations — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Intermediate Representations** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The IR Is a Program That Means the Same Thing, Said More Simply

Take this source line:

```c
x = (a + b) * (a + b);
```

The AST for it is a tree with a `*` at the root and two identical `(a + b)` subtrees. That is faithful to the syntax, but it is awkward to optimize and impossible to hand to a CPU, because a CPU does not understand "multiply two subtrees." The IR rewrites it as a *flat list of one-operation-at-a-time steps*:

```text
t1 = a + b
t2 = a + b
t3 = t1 * t2
x  = t3
```

Each line does exactly one thing. Each line names its result. This is **three-address code**, and it is the most common shape for a beginner-friendly IR. Notice that the IR has *more lines* than the source but each line is *simpler*. That trade — more steps, each trivial — is the whole point: simple, regular steps are easy for the compiler to reason about.

(An optimizer would later notice `t1` and `t2` compute the same thing and rewrite this to one addition. That optimization — *common subexpression elimination* — is exactly the kind of thing the IR exists to enable.)

### 2. The Narrow Waist: M + N, Not M × N

Here is the idea that justifies the existence of IRs. Draw it:

```text
WITHOUT a shared IR:                  WITH a shared IR:

C ──► x86                             C ────┐         ┌──► x86
C ──► ARM                             C++ ──┤         ├──► ARM
C++ ─► x86                            Rust ─┤──► IR ──┤──► RISC-V
C++ ─► ARM                            Swift ┘         └──► Wasm
Rust ► x86
Rust ► ARM       ... (M × N paths)       (M front ends + N back ends)
```

With 4 languages and 4 targets, the left side needs **16** complete compilers. The right side needs **4 + 4 = 8** pieces, and adding a *fifth* language costs one front end (which immediately works on all targets), while adding a *fifth* target costs one back end (which immediately works for all languages). This combinatorial saving is *the* reason LLVM became the foundation of Clang, Rust, Swift, Julia, and dozens of other languages — they all share one IR and one set of back ends.

### 3. Three-Address Code: The Shape

"Three-address" means each instruction names *at most three things*: one result and (up to) two operands. The forms you will see:

| TAC form | Example | Meaning |
|----------|---------|---------|
| Binary op | `t1 = a + b` | compute `a + b`, store in `t1` |
| Unary op | `t2 = -x` | negate `x` |
| Copy | `y = t1` | move a value |
| Conditional branch | `if t1 goto L2` | jump if `t1` is true |
| Unconditional branch | `goto L3` | always jump |
| Label | `L2:` | a named position to jump to |
| Call | `t3 = call f, 2` | call `f` with 2 args |

A complex expression becomes a *sequence* of these by inventing temporaries for each intermediate result. This "flattening" of a tree into a list is one of the first jobs the IR-builder does.

### 4. The Control-Flow Graph: The Picture Underneath Everything

A linear list of TAC has branches in it (`goto`, `if ... goto`). To analyze a program, the compiler groups instructions into **basic blocks** and connects them with edges. A **basic block** is a run of instructions you always execute together: you enter at the top, and you fall straight through to the bottom — no jump can land in the middle, and only the last instruction can be a branch.

Consider:

```c
if (x > 0)
    y = 1;
else
    y = 2;
z = y;
```

As a CFG:

```text
        ┌─────────────────────┐
        │ B0 (entry)          │
        │   t = x > 0         │
        │   if t goto B1      │
        │   else goto B2      │
        └────────┬─────┬──────┘
            true │     │ false
                 ▼     ▼
        ┌──────────┐ ┌──────────┐
        │ B1       │ │ B2       │
        │  y = 1   │ │  y = 2   │
        │ goto B3  │ │ goto B3  │
        └─────┬────┘ └────┬─────┘
              │           │
              └─────┬─────┘
                    ▼
              ┌──────────┐
              │ B3       │
              │  z = y   │
              └──────────┘
```

This graph is the **substrate** for almost everything a compiler does later: figuring out which variables are alive where, which code is unreachable, where loops are, and so on. When you hear "dataflow analysis," it means "walk this graph and track facts." **Build the CFG, and you have unlocked the entire optimization toolbox.**

### 5. Lowering: Information Loss on Purpose

Going from AST to IR is called **lowering**. Each step throws away high-level structure that the machine does not need and makes the low-level structure explicit. The AST says "this is a `for` loop"; the IR says "here is a block, here is a comparison, here is a conditional branch back to the top." The loop *concept* is gone; the loop *mechanics* are spelled out. That is deliberate. Lower-level forms are more uniform and therefore easier to optimize and to translate to machine code. Compilers often lower in several stages — high-level IR, then mid-level, then low-level — which is the subject of later levels.

### 6. Stack-Based vs Register-Based IRs (a First Taste)

There are two big families of IR you will meet:

- **Register-based** IRs (like LLVM IR) use an *unlimited* supply of named virtual registers: `%1 = add i32 %a, %b`. The three-address code above is register-based — each `t1`, `t2` is a virtual register. This is convenient for analysis and is what optimizing compilers prefer.
- **Stack-based** IRs (like **JVM bytecode**, **.NET CIL**, and **WebAssembly**) have no named temporaries. Instead they push operands onto an operand stack and apply operators that pop their inputs and push their result. `a + b` becomes "push a, push b, add" — and `add` implicitly takes the top two stack slots. This is compact (great for *distributing* code, e.g. a `.class` file you download) but the implicit stack makes some analyses fiddlier.

You will meet both. For now just know: a register-based IR names every value; a stack-based IR keeps values on an implicit stack. We will say much more in `senior.md`.

---

## Code Examples

Below we take one small function and show its source, its three-address code, and its control-flow graph. The exact IR syntax is invented for teaching (real IRs come in `senior.md`), but the *shape* is faithful.

### Example 1: A straight-line expression → TAC

Source:

```c
int f(int a, int b) {
    return (a + b) * (a - b);
}
```

Three-address code:

```text
f(a, b):
    t1 = a + b
    t2 = a - b
    t3 = t1 * t2
    return t3
```

Each operation gets its own line and its own temporary. The nested expression tree becomes a flat list. This is the most basic lowering: walk the AST, and for each operator node, emit one instruction and a fresh temp.

### Example 2: An `if` → TAC with branches and labels

Source:

```c
int max(int a, int b) {
    int m;
    if (a > b)
        m = a;
    else
        m = b;
    return m;
}
```

Three-address code:

```text
max(a, b):
    t1 = a > b
    if t1 goto L_then
    goto L_else
L_then:
    m = a
    goto L_end
L_else:
    m = b
    goto L_end
L_end:
    return m
```

The high-level `if/else` is gone. In its place: a comparison producing a boolean temp, a conditional jump, and labels marking where execution can land. This is what "lowering control flow" looks like.

### Example 3: The same `max` as a control-flow graph

```text
        ┌─────────────────────┐
        │ entry               │
        │   t1 = a > b        │
        │   if t1 goto then   │
        └───────┬──────┬──────┘
           true │      │ false
                ▼      ▼
        ┌──────────┐ ┌──────────┐
        │ then     │ │ else     │
        │  m = a   │ │  m = b   │
        └─────┬────┘ └────┬─────┘
              └─────┬──────┘
                    ▼
              ┌──────────┐
              │ end      │
              │ return m │
              └──────────┘
```

Four basic blocks, edges showing the two ways to reach `end`. Notice that `m` is assigned in *two different blocks*. The block `end` reads whichever value arrived. Keep this picture in mind — when you reach `middle.md`, this exact "value comes from two places at a merge" situation is what **SSA's φ (phi) function** is invented to handle.

### Example 4: A loop → CFG with a back edge

Source:

```c
int sum_to(int n) {
    int s = 0;
    int i = 1;
    while (i <= n) {
        s = s + i;
        i = i + 1;
    }
    return s;
}
```

Control-flow graph:

```text
   ┌──────────────┐
   │ entry        │
   │  s = 0       │
   │  i = 1       │
   └──────┬───────┘
          ▼
   ┌──────────────┐ ◄────────────┐
   │ header       │              │
   │  t = i <= n  │              │  back edge
   │  if t goto   │              │  (loop)
   │   body       │              │
   └───┬──────┬───┘              │
 true  │      │ false            │
       ▼      ▼                  │
 ┌──────────┐ ┌──────────┐       │
 │ body     │ │ exit     │       │
 │  s = s+i │ │ return s │       │
 │  i = i+1 │ └──────────┘       │
 └────┬─────┘                    │
      └──────────────────────────┘
```

The edge from `body` back up to `header` is a **back edge** — it is how the compiler recognizes a loop. Loops are just cycles in the CFG. Once you can see loops as cycles, loop optimizations (hoisting code out of the loop, unrolling) become graph manipulations.

### Example 5: Stack-based vs register-based for `a + b`

Same expression, two IR families:

```text
Register-based (LLVM-style, named values):
    %1 = add i32 %a, %b

Stack-based (JVM-bytecode-style, implicit operand stack):
    iload a      ; push a
    iload b      ; push b
    iadd         ; pop b, pop a, push a+b
```

The register form names the result (`%1`). The stack form leaves the result on top of the stack for the next instruction to consume. Both are valid IRs; they make different trade-offs (compactness vs ease of analysis).

---

## Coding Patterns

### Pattern 1: Emit-as-you-walk (AST → TAC)

Lowering an AST to three-address code is a recursive walk. Each `gen` call emits instructions and *returns the temporary holding its result*:

```python
counter = 0
def fresh():
    global counter
    counter += 1
    return f"t{counter}"

def gen(node):
    if node.kind == "num":
        return str(node.value)            # literals need no temp
    if node.kind == "var":
        return node.name
    if node.kind == "binop":
        left  = gen(node.left)            # recursively lower operands
        right = gen(node.right)
        t = fresh()
        emit(f"{t} = {left} {node.op} {right}")
        return t                          # caller uses this temp
```

The key idea: a child lowers itself and hands its result up as a temp name; the parent combines child temps into one new instruction. This single pattern lowers any expression tree.

### Pattern 2: Build basic blocks while emitting

Start a new block whenever you emit a label or just after a branch. A simple builder keeps a "current block" and appends to it:

```python
def emit(instr):
    current_block.instructions.append(instr)

def start_block(label):
    global current_block
    current_block = Block(label)
    cfg.add(current_block)
```

The rule for *ending* a block: a branch (`goto`, `if ... goto`) or a `return` is always the last instruction in its block. The next instruction begins a new block.

### Pattern 3: Labels first, fill later (forward branches)

When lowering an `if`, you need to jump to the `else` block before you have emitted it. Allocate the *label name* up front, emit the branch to it, and define the label's block later:

```python
l_then, l_else, l_end = fresh_label(), fresh_label(), fresh_label()
cond = gen(if_node.condition)
emit(f"if {cond} goto {l_then}")
emit(f"goto {l_else}")
start_block(l_then); gen(if_node.then_branch); emit(f"goto {l_end}")
start_block(l_else); gen(if_node.else_branch); emit(f"goto {l_end}")
start_block(l_end)
```

### Pattern 4: One pass per concern

Resist doing everything in one giant pass. Lower to IR in one pass; build the CFG in another; run each optimization as its own pass over the IR. Passes that each do one thing are easy to test and reorder.

---

## Best Practices

- **Keep each IR instruction trivially simple.** One operator, named result. If an instruction does two things, split it. Simplicity is what makes analysis tractable.
- **Make every value have a clear name (in register-based IR).** Never reuse a temp for an unrelated value during lowering — fresh temps are cheap and prevent confusion. (This habit also eases the jump to SSA later.)
- **Build the CFG explicitly.** Do not leave control flow implicit in a flat list. The graph is the thing every later pass needs.
- **Decide your IR's *level* deliberately.** High-level enough to be target-independent, low-level enough that lowering to machine code is straightforward. When unsure, start higher and lower in stages.
- **Print your IR.** A textual dump you can read (and diff in tests) is worth its weight in gold. Every real compiler can print its IR; yours should too.
- **Lower in stages, not one leap.** AST → high-level IR → low-level IR is easier to get right than AST → assembly directly.
- **Verify the IR.** A small checker that asserts "every temp is defined before use," "every block ends in a branch or return," and "every branch target exists" catches a huge class of bugs early.

---

## Edge Cases & Pitfalls

- **Falling off the end of a block.** Every basic block must end in a branch, jump, or return. A block that "just stops" with no terminator is malformed — the CFG has no edge out of it. Forgetting the terminator on the `then` branch of an `if` (so it falls into the `else`) is a classic beginner bug.
- **Reusing a temporary across an unrelated computation.** If `t1` holds `a + b` and you later reuse `t1` for `c * d`, you have created a fake dependency and likely a wrong-code bug. Always use fresh temps while lowering.
- **Confusing "the IR is text" with "the IR is a data structure."** The textual dump is a *view*. Internally the IR is objects/graphs. You manipulate the structure, not strings.
- **Branching into the middle of a block.** By definition impossible in a correct CFG — a jump target must be the *start* of a block. If your lowering produces a jump into the middle of a block, you have split the block wrong.
- **Forgetting that a value at a merge can come from two places.** In the `max` example, `m` is set in two blocks and read in a third. A naive IR just writes `m` twice; this is fine until you move to SSA, where it forces the φ-function. Knowing this now makes `middle.md` painless.
- **Choosing the wrong IR level.** Too high-level (close to the AST) and you cannot express machine concerns; too low-level (close to assembly) and you lose portability and the ability to optimize generally. This is a genuine design decision, not a detail.
- **Treating the IR as throwaway.** Beginners sometimes skip the IR and translate AST straight to assembly. It works for toys and collapses the moment you want optimization or a second target. The IR is the investment that pays off later.
- **Assuming one IR is enough.** Real compilers stack several IRs at different levels. You do not need that on day one, but do not be surprised that LLVM has GENERIC/GIMPLE/RTL-like layering elsewhere and MLIR has many "dialects" — covered in higher levels.

---

## Apply it

1. Choose one small, known input for **Intermediate Representations**.
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

- What problem does Intermediate Representations solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
