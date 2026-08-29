# Code Generation — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Code Generation** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Instruction Selection as Tree Covering

Represent an IR expression as a tree. `a[i] + 7` (with `int a[]`) becomes:

```text
            (+)
           /   \
       (load)   7
          |
        (+)
       /    \
   a_base   (*)
           /    \
          i      4
```

You have a library of **tiles**, each matching some subtree shape and producing one machine instruction at some cost. For x86-64, among the tiles are:

- `ADD reg, imm` — matches `(+ reg imm)`, cost 1.
- `MOV reg, [base + index*scale]` — matches the whole `(load (+ base (* index scale)))` subtree, cost 1.
- `LEA reg, [base + index*scale + disp]` — matches `(+ (+ base (* index scale)) disp)`, cost 1.

**Tiling** = covering the tree with non-overlapping tiles so every node is covered exactly once. The big `MOV [base+index*scale]` tile swallows four IR nodes at once, which is why the selector prefers it: fewer, cheaper instructions.

**Maximal munch** is the greedy strategy: start at the root, choose the *largest* tile that matches, then recurse on the subtrees dangling below that tile. It's simple and fast and gives good (not always optimal) results. The risk: a locally-large tile can leave an awkward, expensive remainder.

**Optimal tree covering** uses **dynamic programming**: for each node, compute the minimum cost to produce its value in each possible "kind" (register, condition flag, address), considering every tile that matches there and adding the best costs of its sub-results. This is exactly what **BURS/iburg-style** generators do — you write a cost-annotated tree grammar, and a tool produces a linear-time optimal tree-pattern matcher. For a single tree, DP gives a provably minimum-cost cover.

### 2. Why CISC and RISC Selection Differ

On **CISC (x86-64)**, the tile library is large and tiles overlap heavily: `lea`, complex addressing modes, read-modify-write memory operands, instructions with implicit operands. Selection is rich and high-payoff — finding the right big tile saves real instructions. The variable-length encoding also means a "good" choice can be smaller in bytes, helping the instruction cache.

On **RISC (RISC-V, and largely AArch64)**, tiles are mostly small and uniform — most instructions are register-register, fixed 4 bytes. There's less to discover; selection is closer to one-IR-op-to-one-instruction, with a few useful composite forms (AArch64's shifted-register operands, load/store with index). The payoff of clever selection is smaller, but scheduling and register allocation carry more weight because you emit more instructions.

### 3. Register Allocation by Graph Coloring (Chaitin–Briggs)

The classical formulation:

1. **Liveness analysis.** For each value, compute its **live range** — from its definition to its last use. Across basic blocks this is a standard backward dataflow analysis.
2. **Build the interference graph.** One node per value. Add an edge between two values whose live ranges **overlap** — they're simultaneously alive, so they can't occupy the same register.
3. **Color with K colors.** K = number of allocatable physical registers. A valid K-coloring assigns each value a register such that no two interfering values share one. Graph coloring is NP-hard in general, so we use a heuristic:
   - **Simplify:** repeatedly remove any node with **degree < K** and push it on a stack. Such a node is *always* colorable later (fewer than K neighbors means a free color exists).
   - **Spill:** if every remaining node has degree ≥ K, pick one to **spill** (mark it as memory-resident), remove it, continue.
   - **Select:** pop nodes off the stack, assigning each a color not used by its already-colored neighbors.
4. **Insert spill code.** For each spilled value, add a store after each definition and a load before each use, then *rebuild and recolor* (spilling creates tiny new live ranges). Iterate until colorable.

**Briggs's improvements** over Chaitin's original: *optimistic coloring* (push potential spills onto the stack and try to color them anyway during select — they often succeed) and better coalescing.

### 4. Spill Cost and Coalescing

When you must spill, *which* value? You want to spill the cheapest one. A standard **spill-cost** heuristic:

```text
spill_cost(v) = (sum over uses/defs of v: 10^loop_depth) / degree(v)
```

Values used inside deep loops are expensive to spill (the `10^loop_depth` weight); values with high interference degree are attractive to spill (removing them unblocks many others). Real allocators tune this formula heavily.

**Coalescing** addresses copies. SSA and calling conventions introduce many `mov a, b` instructions. If `a` and `b` don't interfere, you can **coalesce** them into one value, deleting the `mov`. But aggressive coalescing can *raise* the merged node's degree and cause spills — so allocators use **conservative coalescing** (Briggs: only coalesce if the result has < K neighbors of significant degree) to avoid making the graph harder to color.

### 5. Linear-Scan Allocation (the JIT Favorite)

