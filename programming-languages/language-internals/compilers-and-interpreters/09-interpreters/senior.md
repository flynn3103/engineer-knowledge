# Interpreters — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Interpreters** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Where the time goes: the dispatch cost

In a tight bytecode loop, the operations are cheap; the *getting between them* is not. Each iteration of a `switch`-based loop does: read `code[ip]`, range-check (in some languages), compute the jump table entry, take an **indirect branch** to the handler, run the (often 1–3 instruction) handler, then branch back to the top of the loop. The two indirect branches — into the handler and back to the loop top — are the problem.

The killer is **branch misprediction**. A `switch` loop has *one* indirect branch site that jumps to ~100 different targets depending on the opcode. The CPU's branch-target predictor keeps a small history per branch *site*; with one site and a chaotic sequence of targets, it mispredicts constantly. Each misprediction flushes the pipeline — tens of cycles wasted. On dispatch-bound interpreters this is the single largest cost.

### 2. Threaded code: give each opcode its own branch

The fix is structural: instead of one central `switch` that everyone returns to, let **each opcode handler dispatch to the next one directly**. Now the indirect branch lives at the *end of each handler*, so there are ~100 branch sites, one per opcode. The predictor can learn per-site patterns — and bytecode has lots of them (a comparison is usually followed by a conditional jump; a load is often followed by an add). Correlated sequences become predictable, and mispredictions drop sharply.

This family is called **threaded code**. The most common variant uses **computed goto**.

### 3. Direct threading with computed goto (`&&label`)

GCC and Clang support *labels as values*: `&&label` yields a `void*` to that label, and `goto *ptr` jumps to it. With a dispatch table of handler addresses, you write:

```c
static void* table[] = { &&op_const, &&op_add, &&op_load, /* ... */ };

#define DISPATCH() goto *table[code[ip++]]

DISPATCH();              // start
op_const:  push(constants[code[ip++]]); DISPATCH();
op_add:    { Value b = pop(), a = pop(); push(a + b); } DISPATCH();
op_load:   push(locals[code[ip++]]);    DISPATCH();
// ...
```

There is **no central loop**. Each handler ends by jumping straight to the next handler. This is exactly the technique CPython enables with `USE_COMPUTED_GOTOS` in `ceval.c` — and it is why CPython's eval loop is written the way it is. Typical gains are 15–50% on dispatch-bound code, depending on architecture and workload.

### 4. The threaded-code family: direct, indirect, subroutine

- **Direct/token threading** (above): bytecode holds tokens (small ints); a table maps token → handler address; `goto *` jumps. Fastest portable software dispatch.
- **Indirect threading**: bytecode holds pointers into a table of pointers to handlers — one more indirection, historically used when you cannot take label addresses. Slightly slower, more flexible.
- **Subroutine threading**: each opcode compiles to a real `call handler` instruction. The win is the CPU's dedicated **return-address stack predictor**, which is very accurate. This blurs into "compiling bytecode to a list of calls" — a stepping stone toward a JIT.

A historical note: the term "threaded code" comes from Forth implementations, long before today's bytecode VMs; the ideas are old and battle-tested.

### 5. Superinstructions: fuse common sequences

Profiling real bytecode reveals that certain opcode *pairs* and *triples* dominate. `LOAD_FAST` followed by `LOAD_FAST` followed by `BINARY_ADD` is everywhere. A **superinstruction** is a single new opcode that does the work of a whole common sequence, paying the dispatch cost **once** instead of three times.

```text
  LOAD_FAST a; LOAD_FAST b; ADD     ->     ADD_LOCALS a, b
```

You discover hot sequences by profiling, then either hand-write superinstructions or generate them. This trades a larger opcode set (and a bigger dispatch table) for fewer dispatches. CPython's "adaptive specializing interpreter" (PEP 659, Python 3.11+) is a modern, automatic descendant of this idea: it rewrites generic opcodes into specialized ones at runtime based on observed types.

### 6. Stack caching: keep the top-of-stack in a register

In a stack-based VM, almost every instruction touches the **top of the operand stack** — and the stack lives in memory. **Stack caching** keeps the top one (or two) stack entries in CPU registers, so back-to-back instructions hand off through a register instead of a memory store + load. An `ADD` that takes `b` from the cached TOS register avoids a memory round-trip entirely. Implementations track which "stack state" they are in (0, 1, or 2 items cached) and specialize handlers per state. This is a meaningful win precisely because stack VMs touch TOS constantly.

### 7. Inline caching at the interpreter level

