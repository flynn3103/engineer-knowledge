# Code Generation — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Code Generation** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The Back End's Starting Point and Goal

By the time code generation begins, the optimizer has produced IR that is *correct and reasonably efficient* but *still abstract*. A line of IR might read:

```text
%t3 = mul %t1, 4
%t4 = add %base, %t3
%v  = load %t4
```

This says: multiply `%t1` by 4, add the result to `%base`, treat that as an address, and load the value there. Notice the value names: `%t1`, `%t3`, `%v`. These are **virtual registers** — there could be thousands of them in a function. The IR assumes that's fine.

The goal of code generation is to turn this into real instructions for, say, x86-64:

```asm
    lea  rax, [rbx + rsi*4]   ; rax = base + t1*4, in ONE instruction
    mov  rcx, [rax]           ; load
```

Two instructions, two physical registers. Notice what happened: three IR operations (`mul`, `add`, `load`) collapsed differently than you'd expect — the multiply and the add fused into a single `lea`, because x86 has an addressing mode that does exactly that. That fusing is **instruction selection** at work.

### 2. Sub-Problem One: Instruction Selection

Instruction selection answers: *for each piece of the IR, which target instruction (or combination) implements it?*

The naive approach is one-IR-op-to-one-instruction: emit a multiply, then an add, then a load. That works and is correct. But real CPUs offer instructions that do *more than one IR operation at once*:

- x86's `lea rax, [rbx + rsi*4]` does a multiply-by-constant and an add in one instruction.
- A **fused multiply-add (FMA)** does `a*b + c` in one instruction on most modern chips.
- An addressing mode like `mov rax, [rbx + rcx + 8]` folds an add and an offset into the load itself.

A good selector spots these patterns. It treats the IR as a little tree and tries to **cover** that tree with the largest, cheapest instruction tiles available. This is why selection differs so much between CISC and RISC: on x86 (CISC) there are huge tiles to find (`lea`, complex addressing); on RISC-V there are mostly small, uniform tiles, so selection is simpler but you emit more instructions.

The junior takeaway: **one IR operation does not equal one machine instruction.** The selector may merge several, or split one into several.

### 3. Sub-Problem Two: Register Allocation

Register allocation answers: *the IR used thousands of virtual registers; the CPU has ~16. Who gets a real register?*

Values that are in registers are fast. Values that don't fit must be **spilled** — written out to the stack and reloaded when needed. Spilling is correct but slow: every spilled value costs a store and one or more loads, hitting memory instead of staying in the chip.

The allocator's job is to keep the *most-used* values in registers and spill the rest, while never assigning the same register to two values that are alive at the same time. Two values are "alive at the same time" if both will be read later — you can't put both in `rax`, or one would clobber the other.

When you see assembly that constantly writes values to `[rsp + N]` and reads them back, you are looking at **spill code** — the allocator ran out of registers. Reducing register pressure (e.g. by breaking a giant function into smaller ones) is a real, practical optimization.

The junior takeaway: **registers are scarce. The allocator is rationing them, and the leftovers go to the stack.**

### 4. Sub-Problem Three: Instruction Scheduling

Instruction scheduling answers: *given the instructions, what order should they be emitted in?*

Even after selection and allocation, order matters because of how CPUs execute. A `load` from memory takes several cycles to complete. If the very next instruction needs that loaded value, the CPU **stalls** — it waits, doing nothing. But if you can slip an *independent* instruction in between, the CPU does useful work while the load completes.