Graph coloring is high quality but slow — building and iterating the interference graph is expensive. **Linear scan** trades a little code quality for a lot of compile speed:

1. Order all live ranges by their start point.
2. Sweep left to right. Maintain an "active" set of currently-live ranges sorted by end point.
3. At each new range: **expire** any active range that has ended (free its register); if a register is free, assign it; if not, **spill** — either the new range or the active one ending latest, whichever is cheaper.

It's roughly O(n log n), produces decent (not optimal) allocations, and is exactly why JITs (HotSpot's C1, many JavaScript engines) and fast compilers (Go's compiler uses a linear-scan-style allocator) choose it: when you compile at runtime, *compile time is run time*, so a fast allocator wins even if the code is slightly worse.

### 6. Callee-Saved vs Caller-Saved Interaction

The ABI splits physical registers into two classes, and the allocator must respect both:

- **Caller-saved (volatile):** a called function may clobber these freely. If the allocator keeps a value in a caller-saved register *across a call*, it must spill/reload around the call.
- **Callee-saved (non-volatile):** a function must preserve these — if it uses one, it saves it in the prologue and restores it in the epilogue.

So values that live *across* calls prefer callee-saved registers (no per-call spilling, just one save/restore in prologue/epilogue), while short-lived values prefer caller-saved registers (no prologue cost). A good allocator models this as part of the cost.

### 7. Instruction Scheduling: the Dependence DAG and List Scheduling

Within a basic block, build a **data-dependence DAG**:

- **True (read-after-write) dependence:** B reads what A wrote → B must follow A.
- **Anti (write-after-read) dependence:** B overwrites what A read → ordering constraint.
- **Output (write-after-write) dependence:** both write the same location.

Each node carries a **latency**. The scheduler wants a topological order of this DAG that minimizes total cycles, keeping functional units busy and ensuring a result is ready by the time it's needed.

**List scheduling** is the standard greedy method:

1. Compute a **priority** per instruction — commonly the **critical-path length** (longest latency-weighted path to a DAG leaf). Higher priority = more urgent.
2. Maintain a **ready set** (instructions whose predecessors are all scheduled).
3. Repeatedly: pick the highest-priority ready instruction whose required functional unit is free, "issue" it, advance the cycle clock, and move newly-ready instructions into the ready set.

The classic win: place a high-latency load early and fill the cycles before its use with independent instructions, so the load result is ready exactly when needed instead of stalling.

### 8. Software Pipelining (Loop Scheduling)

For tight loops, list scheduling within one iteration isn't enough — the win is *overlapping iterations*. **Software pipelining** (e.g. **modulo scheduling**) restructures a loop so that, in steady state, each iteration of the new loop body executes operations from *several* original iterations at once (load for iteration i+2, multiply for i+1, store for i). It massively increases ILP for in-order machines, at the cost of a complex prologue/epilogue and high register pressure (multiple iterations' values alive at once).

### 9. The Phase-Ordering Conflict, Concretely

Now the central tension. Consider scheduling a loop to expose ILP: you spread independent loads early so their results are ready later. But "ready later" means those loaded values are **alive longer**, overlapping more other values — which **raises register pressure** and can force the allocator to spill. The spill code adds memory traffic, partly undoing the scheduling win.

So:

- **Schedule before allocate:** you get a good schedule but may have created so much pressure that allocation spills, hurting performance.
- **Allocate before schedule:** allocation pins values to registers, adding **false dependences** (two values forced into the same register can't be reordered freely), constraining the scheduler.

There is no universally correct order. Real compilers compromise: schedule, allocate, then *re-schedule* (post-allocation scheduling) to clean up; or use **register-pressure-aware scheduling** that throttles parallelism when pressure gets high. This is the canonical example of the phase-ordering problem.

---

## Code Examples

### Maximal Munch, Sketched

A toy maximal-munch selector over a tiny expression tree (pseudocode in Python-like form):

```python
# IR tree nodes: ('const', n), ('reg', name), ('add', l, r), ('mul', l, r), ('load', addr)

def munch(node, emit):
    # Try the LARGEST tiles first; fall back to smaller ones.
    if node[0] == 'load':
        addr = node[1]
        # Tile: load [base + index*scale]
        if addr[0] == 'add' and addr[2][0] == 'mul' and addr[2][2] == ('const', 4):
            base = munch(addr[1], emit)          # recurse on leftover subtree
            index = munch(addr[2][1], emit)
            d = fresh_reg()
            emit(f"mov {d}, [{base} + {index}*4]")   # ONE instruction, 4 nodes
            return d
        a = munch(addr, emit)
        d = fresh_reg(); emit(f"mov {d}, [{a}]"); return d
    if node[0] == 'add':
        l = munch(node[1], emit); r = munch(node[2], emit)
        d = fresh_reg(); emit(f"add {d}, {l}, {r}"); return d
    if node[0] == 'const':
        d = fresh_reg(); emit(f"mov {d}, {node[1]}"); return d
    if node[0] == 'reg':
        return node[1]
```

The key move: when matching `load`, the selector *peeks deeper* into the address subtree to grab the big `[base + index*4]` tile before falling back to a plain `[addr]`. That peek is what fuses multiple IR nodes into one instruction.

### Building an Interference Graph

```python
# live[i] = set of values live AT instruction i (from backward liveness analysis)
def interference_graph(instructions, live):
    edges = set()
    for i, ins in enumerate(instructions):
        defined = ins.defs        # values this instruction writes
        for d in defined:
            for other in live[i]:
                if other != d:
                    edges.add(frozenset((d, other)))  # they overlap -> interfere
    return edges
```

A value interferes with everything else alive at the point it's defined: they coexist, so they need distinct registers.

### Chaitin-Style Simplify / Spill / Select

```python
def color(nodes, adj, K):
    stack, spilled = [], set()
    graph = {n: set(adj[n]) for n in nodes}
    work = set(nodes)
    while work:
        # SIMPLIFY: remove a low-degree (< K) node — always colorable later.
        low = next((n for n in work if len(graph[n]) < K), None)
        if low is None:
            # SPILL: every node has degree >= K. Pick cheapest to spill.
            low = min(work, key=spill_cost)
            spilled.add(low)
        stack.append(low)
        work.discard(low)
        for m in graph[low]:
            graph[m].discard(low)
    # SELECT: pop and assign a color avoiding neighbors' colors.
    colors = {}
    while stack:
        n = stack.pop()
        used = {colors[m] for m in adj[n] if m in colors}
        free = next((c for c in range(K) if c not in used), None)
        if free is None:          # optimistic spill that didn't pan out
            spilled.add(n)
        else:
            colors[n] = free
    return colors, spilled
```

If `spilled` is non-empty, the real allocator inserts spill code and reruns the whole thing.

### Linear Scan, Core Loop

```python
def linear_scan(intervals, K):           # intervals sorted by start
    active = []                            # sorted by end point
    free = list(range(K))
    location = {}
    for iv in intervals:
        # EXPIRE intervals that ended before iv starts -> free their registers.
        active = [a for a in active if a.end > iv.start
                  or (free.append(location[a.id]) or False)]
        if free:
            location[iv.id] = free.pop()
            active.append(iv); active.sort(key=lambda a: a.end)
        else:
            spill = active[-1]             # the one ending latest
            if spill.end > iv.end:
                location[iv.id] = location[spill.id]
                location[spill.id] = 'STACK'
                active[-1] = iv; active.sort(key=lambda a: a.end)
            else:
                location[iv.id] = 'STACK'
    return location
```

One left-to-right sweep, no interference graph — that's the speed advantage.

### List Scheduling Over a Dependence DAG

```python
def list_schedule(dag, latency):
    # priority = critical-path length (longest latency-weighted path to a leaf)
    prio = critical_path_lengths(dag, latency)
    ready = [n for n in dag.nodes if not dag.preds(n)]
    cycle, schedule, finish = 0, [], {}
    while ready:
        ready.sort(key=lambda n: prio[n], reverse=True)
        n = ready.pop(0)                    # highest-priority ready instr
        start = max([finish[p] for p in dag.preds(n)] + [cycle])
        finish[n] = start + latency[n]
        schedule.append((start, n))
        for s in dag.succs(n):
            if all(p in finish for p in dag.preds(s)):
                ready.append(s)
        cycle += 1
    return sorted(schedule)
```

Picking the highest-critical-path instruction first is the heuristic that keeps the longest chain moving.

### Seeing the Conflict in Real Output

```c
// Compile this at -O2 and inspect the loop. With more accumulators the
// compiler exposes more ILP (good for the pipeline) but uses more registers.
double dot(const double *a, const double *b, long n) {
    double s = 0;
    for (long i = 0; i < n; i++) s += a[i] * b[i];
    return s;
}
```

```bash
gcc -O3 -S dot.c -o dot.s          # look for multiple xmm accumulators / FMA
```

At `-O3` the compiler often **unrolls** and uses several accumulator registers to break the dependence chain on `s` (more ILP) — and uses correspondingly more `xmm` registers. That's the scheduling-vs-pressure trade-off made visible: more parallelism, more registers consumed.

---

## Coding Patterns

### Pattern 1: Lower Register Pressure to Avoid Spills

Identify the loop's *simultaneously live* values. Reduce them: scalar-replace fewer arrays, shorten live ranges by computing values closer to use, or split a monster function so each piece has its own register budget.

### Pattern 2: Help the Selector See the Pattern

Write expressions in the *natural algebraic shape* the selector recognizes (`base[i]`, `a*b + c`). Obfuscating with manual shifts and temporaries can hide the very tile the selector wanted (`lea`, FMA).

### Pattern 3: Break Dependence Chains for ILP

When a reduction loop (`s += ...`) is latency-bound, manually use multiple accumulators (or let `-ffast-math`/`-O3` do it) so independent partial sums can issue in parallel — the same trick the scheduler/unroller applies.

### Pattern 4: Pin Hot Values, Spill Cold Ones

If you control codegen (writing a compiler), bias the spill heuristic with loop depth so deep-loop values stay in registers and cold setup values spill. The standard `10^loop_depth` weighting encodes this.

### Pattern 5: Post-Allocation Re-Scheduling

In a compiler, run a light scheduling pass *after* allocation to clean up the false dependences allocation introduced. This is a pragmatic answer to the phase-ordering conflict.

---

## Best Practices

- **Think in live ranges, not variables.** A "variable" may have several disjoint live ranges; the allocator works on ranges, and so should your reasoning.
- **Treat K as a hard budget.** The number of allocatable registers is small (x86-64: ~14 usable GPRs after reserving). Design hot code to stay under it.
- **Coalesce conservatively.** Eliminating copies is good, but aggressive coalescing that raises degree can cause spills. Briggs/George conservative coalescing is the safe default.
- **Pick the allocator to match the compiler's job.** Compile speed critical (JIT) → linear scan. Run speed critical (AOT) → graph coloring / SSA-based.
- **Schedule with pressure awareness.** Don't expose ILP blindly; throttle when register pressure approaches K, or you'll trade scheduling gains for spill losses.
- **Respect the ABI register classes.** Values that live across calls belong in callee-saved registers; short-lived ones in caller-saved. Model this in the cost, not as an afterthought.
- **Validate selection cost models against real latencies.** A tile that's "one instruction" isn't always cheap (a memory-operand RMW can be slower than separate ops on some microarchitectures).

---

## Edge Cases & Pitfalls

- **Maximal munch's greedy trap.** A large tile chosen at the root can fragment the rest of the tree into expensive small pieces. Greedy isn't optimal; DP avoids it but costs more.
- **Spilling creates new live ranges.** Each spill inserts load/store instructions with their own (tiny) live ranges, which can *increase* pressure elsewhere and force re-iteration. Allocation isn't single-pass.
- **Coalescing too aggressively causes spills.** Merging two non-interfering copies can produce a high-degree node that no longer colors. The "obvious" optimization can backfire — hence conservative coalescing.
- **Pre-colored registers constrain coloring.** ABI-fixed registers (argument registers, the return register, `rsp`) are *pre-colored* nodes — already assigned a color — which constrains everything adjacent. Forgetting these is a classic allocator bug.
- **Anti- and output-dependences are real scheduling constraints.** They're not data flow but they still forbid reorderings, because reuse of a register/location creates ordering requirements. Ignoring them produces wrong code.
- **List scheduling is per-basic-block by default.** Latency hiding across block boundaries needs extensions (superblock/trace scheduling). A naive scheduler leaves cross-block opportunities on the table.
- **Software pipelining explodes register pressure.** Overlapping N iterations keeps N iterations' values alive; on a register-poor target this can spill away the benefit.
- **Phase ordering has no winner.** Whichever order you run selection/allocation/scheduling, some program loses. Don't expect a "correct" order — expect compromises (re-scheduling, pressure-aware passes).
- **On out-of-order CPUs, careful scheduling is partly wasted.** The hardware reorders anyway. Don't over-invest compiler scheduling for big OoO cores; do invest for in-order embedded targets.
- **Linear scan's lifetime holes hurt.** Basic linear scan treats a live range as one interval even when the value is dead in the middle ("lifetime holes"); it can hold a register unnecessarily. Extensions (second-chance binpacking, interval splitting) fix this — plain linear scan doesn't.
- **Spill-cost heuristics are estimates, not truth.** The `uses × loop_depth / degree` formula can misjudge; profile-guided weights do better but require profiles. Don't treat the heuristic as ground truth.

---

## Apply it

1. Find a real component where **Code Generation** affects an interface or dependency.
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

- Which boundary is most affected by Code Generation?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