Dynamic languages do expensive lookups: "what method does `x.foo()` resolve to?", "where is property `name` on this object?". The answer usually does not change at a given call site — the same site sees the same object *shape* over and over. An **inline cache** memoizes the resolution *at the call site*: the first time, do the slow lookup and remember (shape → slot/method); next time, check the cached shape and, on a hit, skip the lookup. This is foundational to fast dynamic-language interpreters and to V8's hidden classes; at the interpreter level it lives in the bytecode (or a side table keyed by instruction). A *monomorphic* site (one shape) is fastest; *polymorphic* (a few shapes) keeps a small set; *megamorphic* falls back to the slow path.

### 8. Closures and upvalues: capturing variables across scopes

A **closure** is a function plus the variables it captured from enclosing scopes. The simple representation is an **environment chain**: each scope is a record with a pointer to its parent, and a variable lookup walks outward until found. Correct, but a runtime hash/linked-list walk — slow, the very thing `middle.md` worked to eliminate for locals.

Lua's **upvalue** mechanism is the elegant production answer. A captured local is referenced through an *upvalue* object. While the enclosing function is still running, the upvalue points directly at the live stack slot (an "open" upvalue). When that function returns, the value is "closed" — copied into the upvalue object so the closure keeps working after the stack frame is gone. This gives closures correct sharing semantics without a general environment-chain walk on every access. Understanding open/closed upvalues is a hallmark of someone who has actually implemented closures.

### 9. Exceptions: unwinding the interpreter's stack

The guest language's exceptions must unwind the *interpreter's* model of the call stack, not (only) the host's. Two common designs: (a) a **handler stack** — push try/catch handlers as you enter them; on throw, pop frames until you find a matching handler, restoring the operand stack and IP; or (b) **exception tables** — per-function metadata mapping IP ranges to handler offsets (the JVM's approach), so the normal path pays nothing and the throw path consults the table. The throw must correctly unwind operand stacks and run any `finally`/cleanup along the way. Getting stack restoration exactly right (operand stack height, locals, IP) is a classic source of subtle bugs.

### 10. Tail calls: recursion without stack growth

A call in **tail position** — the function's last action is to return the result of another call — does not need the current frame anymore. A **proper tail call** reuses the current frame: overwrite the arguments, jump to the callee's start, do *not* grow the stack. This turns tail-recursive guest code into iteration, so deep recursion runs in constant stack space (Scheme requires this; Lua provides it). Without TCO, deep guest recursion overflows the *host* stack — a real limitation of naive interpreters. Detecting tail position is a compile-time analysis; performing TCO is a special `TAIL_CALL` opcode (or a check in `CALL`) that reuses rather than pushes a frame.

### 11. The interpreter-to-JIT path

Interpreting is fast to start and slow to run; native compilation is the reverse. Production systems get both by **starting interpreted and JIT-compiling hot code**. Each function (or loop) carries a counter; when it crosses a threshold, a compiler turns its bytecode into native code, and future calls run the compiled version. This is **tiered execution**: V8 runs **Ignition** (bytecode interpreter) then **TurboFan** (optimizing JIT); the JVM runs an interpreter then **C1** then **C2**; CPython 3.13+ ships an experimental JIT atop its adaptive interpreter. The interpreter is not thrown away — it handles cold code, provides a baseline, and serves as the **deopt** target when the JIT's speculative assumptions (from inline caches) turn out wrong. The codegen details belong to runtime-systems; the *architecture* — interpret first, profile, compile the hot parts, deopt on surprise — is the senior interpreter-implementer's mental model.

### 12. Meta-tracing and partial evaluation (a gentle introduction)

Two research-grade ideas, now in production, let you get a JIT *without hand-writing one*:

- **Meta-tracing (PyPy/RPython):** you write an *interpreter* in RPython; the meta-tracing JIT observes the interpreter executing a hot guest loop and records the *trace of interpreter operations*, then compiles that trace. You get a JIT for your language essentially for free, derived from your interpreter.
- **Partial evaluation / Futamura projections (Truffle/GraalVM):** an AST interpreter, specialized against a specific program by a partial evaluator, *becomes* a compiler for that program — the first Futamura projection. Truffle does this: write a self-optimizing AST interpreter, and Graal partially-evaluates it into optimized native code.

Both turn the slogan "an interpreter plus a clever compiler equals a compiler" into engineering reality. We go deeper in `professional.md`; here the point is that your interpreter can be the *source* of a JIT, not merely a fallback for one.

---

## Code Examples

### Switch dispatch vs computed-goto (direct threading) in C

The two loops below run identical bytecode. The first is portable; the second uses GCC's computed goto and is typically meaningfully faster on dispatch-bound code.

