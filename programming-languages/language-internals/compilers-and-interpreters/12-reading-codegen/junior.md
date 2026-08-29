# Reading Codegen (Disassembly & Compiler Output) — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Reading Codegen (Disassembly & Compiler Output)** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The compiler produces text you can read

When you compile, the compiler runs your source through several stages and ends with **machine code** — bytes the CPU runs directly. Those bytes have a readable text spelling called **assembly**. You have two ways to see it:

1. **Ask the compiler to stop one step early** and print assembly instead of finishing the binary: `gcc -S file.c` produces `file.s`, a text file of assembly.
2. **Disassemble a finished binary** — take the compiled `.o` or executable and convert the bytes back to assembly: `objdump -d a.out`.

Both give you the same thing to read. The first is easier when you have the source; the second is what you use when you only have a binary.

### 2. Assembly is just a list of tiny operations

Each line of assembly is roughly one CPU instruction. They are *much* simpler than source code. There is no `for` loop instruction — a loop is built from a *compare*, a *jump*, and a *label*. There is no `a + b * c` — it's separate `mul` and `add` instructions. Reading assembly is mostly recognizing these small patterns. Here is a function that adds two numbers, on x86-64 (Intel syntax):

```asm
add_two:
        lea     eax, [rdi + rsi]   ; eax = first_arg + second_arg
        ret                        ; return (the result is in eax)
```

Three things to notice already:
- `rdi` and `rsi` are where the **first two arguments** arrive (the calling convention puts them there).
- The **return value** goes in `eax`/`rax`.
- `lea` here is being used as a sneaky "add two registers" — more on that later.

### 3. Registers: the CPU's tiny scratchpad

The CPU does almost all its work in **registers** — 16 general-purpose slots on x86-64. Their full 64-bit names are `rax`, `rbx`, `rcx`, `rdx`, `rsi`, `rdi`, `rbp`, `rsp`, and `r8` through `r15`. The same register has smaller names for its lower bits:

| 64-bit | 32-bit | 16-bit | 8-bit |
|--------|--------|--------|-------|
| `rax`  | `eax`  | `ax`   | `al`  |
| `rbx`  | `ebx`  | `bx`   | `bl`  |
| `rcx`  | `ecx`  | `cx`   | `cl`  |
| `rdi`  | `edi`  | `di`   | `dil` |

So `eax` and `rax` are the *same register* — `eax` just means "the bottom 32 bits of `rax`." Beginners get confused seeing `mov eax, 5` and `mov rax, ...` in the same function; it's one register being used at different widths. A special register, `rsp`, is the **stack pointer** (it points at the call stack); you'll see it constantly in the prologue/epilogue.

### 4. The dozen instructions you actually need

You do not need thousands of instructions. For everyday reading, these cover 90% of what you'll see:

| Instruction | What it does |
|-------------|--------------|
| `mov dst, src` | Copy `src` into `dst`. The workhorse. |
| `lea dst, [addr]` | "Load effective address" — compute an address (or, sneakily, do arithmetic) without touching memory. |
| `add` / `sub` | Add / subtract. |
| `imul` / `mul` | Multiply. |
| `cmp a, b` | Compare (subtract without storing) and set *flags*. |
| `test a, b` | Bitwise AND without storing; sets flags. Often `test rax, rax` = "is rax zero?" |
| `jmp` / `je` / `jne` / `jl` / `jg` | Jump always / jump if equal / not-equal / less / greater (based on the last `cmp`). |
| `call` / `ret` | Call a function / return from one. |
| `push` / `pop` | Put a register on the stack / take it off. |
| `xor eax, eax` | A common idiom that means "set `eax` to 0" (cheaper than `mov eax, 0`). |

That's the toolkit. The first time you read real assembly it looks dense; after an hour with Compiler Explorer, it reads like prose.

### 5. AT&T vs Intel syntax — the operand-order trap

The same machine instruction can be *written* two ways. This trips up everyone exactly once:

