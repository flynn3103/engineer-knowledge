# Bytecode & Virtual Machines — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Bytecode & Virtual Machines** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Why have bytecode at all? The two-step compile

A pure interpreter could read your source text and execute it directly, re-parsing every line each time it runs. That's slow: parsing is expensive and you'd redo it on every loop iteration. A pure compiler could translate source straight to machine code — fast, but the result only runs on *one* kind of CPU, and the compiler has to know every processor.

Bytecode splits the difference into **two steps**:

1. **Compile** source → bytecode, *once*. The hard work (parsing, name resolution, turning expressions into instructions) happens here.
2. **Execute** bytecode on a VM, *every time you run*. This is fast because the bytecode is already simple and pre-digested.

The payoff:

- **Portability.** The bytecode is the same on every machine. Only the VM is platform-specific. Ship one `.jar`, run it on Windows, macOS, Linux, a phone — anywhere with a JVM.
- **Compactness.** Bytecode is dense. A whole method fits in a handful of bytes.
- **Speed vs. a tree-walker.** Executing a flat list of simple opcodes is much faster than re-walking a syntax tree.
- **Safety (later).** Bytecode can be *checked* before it runs (the JVM verifier — see `middle.md`).

### 2. The stack machine: the most common VM design

Most famous VMs — the JVM, CPython, the .NET CLR, WebAssembly — are **stack machines**. The defining feature: instructions don't name where their inputs come from. They pop inputs off an **operand stack** and push results back.

Think of the operand stack as a scratchpad. To compute `2 + 3`:

```
PUSH 2        stack: [2]
PUSH 3        stack: [2, 3]
ADD           pops 3 and 2, pushes 5 → stack: [5]
```

The `ADD` instruction is tiny — it carries *no operands at all*. It just says "take the top two, add them, put the result back." Every arithmetic op works this way. This makes the instruction set small and the compiler simple: to compile an expression, you walk it and emit pushes and operations in the right order.

### 3. Local variables live in numbered slots

The operand stack is for *temporary* values mid-calculation. Your actual variables (`x`, `total`, `i`) live in a separate place: **local variable slots**, numbered `0, 1, 2, …`. Two instructions move values between the slots and the stack:

- `LOAD slot_n` — push the value in slot *n* onto the stack.
- `STORE slot_n` — pop the top of the stack into slot *n*.

So `x = a + b` (where `a`, `b`, `x` are slots 0, 1, 2) becomes:

```
LOAD 0        push a
LOAD 1        push b
ADD           pop both, push a+b
STORE 2       pop result into x
```

### 4. The constant pool: refer to literals by number

Instructions are kept small. Instead of embedding the string `"hello"` or the number `3.14159` directly inside an instruction, the compiler puts those literals in a side-table — the **constant pool** — and the instruction just carries an *index* into it.

```
LOAD_CONST 0    # pool[0] is the string "hello"
LOAD_CONST 1    # pool[1] is the number 42
```

This keeps the instruction stream uniform and dense, and lets the same literal be shared by many instructions without repeating it.

### 5. The interpreter loop: fetch, decode, execute

The whole VM is, at its heart, one loop:

1. **Fetch** the next opcode (read the byte at the "program counter," then advance it).
2. **Decode** it (figure out which operation this byte means).
3. **Execute** the matching action (do the add, the push, the jump…).
4. Go back to step 1.

In pseudo-code:

```
pc = 0
while true:
    op = code[pc]; pc += 1
    switch op:
        case PUSH:  operand = code[pc]; pc += 1; stack.push(operand)
        case ADD:   b = stack.pop(); a = stack.pop(); stack.push(a + b)
        case LOAD:  slot = code[pc]; pc += 1; stack.push(locals[slot])
        case STORE: slot = code[pc]; pc += 1; locals[slot] = stack.pop()
        case RETURN: return stack.pop()
        ...
```

That `switch` *is* the virtual machine. Everything else is bookkeeping.

### 6. Where the bytecode is stored

You can usually *see* the bytecode on disk:

