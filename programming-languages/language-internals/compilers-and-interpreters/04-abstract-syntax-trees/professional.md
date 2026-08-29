# Abstract Syntax Trees — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Abstract Syntax Trees** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. The cost model of a pointer tree

Start with the obvious AST and count the costs honestly. Each node is a separate heap object:

```rust
enum Expr {
    Lit(i64),
    BinOp { op: Op, lhs: Box<Expr>, rhs: Box<Expr> },  // two heap pointers
}
```

For a tree of N nodes:

- **N allocations** to build it, **N frees** to tear it down. malloc/free are not free; at N in the millions this is a measurable slice of compile time.
- **Poor locality.** `lhs` and `rhs` are wherever the allocator happened to put them — likely different cache lines, possibly different pages. Walking the tree is a tour of cache misses; the CPU stalls waiting on memory it cannot prefetch (the next address is only known *after* the current load completes — pointer chasing defeats the prefetcher).
- **Fat nodes.** Each `Box` is 8 bytes; each heap object carries an allocator header and alignment padding. A node that holds 2 bytes of real data may occupy 48.
- **Recursive drop / free** can blow the stack on deep trees and is itself a pointer-chasing walk.

None of this matters for a 200-node script. All of it matters for a compiler. The pointer tree optimizes for *programmer convenience* (it looks like the grammar) at the expense of *machine sympathy*.

### 2. The flat / arena / index-based AST

The data-oriented alternative: put every node in one contiguous array, and replace pointers with indices.

```rust
type NodeId = u32;                 // 4 bytes, not 8; an index, not a pointer

enum Node {
    Lit(i64),
    BinOp { op: Op, lhs: NodeId, rhs: NodeId },   // indices into `nodes`
}

struct Ast {
    nodes: Vec<Node>,              // ONE allocation, grows by doubling
    spans: Vec<Span>,             // parallel array: span of nodes[i]
}
```

What this buys:

- **One allocation (amortized).** Building the tree is pushing onto a `Vec`. Tearing it down is one `free`. No per-node malloc.
- **Cache locality.** Nodes are adjacent in memory; a traversal streams through the array, and the prefetcher actually works. Children are *nearby* indices, not random addresses.
- **Smaller handles.** A `u32` index halves the 8-byte pointer and, in a 4-billion-node ceiling that no real program approaches, costs nothing.
- **Cheap serialization and parallelism.** A flat array of POD nodes can be `memcpy`'d, mmap'd, or sent to another thread without pointer fix-ups.

The costs: you lose the borrow-checker's help (an index can dangle or point at the wrong node — it is a manual pointer), you need the `Ast` in hand to dereference any node (`ast.nodes[id]`), and recursive algorithms become "follow this index" instead of "follow this pointer," which is a small ergonomic tax. But for a compiler the locality and allocation wins dominate. **rustc** arena-allocates and interns; **Zig's** parser produces a flat `Ast` with a `MultiArrayList` of nodes; **Carbon** was explicitly designed around a flat parse tree stored as an array, citing data-oriented performance as a core goal.

### 3. Struct-of-arrays: pushing locality further

The flat AST above is still *array-of-structs* (AoS): each `Node` holds its tag, operands, and maybe a span inline, so the struct is as wide as its biggest variant. **Struct-of-arrays (SoA)** splits each field into its own parallel array:

```text
AoS (array of structs):        SoA (struct of arrays):
 nodes: [ {tag,a,b,span},        tags:  [tag, tag, tag, ...]
          {tag,a,b,span},        lhs:   [a,   a,   a,   ...]
          ... ]                  rhs:   [b,   b,   b,   ...]
                                 spans: [span,span,span,...]
```

Why bother? Because a pass that only reads tags (say, "count all `Call` nodes") streams through the `tags` array touching *only* tags — no span bytes pollute the cache lines. Each pass pays for exactly the fields it uses. **Zig's `MultiArrayList`** is precisely this: the AST is stored SoA, so the tokenizer/parser and later passes each touch only the columns they need. The cost is ergonomic — you index three arrays instead of dereferencing one struct — and SoA only pays off when passes are field-selective. It is the most aggressive locality move and the one most tied to a specific compiler's access patterns.

### 4. Interning: store each unique thing once

A million-line program mentions the identifier `i`, the type `i32`, and the literal `0` countless times. Storing each occurrence as its own string/heap allocation is wasteful and makes comparison expensive (string compare). **Interning** deduplicates: each unique value is stored once in a table, and everywhere else holds a small integer id into that table.

```rust
// Instead of String everywhere:
struct Symbol(u32);              // an interned-string id
// `i` is always Symbol(7); comparing two names is comparing two u32s.
```

