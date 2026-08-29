# Bytecode & Virtual Machines — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Bytecode & Virtual Machines** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Stack-based vs register-based: the central trade-off

Both designs are virtual machines. The difference is *where instructions get their operands*.

**Stack machine.** Operands are implicit — on the operand stack.

```
; compute  x = a + b   (a,b,x are locals 0,1,2)
LOAD 0
LOAD 1
ADD
STORE 2
```

Four instructions. Each is tiny (often 1 byte + maybe a small operand). The instruction stream is long but the instructions are simple.

**Register machine.** Operands are explicit — instructions name source and destination "registers" (numbered local slots).

```
; same computation
ADD r2, r0, r1     ; r2 = r0 + r1
```

*One* instruction. But it's bigger — it carries three register numbers. The instruction stream is short but each instruction is wide.

The trade-off, precisely:

| Aspect | Stack VM | Register VM |
|--------|----------|-------------|
| **Instructions per operation** | More (lots of explicit push/pop) | Fewer (operands named in one instr) |
| **Instruction size** | Small (few/no operands) | Larger (multiple operand fields) |
| **Total code size** | Often comparable; more instrs, smaller each | Often comparable; fewer instrs, bigger each |
| **Dispatch count** | **Higher** — each instr is a trip through the loop | **Lower** — fewer trips through the loop |
| **Codegen complexity** | **Simpler** — emit push/op/pop, no register allocation | **Harder** — must assign virtual registers (a mini register-allocation problem) |
| **JIT-ability** | Fine, but the JIT must reconstruct dataflow from stack pushes/pops | **Easier** — operands and dataflow are explicit |
| **Examples** | JVM, CPython, CLR, Wasm | Lua 5, Dalvik (Android), BEAM-style |

The headline insight: **dispatch is expensive.** Every time the interpreter loop fetches and decodes an instruction, it pays overhead (a branch the CPU may mispredict — see `senior.md`). Register VMs do fewer, fatter instructions, so they dispatch less often. That's exactly why **Lua 5.0 switched from a stack VM to a register VM** and got measurably faster — fewer instructions executed for the same work. Dalvik (the original Android VM) chose register-based for the same reason, *and* because explicit operands are friendlier to ahead-of-time and JIT compilation.

The counter-argument for stack VMs: **simplicity and density.** Codegen is trivial (walk the expression tree, emit pushes and ops), the encoding is compact, and the format is uniform — which makes verification and portability easier. The JVM and Wasm chose stack precisely because the *bytecode is a transport format* meant to be small, verifiable, and easy to generate, with the real performance recovered later by a JIT.

### 2. Anatomy of an instruction

An instruction is **opcode + zero or more operands**. The design choices:

**Fixed-width vs variable-width.**
- *Fixed-width* (e.g. Lua, Dalvik): every instruction is the same size (Lua uses 32-bit words). Decoding is trivial — `pc += 4` always — and the PC math is simple. Costs some space when an instruction needs fewer bits than the fixed width allows.
- *Variable-width* (e.g. the JVM, Wasm, CPython historically): the opcode is one byte; how many operand bytes follow depends on the opcode. Denser, but decoding must know each opcode's length, and PC advancement varies.

**Where do operands come from?**
- *Inline*: bytes right after the opcode. A jump offset, a local-slot number, a small integer. `bipush 100` carries the byte `100` inline.
- *Constant-pool index*: the operand is an *index*; the real value (a string, a large number, a method reference) lives in the constant pool. `ldc #7` means "load constant pool entry 7."