- **Python** writes compiled modules to `__pycache__/<name>.cpython-XY.pyc`. Next time you import that module, if the source hasn't changed, Python skips recompiling and loads the cached bytecode. That's why imports are fast the second time.
- **Java** writes one `.class` file per class. A `.jar` is just a zip of `.class` files plus metadata.
- **C#** compiles to **CIL** (Common Intermediate Language) inside a `.dll` or `.exe` assembly.

---

## Code Examples

### Example 1: Reading Python bytecode with `dis`

Python ships a disassembler in the standard library. Let's see real bytecode.

```python
import dis

def add(a, b, c):
    return a + b * c

dis.dis(add)
```

Output (Python 3.11, lightly annotated — exact format varies by version):

```
  RESUME              0
  LOAD_FAST           a          # push local a
  LOAD_FAST           b          # push local b
  LOAD_FAST           c          # push local c
  BINARY_OP           5 (*)      # pop c, b → push b*c
  BINARY_OP           0 (+)      # pop (b*c), a → push a+(b*c)
  RETURN_VALUE                   # pop and return
```

Notice the *order*: it pushes `a`, then `b`, then `c`, multiplies `b*c` first (because `*` binds tighter than `+`), then adds. The bytecode *encodes operator precedence* by the order of operations — the VM itself knows nothing about precedence. The compiler already figured it out.

`LOAD_FAST` is Python's fast path for function locals (they live in numbered slots). The numbers after `BINARY_OP` are operands selecting *which* binary operation.

### Example 2: Reading Java bytecode with `javap`

```java
public class Calc {
    int compute(int a, int b, int c) {
        return a + b * c;
    }
}
```

Compile and disassemble:

```
javac Calc.java
javap -c Calc
```

Output (the `compute` method):

```
int compute(int, int, int);
  Code:
     0: iload_1      // push local 1 (a)  — slot 0 is 'this'
     1: iload_2      // push local 2 (b)
     2: iload_3      // push local 3 (c)
     3: imul         // pop c,b → push b*c
     4: iadd         // pop (b*c),a → push a+(b*c)
     5: ireturn      // return the int on top
```

Same stack-machine shape as Python, but the opcodes are **typed**: `iload`/`imul`/`iadd`/`ireturn` are the *integer* versions. There are parallel families for `long` (`l`), `float` (`f`), `double` (`d`). Slot 0 is `this` because `compute` is an instance method, so `a`, `b`, `c` are slots 1, 2, 3 — hence `iload_1`, `iload_2`, `iload_3`.

### Example 3: Tracing the stack by hand

Take `a + b * c` with `a=2, b=3, c=4`. Expected result: `2 + 3*4 = 14`. Walk the JVM bytecode and track the operand stack:

```
iload_1   push a(2)        stack: [2]
iload_2   push b(3)        stack: [2, 3]
iload_3   push c(4)        stack: [2, 3, 4]
imul      3*4=12           stack: [2, 12]
iadd      2+12=14          stack: [14]
ireturn   return 14        stack: []
```

Do this on paper a few times. Once the stack movements feel obvious, you understand how a stack machine evaluates *any* expression.

### Example 4: A 30-line stack VM you can read

Here is a complete (toy) stack VM in Python. It runs one program: compute `2 + 3 * 4`.

```python
# Opcodes
PUSH, ADD, MUL, PRINT, HALT = range(5)

program = [
    PUSH, 2,
    PUSH, 3,
    PUSH, 4,
    MUL,        # 3*4 = 12
    ADD,        # 2+12 = 14
    PRINT,
    HALT,
]

def run(code):
    stack = []
    pc = 0
    while True:
        op = code[pc]; pc += 1
        if op == PUSH:
            stack.append(code[pc]); pc += 1
        elif op == ADD:
            b = stack.pop(); a = stack.pop(); stack.append(a + b)
        elif op == MUL:
            b = stack.pop(); a = stack.pop(); stack.append(a * b)
        elif op == PRINT:
            print(stack[-1])
        elif op == HALT:
            return

run(program)   # prints 14
```

That `while`/`if`-chain is a real (tiny) virtual machine. CPython's and the JVM's are the same shape — just with hundreds of opcodes, typed operations, function calls, and decades of optimization. Building one yourself is the capstone in `tasks.md`.