Interning turns identifier and type equality from O(length) string/structural comparisons into O(1) integer comparisons, shrinks memory dramatically, and is foundational to fast name resolution. rustc interns symbols, types, and many other things; the `Ty` you compare in type checking is an interned pointer, so type equality is a pointer/id comparison, not a deep structural walk. Interning is the natural companion to a flat AST: both replace fat, scattered, deeply-compared data with small, dense, cheaply-compared ids.

### 5. Red-green trees: immutability + incrementality

IDEs have a brutal constraint: **re-analyze on every keystroke, within a frame.** Reparsing and re-type-checking the whole file each time is impossible for large files. The reuse strategy must be: keep the unchanged 99% and rebuild only what the edit touched. Roslyn's answer is the **red-green tree**, and it is worth understanding precisely because it solves two problems at once — immutability for safe sharing, and laziness for cheap parent/position access.

**Green tree (the substance).**
- Immutable. Once built, a green node never changes.
- Stores only *relative width* (how many characters it spans), **not absolute position**. This is the key trick: a node that knows only its width is *position-independent* and can be reused anywhere.
- Has no parent pointer (a parent pointer would tie it to one location and one tree version, defeating sharing).
- Fully shareable: the same green subtree can appear in many tree versions.

**Red tree (the facade).**
- Lazily created on demand as you navigate down from the root.
- Adds the two things green lacks: a **parent pointer** and an **absolute position** (computed by summing widths from the root).
- Cheap and disposable; recomputed for each tree version, never stored long-term.

**Why two layers?** Parent pointers and absolute positions are exactly the data that *changes* when you edit (insert a character and every following node's absolute position shifts; a node's parent depends on which tree it is in). By moving that volatile data into the throwaway red layer, the green layer becomes a stable, immutable, infinitely-shareable substrate. Edit one token: build a new green node for it, build new green nodes only along the spine from the edit to the root, and **reuse every other green subtree by reference.** A 100,000-node file with a one-character edit rebuilds maybe 20 green nodes. That is what makes Roslyn's IDE incremental.

The names are literally from the original whiteboard: green nodes were drawn in green (the persistent data), red nodes in red (the facade). The pattern is not Roslyn-exclusive — Swift's **libSyntax**/SwiftSyntax used the same idea, and the broader **persistent data structure** literature (Okasaki) is the theory underneath.

### 6. Putting it together: which design for which job

There is no universally best layout; there is a best layout *for a goal*:

| Goal | Layout |
| --- | --- |
| Teaching, small interpreter, prototyping | Pointer tree (`Box`/`unique_ptr`). Simplest. |
| Batch compiler, parse-once-analyze-many, max throughput | Flat/arena, index-based, interned (rustc, Zig, Carbon). |
| Field-selective passes, extreme locality | Struct-of-arrays flat AST (Zig `MultiArrayList`). |
| IDE, edit-on-every-keystroke, incremental reuse | Red-green tree (Roslyn, SwiftSyntax). |
| Source-faithful rewriting + incrementality | Full-fidelity red-green (Roslyn keeps trivia too). |

A real toolchain may use *several*: a flat arena AST for the batch compiler path and a red-green-style tree for the IDE path over the same language. The layout follows the workload, and a professional engineer chooses it deliberately rather than defaulting to the pointer tree because it is what the textbook drew.

### 7. Memory reclamation and lifetime

The layout dictates the lifetime model. A pointer tree is reclaimed node-by-node (GC, refcount, or recursive drop). An **arena** is reclaimed *all at once*: the entire AST lives as long as the arena, and freeing the arena frees every node in one operation — perfect for a compiler where the AST has a clear phase lifetime and individual nodes are never freed early. This is why arenas pair so naturally with compilers: there is no "free this one node" use case; you build the tree, use it for a phase or the whole run, then drop it wholesale. The flip side: you cannot cheaply free part of the tree, and a long-lived arena can hold memory you are "done" with. For incremental/IDE workloads the red-green tree's *persistent* model (old versions garbage-collected when no longer referenced) is the better fit. Match the reclamation strategy to whether the AST's lifetime is *batch* (arena) or *evolving* (persistent).

## Code Examples

### A flat, index-based AST with a traversal (Rust)