**Typed vs untyped opcodes.**
- The JVM is *typed*: `iadd` (int), `ladd` (long), `fadd` (float), `dadd` (double) are four distinct opcodes. This makes verification and JIT straightforward but multiplies the opcode count.
- CPython is largely *untyped*: `BINARY_OP` dispatches on the runtime types of the operands (because Python is dynamically typed — the bytecode *can't* know the types ahead of time).

**CPython 3.6+ uses fixed 2-byte instructions.** Since 3.6, every CPython instruction is exactly `(opcode, arg)` — 2 bytes — with `EXTENDED_ARG` prefixes for arguments larger than 255. So even the "variable-width" JVM and "wordcode" CPython make different choices.

### 3. Stack effect and maximum stack depth

Every instruction has a **stack effect**: how many values it pops and pushes.

```
LOAD_CONST   ( 0 pop, 1 push )  →  +1
ADD          ( 2 pop, 1 push )  →  −1
POP          ( 1 pop, 0 push )  →  −1
STORE slot   ( 1 pop, 0 push )  →  −1
```

Two consequences:

1. **The stack must balance.** A well-formed method ends with the operand stack at a predictable depth (often empty after a `return`). If you emit code where a branch leaves the stack at depth 2 and the fall-through leaves it at depth 1, you've produced *invalid* bytecode. The JVM verifier (see `senior.md`) rejects exactly this.
2. **The compiler computes the maximum depth** the stack ever reaches and records it (`max_stack` in a `.class`). The VM uses it to pre-allocate each call frame's operand-stack space — no resizing needed at runtime.

### 4. Control flow is just jumps

There is no `if` opcode and no `while` opcode. High-level control flow compiles into **conditional and unconditional jumps** that modify the program counter.

`if (a < b) { X } else { Y }` becomes roughly:

```
        load a
        load b
        if_icmpge ELSE   ; if a >= b, jump to ELSE
        ... X ...
        goto END
ELSE:   ... Y ...
END:    ...
```

A `while` loop is a conditional branch at the top and an unconditional `goto` back to it. Short-circuit `a && b` compiles so that if `a` is false, you *jump past* the evaluation of `b` entirely — that's literally what "short-circuit" means at the bytecode level.

**WebAssembly is the exception that proves the rule.** Wasm has **structured control flow** — `block`, `loop`, `if`/`else`, `br`/`br_if` that can only branch to *enclosing* labels. There are no arbitrary `goto`s to numeric offsets. This restriction makes Wasm bytecode *much* faster to validate and compile (the control-flow structure is given, not reconstructed). We return to why this matters in `senior.md` and `professional.md`.

### 5. Backpatching: emitting a jump before you know the target

When a single-pass compiler emits a forward jump (`if a < b: goto ELSE`), it hits a problem: it doesn't yet know *where* `ELSE` is — it hasn't generated that code. **Backpatching** is the standard fix:

1. Emit the jump opcode with a **placeholder** offset (e.g. `0xFFFF` or `0`).
2. Remember the position of that placeholder.
3. Keep generating code.
4. When you finally reach the target, compute the real offset and **go back and overwrite** the placeholder.

```
emit  JUMP_IF_FALSE, 0xFFFF     ; placeholder
hole = position_of_placeholder
... emit the "then" branch ...
target = current_position
patch(hole, target - hole)      ; fill in the real (relative) offset
```

Backward jumps (loops) don't need backpatching — the target already exists when you emit the jump. Only *forward* jumps do. This is a small but essential technique; you'll implement it in the `tasks.md` capstone the moment you add `if` to your VM.

### 6. What's actually in a `.class` file

A `.class` file (one Java class) has a strict layout. From the front:

```
magic            0xCAFEBABE        ; identifies "this is a class file"
minor_version    u2
major_version    u2                ; e.g. 65 = Java 21
constant_pool_count u2
constant_pool[]                    ; strings, class/method/field refs, numbers
access_flags     u2                ; public/final/abstract...
this_class, super_class            ; indices into the constant pool
interfaces[]
fields[]
methods[]                          ; each method: name, descriptor, and a Code attribute
attributes[]
```

Each method's **Code attribute** contains `max_stack`, `max_locals`, the actual bytecode bytes, an exception table, and optional debug attributes (`LineNumberTable`, `LocalVariableTable`). The **constant pool** is the spine: almost everything is an *index* into it, including class names, method signatures, and string literals.

A **`.pyc`** file is simpler: a small header (magic number identifying the Python version, a bit-field of flags, a source hash or timestamp, source size) followed by a *marshalled* code object. That code object recursively contains the bytecode bytes, the constant tuple (`co_consts`), the local/var names, line-number info, and nested code objects for inner functions. `import marshal; marshal.loads(...)` can read it.

---

## Code Examples

### Example 1: See a forward jump and its offset (Python)

```python
import dis

def f(a, b):
    if a < b:
        return 1
    return 2

dis.dis(f)
```

Output (3.11-ish, annotated):

```
  LOAD_FAST                a
  LOAD_FAST                b
  COMPARE_OP               '<'
  POP_JUMP_FORWARD_IF_FALSE  to L1   ; conditional branch — jumps over the 'then'
  LOAD_CONST               1
  RETURN_VALUE
L1:
  LOAD_CONST               2
  RETURN_VALUE
```

The conditional branch carries the target as an operand. That target was *backpatched* by the compiler: when it emitted `POP_JUMP_FORWARD_IF_FALSE`, it didn't yet know where `L1` would land — it filled the offset in after generating the `then` branch.

### Example 2: A loop is a backward jump (Java)

```java
int sum(int n) {
    int s = 0;
    for (int i = 0; i < n; i++) s += i;
    return s;
}
```

`javap -c` (trimmed):

```
 0: iconst_0
 1: istore_2          // s = 0
 2: iconst_0
 3: istore_3          // i = 0
 4: iload_3
 5: iload_1
 6: if_icmpge 19      // if i >= n, exit loop  (forward jump)
 9: iload_2
10: iload_3
11: iadd
12: istore_2          // s += i
13: iinc 3, 1         // i++
16: goto 4            // back to the condition  (BACKWARD jump)
19: iload_2
20: ireturn
```

`goto 4` is the loop's back-edge. `if_icmpge 19` is the exit. Note `iinc` — a specialized "increment local in place" instruction, no operand stack involved. VMs add such specializations because `i++` is so common.

### Example 3: Inspect a `.pyc` header and code object

```python
import dis, marshal, importlib.util

# Compile some source to a code object
src = "def g(x): return x + 1\n"
code = compile(src, "<demo>", "exec")

# The bytecode bytes themselves:
print(code.co_consts)            # nested code object for g + constants
g_code = [c for c in code.co_consts if hasattr(c, "co_code")][0]
print("constants:", g_code.co_consts)   # (None, 1)
print("varnames:", g_code.co_varnames)  # ('x',)
print("raw bytes:", g_code.co_code.hex())
dis.dis(g_code)
```

You can see the constant pool (`co_consts`), the local names (`co_varnames`), and the raw bytecode bytes — the same things that get marshalled into a `.pyc`.

### Example 4: A stack VM with jumps (toy, with backpatching at compile time)

```python
PUSH, LOAD, STORE, LT, JMP_IF_FALSE, JMP, ADD, PRINT, HALT = range(9)

# Program: i=0; while i<3: print(i); i=i+1
# locals: i = slot 0
LOOP = 4
program = [
    PUSH, 0, STORE, 0,        # i = 0
    # LOOP (offset 4):
    LOAD, 0, PUSH, 3, LT,     # push (i < 3)
    JMP_IF_FALSE, 28,         # if false, jump to HALT (offset backpatched to 28)
    LOAD, 0, PRINT,           # print i
    LOAD, 0, PUSH, 1, ADD, STORE, 0,  # i = i + 1
    JMP, 4,                   # back to LOOP
    # offset 28:
    HALT,
]

def run(code):
    stack, locals_, pc = [], [0], 0
    while True:
        op = code[pc]; pc += 1
        if op == PUSH:  stack.append(code[pc]); pc += 1
        elif op == LOAD:  stack.append(locals_[code[pc]]); pc += 1
        elif op == STORE: locals_[code[pc]] = stack.pop(); pc += 1
        elif op == ADD:   b=stack.pop(); a=stack.pop(); stack.append(a+b)
        elif op == LT:    b=stack.pop(); a=stack.pop(); stack.append(a<b)
        elif op == JMP:   pc = code[pc]
        elif op == JMP_IF_FALSE:
            target = code[pc]; pc += 1
            if not stack.pop(): pc = target
        elif op == PRINT: print(locals_[0])
        elif op == HALT:  return

run(program)   # prints 0, 1, 2
```

This is the same shape as the junior VM, now with control flow. Notice the jump targets are *absolute offsets into `code`* — the kind of value backpatching fills in when you build a compiler for this VM (the capstone in `tasks.md`).

---

## Coding Patterns

### Pattern 1: Compute stack effects to validate your codegen

When emitting bytecode, track a running depth: `depth += pushes - pops` per instruction. If it ever goes negative, or differs between two paths that merge, your codegen is buggy. The maximum value is your `max_stack`.

### Pattern 2: Backpatch forward jumps; emit backward jumps directly

```python
def emit_jump(code, op):
    code.append(op); code.append(0xFFFF)   # placeholder
    return len(code) - 1                    # index of the hole

def patch_jump(code, hole):
    code[hole] = len(code)                  # fill with current position
```

This two-function pair is the whole technique. Use it for every `if`, `else`, and short-circuit operator.

### Pattern 3: Read disassembly by following the arrows

To understand a loop in someone else's bytecode: find the backward `goto`/`JMP` (the loop body boundary) and the conditional branch that exits it. Sketch the arrows. Control flow becomes a small graph.

---

## Best Practices

1. **Pick stack vs register on purpose.** Decide based on whether you'll JIT (register favors it), how much you care about interpreter speed (register), and how simple you need the compiler (stack). Don't cargo-cult.

2. **Keep the encoding regular.** Whatever width scheme you pick, be consistent — irregular encodings make both your decoder and any future JIT harder. Wasm and Lua's regularity is a feature.

3. **Store `max_stack` / `max_locals`.** Pre-sizing frames avoids runtime resizing and lets a verifier check stack balance cheaply.

4. **Always backpatch — never guess offsets.** Hand-computing forward offsets is bug-prone. Emit a placeholder and patch.

5. **Put a magic number and a version in your format.** Even a toy format benefits from a 4-byte magic and a version byte: it turns "mysterious crash on garbage input" into "clean 'not my format / wrong version' error."

---

## Edge Cases & Pitfalls

- **Stack imbalance across branches.** If your `then` branch leaves one extra value on the stack and your `else` doesn't, the merge point has an ambiguous stack height. Real VMs reject this; your toy VM will silently corrupt. Track depth on *both* paths.

- **Relative vs absolute jump offsets.** The JVM uses offsets *relative to the branch instruction's own address*; CPython has used both relative and absolute over versions. Mixing them up produces jumps that land in the middle of an instruction.

- **Jumping into the middle of an instruction.** In a variable-width encoding, a wrong offset can land mid-instruction, and the VM will decode garbage. Fixed-width VMs (Lua) are immune to *this* particular bug.

- **`EXTENDED_ARG` in CPython.** Arguments larger than 255 are prefixed with one or more `EXTENDED_ARG` instructions that supply the high bytes. Naively reading 2 bytes per instruction without handling this corrupts large operands (long jumps, big constant indices).

- **Constant-pool index 0 is special in the JVM.** Pool indices are 1-based; entry 0 is reserved. Off-by-one here is a classic bug when writing a class-file parser.

- **`long`/`double` take two JVM stack slots.** They occupy two operand-stack and two local-variable slots. Forgetting this throws off all your slot arithmetic.

---

## Common Mistakes

1. **Assuming register VMs are always faster.** They reduce dispatch but complicate codegen and don't help once a good JIT exists (the JVM is stack-based and screamingly fast). "Faster" depends on *interpreter vs JIT* and on the workload.

2. **Treating the operand stack and call stack as the same thing.** Each call frame contains its *own* operand stack. Confusing them makes disassembly incomprehensible.

3. **Hand-computing jump offsets.** Always backpatch.

4. **Reading a `.pyc` as if the first bytes were bytecode.** They're a header (magic, flags, hash/timestamp, size). The bytecode is inside the marshalled code object.

5. **Thinking `if`/`while` have dedicated opcodes.** They compile to branches. (Except Wasm's structured control flow — and even there, branches target *labels*, not raw offsets.)

---

## Apply it

1. Find a real component where **Bytecode & Virtual Machines** affects an interface or dependency.
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

- Which boundary is most affected by Bytecode & Virtual Machines?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