---

## Coding Patterns

### Pattern 1: Disassemble to understand, not to optimize (yet)

When you're curious *how* a construct compiles, disassemble it.

```python
import dis
dis.dis(lambda x: x * 2 + 1)
```

This is a learning tool. Don't start "optimizing for fewer bytecodes" as a junior — that's almost always premature. Use `dis` to build intuition about what the language does under the hood.

### Pattern 2: Compare two ways of writing the same thing

```python
import dis
dis.dis(lambda lst: [x*2 for x in lst])   # list comprehension
print("---")
dis.dis(lambda lst: list(map(lambda x: x*2, lst)))  # map + lambda
```

Seeing the different bytecode makes the performance difference concrete instead of folklore.

### Pattern 3: Trust the `.pyc` cache, but know it exists

You normally never touch `.pyc` files — Python manages them. But knowing they're *there* explains: why the first import is slower, why deleting `__pycache__/` is harmless (it regenerates), and why a stale cache *almost* never bites you (Python checks source timestamps/hashes).

---

## Best Practices

1. **Disassemble to learn.** `dis.dis(fn)` and `javap -c Class` are the cheapest way to understand "what does this actually do." Do it often while learning.

2. **Don't micro-optimize bytecode counts.** Fewer bytecodes ≠ faster in any way you can reliably measure as a junior. The JIT and the VM internals dominate. Measure real time before believing anything.

3. **Let the VM manage its caches.** Don't commit `__pycache__/` or `.class` files to source control (they're build artifacts). Add them to `.gitignore`. They regenerate.

4. **Know which file is which.** `.pyc` = Python bytecode cache. `.class` = one Java class. `.jar` = zip of classes. `.dll`/`.exe` (managed) = .NET CIL assembly. `.wasm` = WebAssembly module.

5. **Keep source and bytecode in sync.** If you ever see "bizarre" behavior after editing, a stale cache is a rare-but-real suspect. Delete `__pycache__/` and re-run to rule it out.

---

## Edge Cases & Pitfalls

- **"Compiled" doesn't mean "machine code."** A `.pyc` or `.class` is *compiled* — to bytecode, not to native instructions. People conflate "compiled" with "fast native binary." Java and Python are both compiled-to-bytecode.

- **Bytecode is version-specific.** A `.pyc` built by Python 3.11 won't load in 3.12 (the bytecode format and opcode numbers change between versions). That's why `.pyc` filenames embed the version (`cpython-311`). The JVM is far more stable across versions by design.

- **Decompilation is easy.** A `.class` file decompiles back to near-original Java. If you thought shipping bytecode "hides" your source, it doesn't. (Obfuscators exist for this reason.)

- **The operand stack is not the call stack.** A classic confusion. The operand stack holds *expression temporaries*; the call stack holds *function frames*. Each frame has its own operand stack.

- **`dis` output changes between Python versions.** Don't memorize exact opcode names (`BINARY_ADD` became `BINARY_OP` in 3.11). Learn the *shape*, not the spelling.

- **A VM is not an emulator.** An emulator pretends to be *another real* CPU (e.g. running old console games). A VM here executes a *designed-from-scratch imaginary* instruction set. Related idea, different purpose.

---

## Common Mistakes

1. **Thinking Python "interprets source line by line."** It doesn't — it compiles each module to bytecode first, *then* the VM runs the bytecode. The "interpreter" interprets *bytecode*, not text.

2. **Assuming bytecode is unreadable binary gibberish.** It's structured and easy to disassemble. `javap -c` and `dis` show you exactly what's there.

3. **Believing fewer lines of source = fewer bytecodes = faster.** No reliable relationship. Measure.

4. **Confusing the JVM with the Java language.** The JVM runs *bytecode*, from any language that emits it — Kotlin, Scala, Clojure, Groovy all run on the JVM. The VM doesn't know or care what language produced the bytecode.

5. **Committing build artifacts.** `__pycache__/`, `*.class`, `*.pyc` belong in `.gitignore`.

---

## Apply it

1. Choose one small, known input for **Bytecode & Virtual Machines**.
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

- What problem does Bytecode & Virtual Machines solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