```rust
type NodeId = u32;

#[derive(Clone, Copy)]
enum Node {
    Lit(i64),
    BinOp { op: u8, lhs: NodeId, rhs: NodeId },
}

struct Ast {
    nodes: Vec<Node>,    // ONE backing allocation
    spans: Vec<(u32, u32)>, // parallel: span of nodes[i]
}

impl Ast {
    fn new() -> Self { Ast { nodes: Vec::new(), spans: Vec::new() } }

    fn push(&mut self, node: Node, span: (u32, u32)) -> NodeId {
        let id = self.nodes.len() as NodeId;
        self.nodes.push(node);
        self.spans.push(span);   // span travels in lockstep — never orphaned
        id
    }

    // Evaluate by following indices, not pointers. No allocation, great locality.
    fn eval(&self, id: NodeId) -> i64 {
        match self.nodes[id as usize] {
            Node::Lit(n) => n,
            Node::BinOp { op, lhs, rhs } => {
                let l = self.eval(lhs);
                let r = self.eval(rhs);
                match op { b'+' => l + r, b'*' => l * r, _ => unreachable!() }
            }
        }
    }
}

fn main() {
    // Build  (2 + 3) * 4  bottom-up, recording spans.
    let mut ast = Ast::new();
    let two  = ast.push(Node::Lit(2), (1, 2));
    let three = ast.push(Node::Lit(3), (5, 6));
    let sum  = ast.push(Node::BinOp { op: b'+', lhs: two, rhs: three }, (1, 6));
    let four = ast.push(Node::Lit(4), (11, 12));
    let prod = ast.push(Node::BinOp { op: b'*', lhs: sum, rhs: four }, (1, 12));
    println!("{}", ast.eval(prod));   // 20
}
```

Every node lives in one `Vec`; "children" are `u32` indices; the span array runs parallel so a node and its span are always found by the same index.

### A red-green tree, sketched (pseudocode)

```text
// GREEN: immutable, width-only, no parent, fully shared.
struct GreenNode {
    kind: SyntaxKind,
    width: u32,                 // RELATIVE width, not absolute position
    children: Vec<GreenNode>,   // shared by reference across versions
}

// RED: lazy facade adding parent + absolute position.
struct RedNode<'a> {
    green:  &'a GreenNode,
    parent: Option<&'a RedNode<'a>>,
    offset: u32,                // absolute position, computed on demand
}

// EDIT: replace one token. Only the spine to the root is new green;
// every sibling subtree is reused by reference.
fn with_replaced_leaf(root: &GreenNode, path: &[usize], new_leaf: GreenNode) -> GreenNode {
    if path.is_empty() { return new_leaf; }
    let (i, rest) = (path[0], &path[1..]);
    let mut children = root.children.clone();         // shallow: shares siblings
    children[i] = with_replaced_leaf(&root.children[i], rest, new_leaf);
    GreenNode { kind: root.kind, width: recompute(&children), children }
}
```

The red layer is never stored long-term; you build it on the way down to ask "where am I?", then drop it. A one-token edit rebuilds only `path.len()` green nodes.

### Interning identifiers (Rust)

```rust
use std::collections::HashMap;

#[derive(Clone, Copy, PartialEq, Eq, Hash)]
struct Symbol(u32);

#[derive(Default)]
struct Interner { map: HashMap<String, Symbol>, strs: Vec<String> }

impl Interner {
    fn intern(&mut self, s: &str) -> Symbol {
        if let Some(&sym) = self.map.get(s) { return sym; }
        let sym = Symbol(self.strs.len() as u32);
        self.strs.push(s.to_owned());
        self.map.insert(s.to_owned(), sym);
        sym
    }
    fn resolve(&self, sym: Symbol) -> &str { &self.strs[sym.0 as usize] }
}

fn main() {
    let mut it = Interner::default();
    let a1 = it.intern("counter");
    let a2 = it.intern("counter");
    assert_eq!(a1, a2);          // same id; name comparison is now O(1)
}
```

Once `counter` is `Symbol(n)`, every name comparison in name resolution is a `u32` equality instead of a string compare — and the string is stored exactly once.

## Trade-offs

| You gain... | ...at the cost of... |
| --- | --- |
| Flat/arena AST: one allocation, cache locality, fast build/free | Manual "pointers" (indices can dangle/alias); need the arena to deref |
| Struct-of-arrays: pay only for fields a pass touches | Ergonomics (index parallel arrays); only wins for field-selective passes |
| Interning: O(1) equality, huge memory savings | An intern table to thread through; ids are meaningless without it |
| Red-green tree: cheap incremental edits, safe sharing, full fidelity | Two layers to implement; red recomputation; conceptual overhead |
| Arena reclamation: free the whole AST in one op | Cannot cheaply free part of the tree; may hold memory you're "done" with |
| Pointer tree: simplest, borrow-checker-friendly, looks like grammar | Slow at scale: N allocations, cache misses, fat nodes |

## Coding Patterns

### 1. Index newtypes, not raw integers

Wrap node ids in a typed handle (`struct ExprId(u32)`) so you cannot accidentally index the wrong arena with the wrong id. Recovers some of the type safety that raw indices lose.