```c
// ---- Switch dispatch (portable) ----
Value run_switch(uint8_t *code, Value *constants, Value *locals) {
    Value stack[256]; int sp = 0; size_t ip = 0;
    for (;;) {
        uint8_t op = code[ip++];
        switch (op) {                                   // ONE indirect branch site
            case CONST: stack[sp++] = constants[code[ip++]]; break;
            case ADD:   { Value b = stack[--sp], a = stack[--sp];
                          stack[sp++] = a + b; } break;
            case LOAD:  stack[sp++] = locals[code[ip++]]; break;
            case STORE: locals[code[ip++]] = stack[--sp]; break;
            case JMPF:  { size_t t = code[ip++];
                          if (!stack[--sp]) ip = t; } break;
            case HALT:  return stack[--sp];
        }
        // loop back to the top -> the predictor must guess `op` again
    }
}
```

```c
// ---- Direct threading (computed goto, GCC/Clang) ----
Value run_threaded(uint8_t *code, Value *constants, Value *locals) {
    static void *table[] = {
        [CONST]=&&op_const, [ADD]=&&op_add, [LOAD]=&&op_load,
        [STORE]=&&op_store, [JMPF]=&&op_jmpf, [HALT]=&&op_halt,
    };
    Value stack[256]; int sp = 0; size_t ip = 0;
    #define DISPATCH() goto *table[code[ip++]]          // branch site PER handler
    DISPATCH();
op_const:  stack[sp++] = constants[code[ip++]];                  DISPATCH();
op_add:    { Value b = stack[--sp], a = stack[--sp];
             stack[sp++] = a + b; }                              DISPATCH();
op_load:   stack[sp++] = locals[code[ip++]];                    DISPATCH();
op_store:  locals[code[ip++]] = stack[--sp];                    DISPATCH();
op_jmpf:   { size_t t = code[ip++]; if (!stack[--sp]) ip = t; } DISPATCH();
op_halt:   return stack[--sp];
    #undef DISPATCH
}
```

The only structural change is *where the indirect branch lives*: one shared site (switch) vs one per opcode (threaded). That single change is what gives the branch predictor a fighting chance, and is exactly the option CPython exposes via `USE_COMPUTED_GOTOS`.

### A superinstruction

Profiling shows `LOAD a; LOAD b; ADD` dominates. Add a fused opcode:

```c
op_add_locals:  // operands: two slot indices
    { uint8_t a = code[ip++], b = code[ip++];
      stack[sp++] = locals[a] + locals[b]; }           DISPATCH();
```

The compiler emits `ADD_LOCALS a, b` wherever it sees that triple. Three dispatches collapse into one; the arithmetic is identical.

### Closures via upvalues (sketch)

```c
typedef struct Upvalue {
    Value *location;   // points into the live stack while "open"...
    Value  closed;     // ...or holds the captured value once "closed"
    struct Upvalue *next;
} Upvalue;

typedef struct Closure {
    Function *fn;
    Upvalue **upvalues;   // captured variables
    int upvalue_count;
} Closure;

// When the enclosing frame returns, close upvalues that point above the new top:
void close_upvalues(VM *vm, Value *last) {
    while (vm->open_upvalues && vm->open_upvalues->location >= last) {
        Upvalue *uv = vm->open_upvalues;
        uv->closed = *uv->location;   // copy the live value out of the dying frame
        uv->location = &uv->closed;   // redirect to the closure's own storage
        vm->open_upvalues = uv->next;
    }
}
```

Open upvalues alias the live stack slot (so the closure and the still-running parent share the same variable); closing copies the value so the closure outlives the frame. This is the Lua design Nystrom adapts in *Crafting Interpreters*.

### Tail-call handling

```c
op_tail_call:  // reuse the current frame instead of pushing a new one
    {
        Closure *callee = AS_CLOSURE(peek(arg_count));
        // overwrite current frame's slots with the new arguments, then:
        frame->closure = callee;
        frame->ip = callee->fn->code;     // jump to callee start, no stack growth
        // (slots/operand-stack adjusted to the new function's layout)
    }
    DISPATCH();
```

Because no frame is pushed, a guest function that tail-calls itself a million times uses *one* host frame, not a million. This is what makes Scheme-style loops-as-recursion run in constant space.

### Interpreter-to-JIT trigger (pseudocode)

```c
void call_function(VM *vm, Function *fn) {
    fn->call_count++;
    if (fn->jit_code) {
        run_native(fn->jit_code, vm);          // hot: run compiled code
    } else if (fn->call_count > JIT_THRESHOLD) {
        fn->jit_code = jit_compile(fn);        // crossed the line: compile it
        run_native(fn->jit_code, vm);
    } else {
        run_bytecode(vm, fn);                  // cold: interpret
    }
}
```

