# Interpreters — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Interpreters** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The two-phase architecture: compile, then run

A bytecode interpreter splits execution into two phases:

```text
  Phase 1 (once):   AST  ──[compiler]──►  bytecode + constant pool
  Phase 2 (run):    bytecode  ──[VM loop]──►  result
```

The compiler walks the AST *once* and emits a flat instruction list. The VM then runs that list — possibly many times (e.g. a function called in a loop) — without ever touching the tree again. All the per-node dispatch and name resolution that the tree-walker repeated on every execution is done **once, up front**.

### 2. Bytecode is a flat array of small instructions

Where the tree-walker had `BinOp("+", Number(2), BinOp("*", Number(3), Number(4)))`, the bytecode compiler emits a *linear* sequence. For a **stack-based VM**, `2 + 3 * 4` compiles to:

```text
  CONST  0      # push constant[0] = 2
  CONST  1      # push constant[1] = 3
  CONST  2      # push constant[2] = 4
  MUL           # pop 4, pop 3, push 12
  ADD           # pop 12, pop 2, push 14
```

Notice this is **post-order traversal flattened**: operands are pushed, then the operator pops them and pushes the result. The tree's shape became an instruction order. The constants `2, 3, 4` live in a **constant pool**; the bytecode refers to them by index, not by re-parsing.

### 3. The operand stack does the bookkeeping

In a stack-based VM, intermediate values live on an **operand stack**. Each instruction has a known effect on the stack:

| Opcode | Effect on stack |
|--------|-----------------|
| `CONST i` | push `constant_pool[i]` |
| `ADD` | pop b, pop a, push (a + b) |
| `MUL` | pop b, pop a, push (a * b) |
| `LOAD_LOCAL s` | push `locals[s]` |
| `STORE_LOCAL s` | pop value, store into `locals[s]` |
| `PRINT` | pop value, print it |

The stack is why bytecode can be flat: it remembers "the values computed so far" without needing a tree to hold them. After running the five instructions above, the stack holds a single value, `14` — the result.

### 4. The fetch–decode–execute loop

The VM is one loop. It keeps an **instruction pointer** (IP) into the bytecode and repeats:

```text
  loop:
    opcode = bytecode[IP]      # FETCH
    IP += 1
    switch (opcode):           # DECODE
      case CONST:   push(constants[bytecode[IP]]); IP += 1     # EXECUTE
      case ADD:     b = pop(); a = pop(); push(a + b)
      case MUL:     b = pop(); a = pop(); push(a * b)
      case JUMP:    IP = bytecode[IP]
      case HALT:    return pop()
      ...
```

That is the entire engine. CPython's `ceval.c`, Lua's `lvm.c`, and the JVM's interpreter are all elaborations of this loop. The naive version uses a `switch`; `senior.md` shows the faster dispatch techniques (computed goto, threaded code) that replace it.

### 5. Why locals are an array, not a dictionary

This is the single most important performance idea on this page. In the tree-walker, a variable read was `env["x"]` — a **hash of the string `"x"`, then a lookup**. That is expensive and happens on *every* access.

A bytecode compiler does better. While compiling a function, it knows *all* the local variable names. It assigns each one an integer **slot**: `x → 0`, `y → 1`, `z → 2`. Then `x` compiles to `LOAD_LOCAL 0`, which at runtime is just `push(locals[0])` — a single array index, no hashing, no string comparison.

```text
  Tree-walker:   read x  ->  hash "x"  ->  probe hashmap  ->  value   (slow)
  Bytecode VM:   read x  ->  LOAD_LOCAL 0  ->  locals[0]   ->  value   (fast)
```

This is exactly why, in CPython, **local variables are faster than global variables**: locals use `LOAD_FAST` (an array index), while globals use `LOAD_GLOBAL` (a dictionary lookup). The name resolution moved from *runtime* to *compile time*. This is one of the highest-leverage tricks in interpreter design.

### 6. Control flow becomes jumps

The tree-walker implemented `if`/`while` with the host's own `if`/`while`. The bytecode VM has no tree, so it uses **jumps** that move the IP. An `if` compiles to a conditional jump that skips the unwanted branch:

```text
  if cond { A } else { B }

  <compile cond>          # leaves a boolean on the stack
  JUMP_IF_FALSE  L_else    # if top is false, jump to else
  <compile A>
  JUMP           L_end
L_else:
  <compile B>
L_end:
  ...
```