So the scheduler reorders instructions (without changing the program's meaning) to **hide latency**. It can only reorder things that don't depend on each other; you can't move an instruction before the one that produces its input.

On modern desktop and server CPUs (which reorder instructions themselves, "out-of-order execution"), the compiler's scheduling matters *less* than it used to — the hardware fixes a lot of it. But it still matters for in-order cores (many embedded chips, some phones), and even big cores care about things like keeping the load far from its use.

The junior takeaway: **the order of instructions is a third lever, used to keep the CPU from stalling while it waits for data.**

### 5. These Three Fight Each Other

The three sub-problems are not independent — they interact, and that's a major theme you'll meet again at higher levels. The clearest tension: **scheduling wants to spread independent work out so the CPU stays busy, but spreading work out means more values are "alive" at once, which needs more registers.** More parallelism costs more registers. Register allocation and scheduling pull in opposite directions, and back ends have to balance them. This is called the **phase-ordering problem** — there's no perfect order to run these passes in.

### 6. Calling Conventions: Lowering to the ABI

There's a fourth job woven through code generation: obeying the **calling convention** (part of the **ABI**, the Application Binary Interface). When your function calls another, both sides must agree on *where the arguments go* (which registers, what stack layout) and *where the return value comes back*. They must also agree on which registers a called function is allowed to clobber.

So the back end must:

- Put outgoing arguments in the right registers/stack slots before a call.
- Read the return value from the agreed register.
- Emit a **prologue** that sets up the stack frame and a **epilogue** that tears it down.
- Save and restore any **callee-saved** registers the function uses.

This is why every compiled function has that boilerplate `push`/`mov rbp, rsp` at the top and `pop`/`ret` at the bottom. (The detailed register rules connect to how foreign-function interfaces work across languages, which is covered in the FFI section of this roadmap.)

### 7. Emitting Assembly vs Machine Code, and the Handoff

Finally, the back end has to *produce output*. Two common forms:

- **Emit assembly text** (`-S` gives you this), then hand it to a separate **assembler** which turns it into machine-code bytes.
- **Emit machine code directly** (an integrated assembler), which most modern compilers do for speed.

Either way, the output isn't quite a finished program. References to other functions and global data aren't final addresses yet — they're left as **relocations**, placeholders the **linker** fills in later when it knows where everything lives in memory. (This linker/loader handoff is its own large topic.) A **peephole** pass often runs at the very end, scanning short windows of the final instructions to clean up silly sequences (a `mov` into a register that's immediately overwritten, two adds that could be one).

---

## Code Examples

The best way to learn the back end is to *look at its output*. You don't need to write a compiler; you need to read what one produces. Every example below is something you can run on your own machine.

### Seeing the Three Sub-Problems at Once

Take a trivial C function and ask the compiler for assembly with `-S`:

```c
// add.c
int add_scaled(int *base, int i) {
    return base[i] + 7;
}
```

```bash
gcc -O2 -S add.c -o add.s     # x86-64 assembly into add.s
```

The interesting part of `add.s` on x86-64 looks roughly like:

```asm
add_scaled:
    movslq  esi, rsi          ; sign-extend i to 64 bits
    mov     eax, [rdi + rsi*4]; load base[i] using an addressing mode
    add     eax, 7            ; + 7
    ret
```

Read it through the three-decisions lens:

- **Selection:** `base[i]` became a single `mov eax, [rdi + rsi*4]`. The multiply-by-4 (because `int` is 4 bytes) and the add-to-base were *folded into the load's addressing mode*. Three IR-ish operations, one instruction.
- **Allocation:** the arguments arrived in `rdi` (base) and `esi` (i) per the ABI; the result went into `eax` (where the ABI says return values go). No spilling — only a couple of values are alive.
- **Scheduling:** trivial here; too few instructions to reorder.

### Watching `lea` Get Picked

```c
// lea.c
long mul_add(long a, long b) {
    return a * 4 + b;        // a multiply-by-constant and an add
}
```

```bash
gcc -O2 -S lea.c -o lea.s
```

On x86-64 you'll see:

```asm
mul_add:
    lea     rax, [rsi + rdi*4]   ; rax = b + a*4, in ONE instruction
    ret
```

The selector recognized "multiply a value by a small power-of-two constant and add another value" as *exactly* what `lea` does and emitted one instruction instead of a `shl`/`imul` plus an `add`. This is the textbook example of instruction selection finding a big tile.