- **Intel syntax** (used by Compiler Explorer's default, MSVC, NASM): `mov dst, src` — **destination first**. `mov rax, 5` means "put 5 into rax."
- **AT&T syntax** (the default of `gcc -S` and `objdump` on Linux): `mov src, dst` — **source first**, with `%` on registers and `$` on constants. `mov $5, %rax` means the *same thing*: "put 5 into rax."

So the *exact same instruction* is `mov rax, 5` (Intel) or `mov $5, %rax` (AT&T). If you read it the wrong way you'll think the data is flowing backwards. **Tip:** in Compiler Explorer, there is an "Intel syntax" toggle (it's on by default), and `objdump -M intel -d` forces Intel. When starting out, pick **Intel** everywhere and stay consistent.

### 6. Addressing modes: `[base + index*scale + disp]`

When assembly touches memory, it uses brackets. The general form on x86-64 is:

```text
[base + index*scale + displacement]
```

For example `mov eax, [rdi + rcx*4 + 8]` means: take the address in `rdi`, add `rcx` times 4, add 8, and load the 32-bit value at *that* address into `eax`. This is exactly how the compiler indexes an array: `rdi` is the array start, `rcx` is the index, `4` is the element size (a 4-byte `int`), and `8` is some offset. Recognizing this pattern is how you spot array accesses in the wild.

### 7. The simplest optimizations to recognize

At your level, four optimizations are easy to spot and very satisfying:

- **Constant folding:** you write `return 2 + 3;` and the assembly is just `mov eax, 5`. The compiler did the math.
- **Strength reduction:** you write `x * 8` and instead of a multiply you see `shl` (shift left) or a `lea`. Multiplying by a power of two is a shift.
- **`xor` to zero:** `xor eax, eax` is the idiom for "set to 0," not a real XOR you should puzzle over.
- **Dead code elimination:** you write a variable that's never used, and it simply doesn't appear in the output.

Spotting these is the gateway drug. Once you see the compiler do something clever, you'll want to look every time.

---

## Code Examples