This counter-and-threshold is the skeleton of tiered execution in V8, the JVM, and PyPy — interpret until hot, then compile.

---

## Coding Patterns

### Pattern 1: Macro-driven `DISPATCH()`

Hide the dispatch mechanism behind a `DISPATCH()` macro so you can switch between `switch` and computed-goto builds with one `#ifdef`. CPython does exactly this, supporting both portable and computed-goto builds from one source.

### Pattern 2: Profile, then fuse

Add instrumentation that counts opcode *bigrams/trigrams* at runtime. Pick the hottest sequences and introduce superinstructions for them. Re-profile to confirm the win and to find the next candidates.

### Pattern 3: TOS-in-register with stack-state specialization

Maintain the top-of-stack in a local variable the compiler will keep in a register; specialize handlers for the "0 cached / 1 cached" states. Even caching just the single top entry captures most of the benefit with manageable complexity.

### Pattern 4: Inline-cache slots in the bytecode

Reserve operand space (or a parallel array) at each lookup site to store the cached shape and resolved slot/method. On execution: compare shape; hit → fast path; miss → slow path + refill. Make invalidation explicit when shapes change.

### Pattern 5: Open/closed upvalue list per VM

Keep a linked list of open upvalues sorted by stack address. On every frame return, close the upvalues above the returning frame's base. Centralizing this keeps closure lifetime logic in one auditable place.

### Pattern 6: Counter-and-threshold tiering

Attach an execution counter to each function and loop. Cross a threshold → promote (compile). Keep the interpreter as the cold-path executor and the deopt target. Keep the promotion logic out of the steady-state hot path.

---

## Best Practices

- **Profile before optimizing dispatch.** Confirm the eval loop is the bottleneck (not GC, not allocation, not a slow built-in) before reaching for computed goto or superinstructions.
- **Keep the switch build working alongside the threaded build.** The portable `switch` version is your correctness oracle and your fallback on compilers without computed goto.
- **Make handlers uniform and short.** Predictable, small handlers help both the branch predictor and the instruction cache; they also make superinstruction fusion mechanical.
- **Centralize stack-effect accounting.** Every opcode's push/pop count must be exact; encode it in one table and assert it in debug builds. Stack drift is the dominant VM bug.
- **Design inline caches with invalidation from day one.** A cache without a correct invalidation story is a correctness bug waiting to happen when object shapes change.
- **Get upvalue lifetimes right before optimizing closures.** A closure that reads a freed stack slot is a use-after-free; prove correctness, then make it fast.
- **Treat the JIT as an accelerator of correct interpreter semantics.** The interpreter defines behavior; the JIT must match it bit-for-bit, including deopt. Differential-test JIT vs interpreter relentlessly.
- **Mind portability costs.** Computed goto, label addresses, and tail-call assumptions are compiler-specific. Document the requirements; gate them behind feature macros.

---

## Edge Cases & Pitfalls

- **Computed goto is non-standard.** MSVC lacks `&&label`; some sanitizers and coverage tools interact poorly with it. Always keep the `switch` fallback compilable.
- **The dispatch table must cover every opcode.** A hole (uninitialized table slot) jumps to garbage. Generate the table from the opcode list to keep them in sync.
- **Superinstructions multiply the opcode space.** Too many fused opcodes bloat the i-cache and the table, eroding the gain. Fuse only genuinely hot sequences.
- **Stack caching breaks naive debuggers and stack walkers.** The "real" TOS lives in a register, not memory; any tool reading the operand stack must account for the cached entry.
- **Inline cache invalidation bugs are silent.** A stale cache returns a wrong method/slot after a shape change — a correctness disaster that passes most tests. Invalidate aggressively; test shape transitions.
- **Upvalue closing order matters.** Close upvalues for *all* slots at or above the returning frame; missing one leaves a closure aliasing a dead slot. Off-by-one here is a use-after-free.
- **Tail-call optimization erases stack frames.** Great for space, painful for debugging — the call that "should" be in the backtrace is gone. Some languages (Python) refuse TCO partly for this reason.
- **Exception unwinding must restore the operand stack, not just the IP.** Jumping to a handler with a mis-sized operand stack corrupts subsequent execution. Record stack height per handler.
- **Deopt must be exact.** When a JITed function's speculation fails, control must resume in the interpreter at the precise bytecode state (locals, operand stack, IP). Any mismatch is a heisenbug.
- **`finally`/cleanup during unwinding.** Cleanup blocks must run on the throw path and can themselves throw — re-entrant unwinding is easy to get wrong.

---

## Apply it

1. State the system invariant that **Interpreters** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Interpreters fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