### Forcing a Spill (Register Pressure)

```c
// spill.c — too many live values at once
long pressure(long a, long b, long c, long d, long e, long f,
              long g, long h, long i, long j) {
    long s1 = a + b, s2 = c + d, s3 = e + f, s4 = g + h, s5 = i + j;
    // use every partial sum so none can be discarded:
    return s1*s2 + s3*s4 + s5 + a*b + c*d + e*f + g*h + i*j;
}
```

```bash
gcc -O2 -S spill.c -o spill.s
```

Among the arithmetic you'll see lines like `mov [rsp + 8], rax` (store to stack) and `mov rax, [rsp + 8]` (reload). Those are **spills**: the function has more values alive at once than there are registers, so the allocator parked some on the stack. The same logic written with fewer simultaneously-live values would have no spills.

### Comparing Two Targets

The same C source, two architectures, shows how selection and the instruction set differ:

```bash
# x86-64 (CISC)
gcc -O2 -S lea.c -o lea_x86.s
# AArch64 (RISC) — using a cross-compiler
aarch64-linux-gnu-gcc -O2 -S lea.c -o lea_arm.s
```

The AArch64 version can't fold the multiply into an address the same way; you'll typically see something like a shift-and-add:

```asm
mul_add:                       ; AArch64
    add     x0, x1, x0, lsl 2  ; x0 = b + (a << 2)
    ret
```

ARM still does it in one instruction — but via its own *shifted-register* operand form, not x86's `lea`. Different instruction set, same idea, different spelling. This is exactly why `-O2` output differs across architectures.

### Looking at the Prologue/Epilogue (the ABI)

```c
// frame.c
long uses_stack(long n) {
    long arr[4] = {n, n+1, n+2, n+3};
    long total = 0;
    for (int k = 0; k < 4; k++) total += arr[k];
    return total;
}
```

```bash
gcc -O0 -S frame.c -o frame.s    # -O0 keeps the frame obvious
```

At the top you'll see the **prologue** (`push rbp; mov rbp, rsp; sub rsp, N` — claim a stack frame) and at the bottom the **epilogue** (`leave; ret` or `mov rsp, rbp; pop rbp; ret`). That boilerplate is the calling convention being honored. With `-O2` the compiler often omits the frame pointer entirely as an optimization, which is why `-O0` is better for *seeing* the structure.

### Using a Disassembler Instead of `-S`

You can also compile to an object file and disassemble the real machine-code bytes:

```bash
gcc -O2 -c lea.c -o lea.o
objdump -d lea.o            # shows bytes + decoded instructions
```

`objdump` shows the actual encoded bytes next to the instructions — useful when you want to see *how long* an instruction is (x86 instructions vary from 1 to 15 bytes; RISC instructions are fixed at 4). This is the closest you get to "what the CPU actually sees."

---

## Coding Patterns

These are *practical habits* for working with generated code, not algorithms (those are in `middle.md`).

### Pattern 1: Always Look at `-O2`, Learn from `-O0`

```bash
gcc -O0 -S file.c -o file_O0.s   # readable, maps to source — for LEARNING
gcc -O2 -S file.c -o file_O2.s   # what actually ships — for PERFORMANCE
```

Diff them. The differences *are* the back end's optimizations made visible.

### Pattern 2: Reduce Register Pressure in Hot Code

If you see spill code in a hot loop, you have too many values alive at once. Practical fixes: split a giant function into smaller ones (each gets its own register budget), reduce the number of variables that must persist across the loop, or recompute a cheap value instead of holding it in a register.

### Pattern 3: Let the Compiler Pick the Smart Instruction

Write the *clear* version and trust selection. `x * 8` is fine — the compiler turns it into a shift or folds it into a `lea`; you don't need to write `x << 3` yourself. Premature micro-rewriting often *defeats* the selector by hiding the pattern it was looking for.