A `while` is a backward jump:

```text
L_start:
  <compile cond>
  JUMP_IF_FALSE  L_end
  <compile body>
  JUMP           L_start    # loop back
L_end:
```

The compiler emits placeholder jump targets and **patches** them once the target offset is known (called *backpatching*). This is how every loop and branch in a bytecode language is implemented.

### 7. Stack-based vs register-based VMs

There are two main bytecode styles:

- **Stack-based** (CPython, JVM, Ruby YARV, WebAssembly): operands live on an operand stack. Instructions are small and have few/no operands (`ADD` takes its inputs from the stack). Easy to generate; more instructions executed per operation (lots of push/pop).
- **Register-based** (Lua 5+, Dalvik, Android's old VM): operands live in numbered virtual registers. Instructions name their operands (`ADD r3, r1, r2` means `r3 = r1 + r2`). Fewer, fatter instructions; less push/pop traffic; harder to generate but often faster.

Lua 5's switch to a register-based VM is a famous reason for its renowned speed: `a = b + c` is one `ADD` instruction reading two registers and writing one, instead of `LOAD b; LOAD c; ADD; STORE a` (four instructions) on a stack machine. We explore the trade-offs further in `senior.md`; the deep treatment of bytecode design lives in the eval-and-execution material elsewhere in this roadmap.

### 8. Disassembly: reading the bytecode you produced

Every serious bytecode VM ships a **disassembler** so humans can inspect the compiled form. Python's is built in:

```python
import dis
def f(x):
    return x + 1
dis.dis(f)
#   LOAD_FAST   0 (x)
#   LOAD_CONST  1 (1)
#   BINARY_ADD
#   RETURN_VALUE
```

`LOAD_FAST 0` is exactly the locals-array access from concept 5. Writing a disassembler for your own VM is the best debugging tool you can build — it turns an opaque byte array back into readable instructions.

---

## Code Examples

We will build a complete **compiler + stack-based VM** for the same calculator-with-variables language from `junior.md`. The compiler turns an AST into bytecode; the VM runs it.

### Python — bytecode compiler and VM

```python
# ---------- Opcodes ----------
CONST       = 0   # operand: index into constant pool;  push constants[i]
LOAD_LOCAL  = 1   # operand: slot;                       push locals[slot]
STORE_LOCAL = 2   # operand: slot;                       locals[slot] = pop()
ADD         = 3
SUB         = 4
MUL         = 5
DIV         = 6
PRINT       = 7
JUMP        = 8   # operand: target IP
JUMP_IF_FALSE = 9 # operand: target IP;  pops condition
HALT        = 10

# ---------- AST (same shapes as junior.md) ----------
class Num:
    def __init__(self, v): self.v = v
class Var:
    def __init__(self, name): self.name = name
class BinOp:
    def __init__(self, op, l, r): self.op, self.l, self.r = op, l, r
class Assign:
    def __init__(self, name, expr): self.name, self.expr = name, expr
class Print:
    def __init__(self, expr): self.expr = expr

# ---------- Compiler: AST -> bytecode ----------
class Compiler:
    def __init__(self):
        self.code = []         # flat list of ints (opcodes + operands)
        self.constants = []    # constant pool
        self.slots = {}        # name -> integer slot  (resolved at compile time!)

    def const_index(self, value):
        if value in self.constants:
            return self.constants.index(value)
        self.constants.append(value)
        return len(self.constants) - 1

    def slot_for(self, name):
        if name not in self.slots:
            self.slots[name] = len(self.slots)   # assign next slot
        return self.slots[name]

    def emit(self, *bytes_):
        self.code.extend(bytes_)

    def compile_expr(self, node):
        if isinstance(node, Num):
            self.emit(CONST, self.const_index(node.v))
        elif isinstance(node, Var):
            self.emit(LOAD_LOCAL, self.slot_for(node.name))
        elif isinstance(node, BinOp):
            self.compile_expr(node.l)        # children first (post-order)
            self.compile_expr(node.r)
            self.emit({'+': ADD, '-': SUB, '*': MUL, '/': DIV}[node.op])
        else:
            raise TypeError(f"cannot compile expr {node}")

    def compile_stmt(self, node):
        if isinstance(node, Assign):
            self.compile_expr(node.expr)
            self.emit(STORE_LOCAL, self.slot_for(node.name))
        elif isinstance(node, Print):
            self.compile_expr(node.expr)
            self.emit(PRINT)
        else:
            raise TypeError(f"cannot compile stmt {node}")

    def compile_program(self, statements):
        for s in statements:
            self.compile_stmt(s)
        self.emit(HALT)
        return self.code, self.constants, len(self.slots)

# ---------- VM: run the bytecode ----------
def run(code, constants, num_slots):
    stack = []
    locals_ = [None] * num_slots
    ip = 0
    while True:
        op = code[ip]; ip += 1                 # FETCH
        if op == CONST:                         # DECODE + EXECUTE
            stack.append(constants[code[ip]]); ip += 1
        elif op == LOAD_LOCAL:
            stack.append(locals_[code[ip]]); ip += 1
        elif op == STORE_LOCAL:
            locals_[code[ip]] = stack.pop(); ip += 1
        elif op == ADD:
            b = stack.pop(); a = stack.pop(); stack.append(a + b)
        elif op == SUB:
            b = stack.pop(); a = stack.pop(); stack.append(a - b)
        elif op == MUL:
            b = stack.pop(); a = stack.pop(); stack.append(a * b)
        elif op == DIV:
            b = stack.pop(); a = stack.pop()
            if b == 0: raise ZeroDivisionError("division by zero")
            stack.append(a / b)
        elif op == PRINT:
            print(stack.pop())
        elif op == JUMP:
            ip = code[ip]
        elif op == JUMP_IF_FALSE:
            target = code[ip]; ip += 1
            if not stack.pop():
                ip = target
        elif op == HALT:
            return
        else:
            raise RuntimeError(f"bad opcode {op}")

# ---------- Run: x = 2 + 3 * 4; print(x) ----------
program = [
    Assign("x", BinOp('+', Num(2), BinOp('*', Num(3), Num(4)))),
    Print(Var("x")),
]
code, constants, nslots = Compiler().compile_program(program)
run(code, constants, nslots)   # prints: 14
```

The variable `x` was resolved to slot `0` at compile time. At runtime, `LOAD_LOCAL 0` is a bare array index — no string, no hash. That is the whole point.

### Disassembling our own bytecode

A disassembler makes the byte array readable — invaluable for debugging:

```python
NAMES = {0:"CONST",1:"LOAD_LOCAL",2:"STORE_LOCAL",3:"ADD",4:"SUB",
         5:"MUL",6:"DIV",7:"PRINT",8:"JUMP",9:"JUMP_IF_FALSE",10:"HALT"}
HAS_OPERAND = {0,1,2,8,9}

def disassemble(code):
    ip = 0
    while ip < len(code):
        op = code[ip]
        if op in HAS_OPERAND:
            print(f"{ip:4} {NAMES[op]:14} {code[ip+1]}")
            ip += 2
        else:
            print(f"{ip:4} {NAMES[op]}")
            ip += 1

# For x = 2 + 3 * 4; print(x):
#   0 CONST          0
#   2 CONST          1
#   4 CONST          2
#   6 MUL
#   7 ADD
#   8 STORE_LOCAL    0
#  10 LOAD_LOCAL     0
#  12 PRINT
#  13 HALT
```

### Compiling control flow with backpatching

`if`/`while` need jumps whose targets are not known until later. The compiler emits a placeholder, remembers its position, then patches it:

```python
def compile_while(self, cond, body):
    loop_start = len(self.code)
    self.compile_expr(cond)
    self.emit(JUMP_IF_FALSE, 0)        # placeholder target
    exit_patch = len(self.code) - 1    # remember where the operand is
    for s in body:
        self.compile_stmt(s)
    self.emit(JUMP, loop_start)        # jump back to re-test condition
    self.code[exit_patch] = len(self.code)   # backpatch the exit target
```

This is exactly how real compilers emit loops: forward jumps are patched once the destination is reached.

### A register-style instruction, for contrast

To see the stack-vs-register difference, here is how `x = b + c` looks in each style:

```text
  Stack-based (CPython-like):        Register-based (Lua-like):
    LOAD_LOCAL  1   (b)                ADD  r0, r1, r2   ; r0 = r1 + r2
    LOAD_LOCAL  2   (c)                                  ; (x in r0, b in r1, c in r2)
    ADD
    STORE_LOCAL 0   (x)
```

The register VM does it in **one** instruction instead of four, with no push/pop traffic — at the cost of a more complex compiler that must allocate registers. This is a core reason Lua is so fast.

---

## Coding Patterns

### Pattern 1: Two-pass shape — compile to bytecode, then loop

Keep the compiler (AST → bytecode) and the VM (bytecode → result) cleanly separated. The compiler is recursive and post-order; the VM is one flat loop. Do not interleave them.

### Pattern 2: Constant pool with deduplication

Store literals once in a pool and reference by index. Deduplicate so `2 + 2` reuses one entry. Bytecode carries small integer indices, not big values.

```python
def const_index(self, value):
    if value in self.constants: return self.constants.index(value)
    self.constants.append(value); return len(self.constants) - 1
```

### Pattern 3: Resolve names to slots at compile time

Walk the function once, assign each local an integer slot, and compile reads/writes to `LOAD_LOCAL slot` / `STORE_LOCAL slot`. Never hash a variable name at runtime in the hot path.

### Pattern 4: Emit-placeholder-then-backpatch for jumps

For forward branches, emit the jump with a dummy target, record the operand's position, and overwrite it once you know the destination. This is the standard way to compile `if`, `while`, `break`, and `&&`/`||`.

### Pattern 5: A `case` per opcode, smallest possible bodies

Keep each opcode's handler tiny and side-effect-focused. The smaller and more uniform the cases, the better the loop performs and the easier `senior.md`'s computed-goto rewrite becomes.

### Pattern 6: Build the disassembler alongside the compiler

A disassembler is your eyes inside the VM. Write it early; it makes every "why is my output wrong?" question a five-second read of the instruction stream.

---

## Best Practices

- **Keep the operand stack discipline exact.** Every opcode must leave the stack at the height its compiler assumed. A push/pop imbalance is the most common VM bug; assert stack depth in debug builds.
- **Resolve everything you can at compile time.** Slots, constant indices, jump targets — anything moved out of the loop is a permanent win on every iteration.
- **Make `HALT`/return explicit.** End every code stream with a terminating opcode so the loop has a defined exit, rather than running off the end of the array.
- **Validate opcodes in debug, trust them in release.** A `default: error` case catches compiler bugs during development; you can drop the check in optimized builds.
- **Cache compiled bytecode** if compilation is non-trivial and programs run repeatedly (Python's `__pycache__` is the model).
- **Test the compiler and VM separately.** Snapshot-test the bytecode the compiler emits, and unit-test the VM on hand-written bytecode. Bugs localize instantly.
- **Measure before micro-optimizing the loop.** The big win is *being* a bytecode VM at all; exotic dispatch (`senior.md`) is a second-order gain — profile first.

---

## Edge Cases & Pitfalls

- **Stack imbalance.** If an opcode pops the wrong number of values, or a branch skips a push, the stack drifts and later instructions read garbage. Track expected stack depth per instruction.
- **Jump targets off by one.** Forgetting that the operand follows the opcode (so the next instruction is at `ip+2`, not `ip+1`) corrupts all your jump math. Be precise about operand widths.
- **Forgetting to backpatch.** A placeholder jump target left as `0` sends control to the start of the program. Always patch before finishing compilation.
- **Sharing one constant pool index for different values.** Deduplication must compare values correctly; using `==` where you need identity (or vice versa) merges or splits constants wrongly.
- **Slot collisions across scopes.** A naive slot allocator that reuses indices across nested blocks/functions corrupts variables. Each function frame needs its own locals array (closures/upvalues are `senior.md`).
- **Integer vs float operand confusion in the loop.** Reading an operand byte as a value, or a value as an operand, produces wild results. Keep a clear map of which opcodes have operands.
- **Running off the end of the bytecode.** Without a terminating `HALT`/`RETURN`, the IP increments past the array and crashes (or worse, reads stale memory in a low-level VM).
- **Tail of a `JUMP_IF_FALSE` mispredicted.** Conditional jumps are where branch prediction hurts; this is *correct* but slow, and is exactly what `senior.md`'s dispatch techniques attack.

---

## Apply it

1. Find a real component where **Interpreters** affects an interface or dependency.
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

- Which boundary is most affected by Interpreters?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