### 2. Parallel arrays kept in lockstep

If `spans[i]` is the span of `nodes[i]`, *only ever* push to both together (or wrap the pair in one `push`). A drifted parallel array is a silent corruption.

### 3. Width-only nodes for shareable trees

Store relative widths, not absolute positions, on any node you want to reuse across versions. Compute absolute position lazily from the root. This is the red-green discipline distilled.

### 4. Intern early, compare by id

Intern identifiers/types/literals at construction time; downstream, compare ids, never the underlying strings/structures.

### 5. Arena per phase

Allocate the AST in an arena scoped to the phase (or run) that needs it; drop the arena to reclaim everything at once. No per-node lifetime bookkeeping.

## Best Practices

- **Default to a pointer tree only for prototypes.** The moment performance or scale matters, move to a flat/arena, index-based layout — that is what the production compilers did.
- **Choose layout by workload:** batch → arena; incremental/IDE → red-green/persistent. Don't force one model onto both paths.
- **Intern everything compared by equality** (names, types, common literals). It is one of the highest-leverage memory and speed wins.
- **Keep volatile data (absolute position, parent) out of shareable nodes.** Width + lazy red facade is the pattern.
- **Measure before micro-optimizing layout.** SoA only pays for field-selective passes; profile that your passes are actually column-selective before paying SoA's ergonomic cost.
- **Use typed handles** to claw back safety lost when pointers became indices.
- **Make span/position travel with the node mechanically** (parallel arrays pushed together, or width carried on the node) so it is never orphaned.

## Edge Cases & Pitfalls

- **Dangling/aliasing indices.** A `NodeId` is a manual pointer: it can point at a freed arena, the wrong arena, or a stale slot. The borrow checker cannot help. Typed handles + a single owning arena mitigate.
- **SoA hurting non-selective passes.** A pass that reads *every* field of *every* node may be slower in SoA (it now stride-jumps across arrays) than in AoS. SoA is not universally faster.
- **Red-tree thrash.** Repeatedly rebuilding red facades in a hot loop (e.g., naive repeated `parent`/`position` queries) can dominate; cache the red nodes you revisit.
- **Interner as a bottleneck.** A single global interner behind a lock can serialize a parallel front end; shard or use a concurrent interner.
- **Arena holding memory too long.** A long-lived arena pins every node's memory even after a phase is done; scope arenas tightly.
- **Serialization assuming pointer stability.** Flat ASTs serialize cleanly *only* if ids are array indices, not addresses; mixing the two breaks mmap/round-trip.
- **Forgetting that green widths must be recomputed** up the spine after an edit; a stale width corrupts all downstream absolute positions.

## Common Mistakes

1. **Defaulting to `Box<Expr>` everywhere in a performance-sensitive compiler** and then being surprised parsing is allocation-bound.
2. **Storing absolute positions on nodes you want to reuse** — every edit invalidates them, killing structural sharing.
3. **Putting parent pointers on green nodes** — ties them to one tree, defeating sharing entirely.
4. **Reaching for SoA without profiling** that passes are field-selective; paying ergonomics for no locality win.
5. **Comparing identifiers by string** in name resolution instead of interning and comparing ids.
6. **Using raw `u32` ids** that get crossed between two arenas, indexing nonsense without a compile error.
7. **Refcounting or GC-ing a batch AST** that wants a single wholesale arena free.
8. **Re-creating red nodes in a tight loop** and calling it "the red-green tree is slow."

## Tricky Points

- **rust-analyzer uses `rowan`**, a red-green (concrete-syntax) library, while **rustc** uses a flat-ish arena HIR — same language, two layouts, because one path is IDE-incremental and the other is batch.
- **Green nodes can be interned too** — Roslyn deduplicates small green nodes (e.g., a `;` token, common keywords) so the *substance* itself is shared across the whole tree, not just across versions.
- **A flat AST's recursion still uses the call stack** — index-following `eval` can still overflow on deep trees; production code sometimes uses an explicit work-stack regardless of layout.
- **Carbon's parse tree is post-order-flattened** — children before parents in the array — which lets some passes run as a single linear scan with an explicit stack, no recursion at all.
- **Interned `Ty` equality is pointer equality** in rustc: two types are equal iff they are the *same* interned instance, which is why interning must be canonical (structurally-equal types intern to one instance).
- **Red-green is a persistent data structure**, so old tree versions remain valid and are GC'd only when nothing references them — multiple analyses can hold different versions concurrently.
- **Width-only nodes make "absolute position" an O(depth) computation**, not O(1); usually fine, but a reason red nodes cache their offset.

---

## Apply it

1. Define the user or business outcome that **Abstract Syntax Trees** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Abstract Syntax Trees?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