> All examples assume **Intel syntax** (Compiler Explorer's default). Try every one of these yourself at godbolt.org — that is the whole point.

### Example 1: Add two numbers (the "hello world" of codegen)

```c
int add(int a, int b) {
    return a + b;
}
```

At `-O2`, x86-64:

```asm
add:
        lea     eax, [rdi + rsi]   ; eax = a + b  (rdi=a, rsi=b)
        ret
```

Reading it: arguments come in `rdi` and `rsi`. The compiler used `lea` (which can add two registers in one instruction) to compute `a + b` into `eax`, the return-value register. Then `ret`. That's the whole function. Notice there is **no stack setup** — at `-O2` for such a trivial function, the prologue/epilogue is gone.

### Example 2: The same function at `-O0` (so you can see the literal version)

```asm
add:
        push    rbp
        mov     rbp, rsp
        mov     DWORD PTR [rbp-4], edi   ; store a on the stack
        mov     DWORD PTR [rbp-8], esi   ; store b on the stack
        mov     edx, DWORD PTR [rbp-4]   ; load a back
        mov     eax, DWORD PTR [rbp-8]   ; load b back
        add     eax, edx                 ; eax = a + b
        pop     rbp
        ret
```

Same function, *eight* instructions instead of two. At `-O0` the compiler faithfully shuffles everything through the stack (`[rbp-4]`, `[rbp-8]`) and adds a prologue (`push rbp` / `mov rbp, rsp`) and epilogue (`pop rbp`). This is why `-O0` is easy to *step through in a debugger* but is *not* what your release build looks like. **Lesson: never judge performance from `-O0` codegen.**

### Example 3: Constant folding

```c
int answer(void) {
    return 6 * 7;
}
```

At `-O2`:

```asm
answer:
        mov     eax, 42
        ret
```

The multiply is *gone*. The compiler computed `6 * 7 = 42` at compile time and just returns the constant. This is **constant folding**. If you ever wonder "does the compiler precompute this?" — look. The answer is right there.

### Example 4: Strength reduction (multiply becomes a shift)

```c
int times8(int x) {
    return x * 8;
}
```

At `-O2`:

```asm
times8:
        lea     eax, [0 + rdi*8]   ; eax = x * 8, using the scale factor
        ret
```

No `imul` instruction. The compiler used the addressing-mode `*8` scale to multiply — multiplying by a power of two is just a shift, and `lea` does it for free. This is **strength reduction**: a cheap operation replaced an expensive one. (You may also see it as `shl eax, 3`, i.e. "shift left by 3," which is the same as ×8.)

### Example 5: A simple loop (recognizing loop shape)

```c
int sum_to(int n) {
    int total = 0;
    for (int i = 0; i < n; i++)
        total += i;
    return total;
}
```

At `-O0` (so the loop is visible as a loop), simplified:

```asm
sum_to:
        ; ... prologue, total = 0, i = 0 ...
.L3:
        cmp     i, n          ; compare i with n
        jge     .L4           ; if i >= n, exit the loop
        add     total, i      ; total += i
        add     i, 1          ; i++
        jmp     .L3           ; go back to the top
.L4:
        ; ... return total ...
```

This is the universal shape of a `for` loop in assembly: a **label** at the top (`.L3`), a **compare-and-jump-out** (`cmp` + `jge`), the **body**, the **increment**, and a **jump back** (`jmp .L3`). Once you recognize this, you can find any loop in any disassembly. (Fun aside: at `-O2`, the compiler may replace this entire loop with the closed-form formula `n*(n-1)/2` — try it and watch the loop vanish.)

### Example 6: A function call vs. an inlined call

```c
static int square(int x) { return x * x; }

int use(int n) {
    return square(n) + 1;
}
```

At `-O2`:

```asm
use:
        mov     eax, edi
        imul    eax, eax       ; eax = n * n   (square was INLINED — no call!)
        add     eax, 1
        ret
```

There is **no `call square`** instruction. The compiler copied `square`'s body (`x * x`) directly into `use`. That's **inlining**. If instead you saw `call square` here, you'd know the inline *didn't* happen — a useful thing to detect. The presence or absence of a `call` is one of the first things to look for.

### Example 7: Emitting assembly from the command line

```bash
# Emit assembly text (don't make a binary). Output goes to file.s
gcc -O2 -S file.c
clang -O2 -S file.c

# Force Intel syntax (much friendlier than the AT&T default)
gcc -O2 -S -masm=intel file.c

# Disassemble a compiled binary, interleaving the source lines:
gcc -O2 -g -c file.c            # compile to file.o with debug info
objdump -d -M intel -S file.o   # disassemble, Intel syntax, with source

# Rust: emit assembly for a function (cargo-show-asm makes this nice)
rustc --emit asm -O file.rs
# or the friendly tool:
cargo install cargo-show-asm
cargo asm my_crate::my_function
```

The two most useful first commands: `gcc -O2 -S -masm=intel file.c` (clean assembly with the source) and `objdump -d -M intel a.out` (disassemble a finished binary). But honestly, for *learning*, just use Compiler Explorer.

### Example 8: Using Compiler Explorer (Godbolt) — the workflow

1. Go to **godbolt.org**.
2. Paste your function in the left pane (write it as a *function*, not `main` — it's clearer).
3. Pick a compiler (e.g. `x86-64 gcc 14`) in the right pane's dropdown.
4. Add flags in the "Compiler options" box: start with `-O2`.
5. Look at the assembly on the right. **Click a line of source** — Compiler Explorer highlights the matching assembly in the same color. This source↔asm color mapping is the single most useful feature for beginners.
6. Change the flag to `-O0`, then `-O3`, and watch the output change. Change the compiler from gcc to clang and compare. Change the architecture to ARM64 and see a completely different instruction set.

That color-mapped, instant, side-by-side view is why every performance engineer keeps a Godbolt tab open.

---

## Coding Patterns

These are *reading* patterns — repeatable moves for getting answers fast.

### Pattern 1: Always write it as a function, never `main`

```c
// Good for reading: a clean function with arguments.
int target(int a, int b) { return a + b; }
```

If you put your code in `main` with hardcoded values, the compiler will constant-fold everything and you'll see `mov eax, 5` with no logic. Writing a *function with parameters* forces the compiler to produce real, general code you can read.

### Pattern 2: Compare two optimization levels side by side

Open the function at `-O0` to learn the literal mapping, then switch to `-O2` to see what the optimizer did. The *difference* between them is the optimization. Compiler Explorer lets you open two compiler panes at once — `-O0` on the left, `-O2` on the right.

### Pattern 3: Search for the `call`

When checking inlining, the single fastest move is to look for `call`. If the function you expected to be inlined still shows `call funcname`, the inline didn't happen. No `call` (and the callee's logic appears inline) means it did.

### Pattern 4: Click the source line, follow the color

In Godbolt, click a line of source. The matching assembly lights up in the same color. This instantly answers "which instructions came from this line?" — invaluable when the output is large.

### Pattern 5: Force Intel syntax everywhere

```bash
objdump -d -M intel a.out
gcc -S -masm=intel file.c
```

In Compiler Explorer, the "Intel" toggle is on by default — leave it. Pick one syntax (Intel) and never fight the operand-order confusion again.

### Pattern 6: Use `-g` and `objdump -S` to see source alongside disassembly

```bash
gcc -O2 -g -c file.c
objdump -d -M intel -S file.o
```

The `-S` flag interleaves your *source lines* with the disassembly, so you don't have to map instructions back to source by hand.

---

## Best Practices

- **Use Compiler Explorer first.** Before reaching for command-line tools, paste it into godbolt.org. It's faster and the color mapping is unbeatable for learning.
- **Always read at the optimization level you ship.** If your release build is `-O2`, read `-O2`. Reading `-O0` to *judge performance* is meaningless.
- **Pick Intel syntax and commit to it.** Mixing syntaxes is the #1 cause of "wait, which way does the data flow?" confusion.
- **Write minimal examples.** Isolate the *one* function you care about. Smaller examples produce readable output.
- **Start with constant folding and strength reduction.** They're the most visible and most satisfying optimizations to learn to spot.
- **Recognize patterns, not every instruction.** You don't need to understand every line — find the loop, find the `call`, find the array index.
- **Verify before you claim.** If you're about to tell a teammate "the compiler handles that," look first. Be the person with the X-ray.
- **Keep a cheat sheet of the ~12 instructions** near you until they're second nature.

---

## Edge Cases & Pitfalls

- **The AT&T/Intel operand-order trap.** `mov a, b` means opposite things in the two syntaxes. If your reading of the data flow seems backwards, you're probably in the *other* syntax. Force Intel and re-read.
- **Reading `-O0` and assuming it's your release code.** `-O0` is a deliberately literal, slow translation full of stack traffic. Your shipped `-O2` build looks completely different. Never benchmark or judge speed from `-O0` output.
- **Putting test values in `main` and seeing them folded.** If you hardcode inputs, the compiler computes the answer at compile time and you see *no logic*. Always use a function with real parameters.
- **`eax` and `rax` confusing you.** They're the *same register* at different widths (32-bit vs 64-bit). `mov eax, X` zeroes the top 32 bits of `rax` as a side effect — a quirk you'll meet later; for now just know they're the same register.
- **`xor eax, eax` looking like a puzzle.** It's just the idiom for "set `eax` to 0." Don't overthink it.
- **`lea` looking like a memory load.** `lea` ("load *effective address*") often does *arithmetic*, not a memory access — e.g. `lea eax, [rdi + rsi]` is just `a + b`. The brackets don't always mean "touch memory."
- **Expecting source lines and assembly lines to line up 1:1.** They don't. The compiler reorders and merges. Use the color mapping (Godbolt) or `objdump -S` instead of counting lines.
- **Different compiler = different output.** gcc and clang make different (both valid) choices. If you compare to a tutorial that used the other compiler, the assembly won't match exactly — that's normal.
- **The output for the *wrong architecture*.** Make sure Godbolt's compiler is `x86-64` if that's your target; selecting an ARM compiler gives totally different mnemonics, which is great to know but confusing if unexpected.
- **Forgetting `-O2` entirely.** Many "the compiler didn't optimize this!" panics are just someone reading the default (often `-O0`) output. Add `-O2` and look again.

---

## Apply it

1. Choose one small, known input for **Reading Codegen (Disassembly & Compiler Output)**.
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

- What problem does Reading Codegen (Disassembly & Compiler Output) solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