### Pattern 4: Use the Compiler Explorer Mentally

When you wonder "what does this compile to?", form the habit of actually checking: a local `-S` or an online assembly explorer. Over time you build intuition for which source shapes produce clean code.

### Pattern 5: Trust the ABI, Don't Fight It

When calling across a language boundary or into hand-written assembly, follow the documented calling convention exactly — argument registers, return register, callee-saved set. The back end already does this for you; problems arise only when *you* hand-write the other side.

---

## Best Practices

- **Read generated code with the three-decisions lens.** For any surprising line, ask: is this *selection* (which instruction), *allocation* (why on the stack?), or *scheduling* (why in this order?)?
- **Use `-O0` to understand structure, `-O2` to understand performance.** Don't try to learn the *shape* of compilation from optimized output — it's been rearranged.
- **Recognize spill code on sight.** Repeated `mov [rsp+N], reg` / `mov reg, [rsp+N]` pairs around the same offset mean register pressure. That's a tuning signal.
- **Don't micro-optimize what the back end already does.** Shifts-for-multiplies, `lea` fusion, constant folding, FMA — the compiler does these. Write clearly and verify.
- **When measuring, measure; when reading codegen, read codegen.** Assembly tells you *what* the CPU runs; a profiler tells you *where time goes*. Use both, for their own jobs.
- **Know your target.** x86-64 desktop code, AArch64 phone code, and RISC-V embedded code look different for real reasons. Don't expect identical assembly across architectures.
- **Prefer `objdump -d` when you care about real bytes and instruction lengths;** prefer `-S` when you want clean, labeled, source-adjacent assembly.

---

## Edge Cases & Pitfalls

- **"One IR op = one instruction" is wrong.** The selector merges (`lea`, FMA, folded loads) and splits (a 64-bit op on a 32-bit target becomes several instructions). Don't count source operations and expect a matching instruction count.
- **The GIL of register count: more locals isn't free.** Adding "just one more" variable that's alive across a loop can tip the allocator into spilling, suddenly making a hot loop slower. The cost cliff is invisible in the source.
- **`-O2` output doesn't line up with source lines.** Scheduling reorders instructions, allocation hides variables in registers, and inlining mixes functions together. Debugging optimized code is genuinely harder — that's why debug builds exist.
- **The frame pointer may be gone.** At `-O2`, compilers often omit `rbp` setup to free a register. Stack traces then rely on unwind tables, not a frame-pointer chain. Don't assume every function has a classic prologue.
- **Assembly is not the final program.** `call printf` contains a *placeholder* address until the linker resolves it. Reading object-file assembly and expecting final addresses will confuse you.
- **Hand-written assembly that ignores the ABI corrupts silently.** If you clobber a callee-saved register without restoring it, the caller breaks much later, far from the cause. The back end never makes this mistake; humans writing inline assembly do.
- **Scheduling matters less than you'd think on a big desktop CPU.** Out-of-order execution reorders at runtime, so the compiler's careful schedule is partly redundant there — but it's crucial on in-order embedded cores. Don't generalize from your laptop to a microcontroller.
- **Different optimization levels can expose latent bugs.** Code that relies on undefined behavior may "work" at `-O0` and break at `-O2` because the optimizer and back end are allowed to assume the UB never happens. The back end isn't buggy; the source is.
- **Constant power-of-two multiplies look like shifts in the output.** Don't be alarmed that `x * 8` shows up as `shl` or inside a `lea` scale — that *is* the multiply. It's not a compiler error; it's selection doing its job.
- **WebAssembly "code generation" looks nothing like x86.** Wasm is a stack machine with structured control flow, so a back end targeting it emits push/pop-style stack operations and structured blocks, not register instructions. "Codegen" is target-shaped; don't expect register allocation to look the same there.

---

## Apply it

1. Choose one small, known input for **Code Generation**.
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

- What problem does Code Generation solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
