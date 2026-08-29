# DSLs in Practice — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **DSLs in Practice** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Compiling a DSL: bytecode and beyond

Tree-walking is `O(tree size)` of pointer chasing per evaluation — fine for config evaluated once, ruinous for a rule run on every request. The standard upgrade path:

- **AST → bytecode → VM.** Compile the tree once into a flat opcode array (`PUSH 18`, `LOAD age`, `GT`, `JMPF ...`). A stack-machine loop executes it. This removes recursion overhead and dramatically improves cache behaviour; 5–50× over tree-walking is typical. Lua, Python, and most embedded scripting languages work this way, and it is the right model for a hot rules DSL.
- **AST → host source (transpile).** Emit Go/JS/C from the AST, compile it with the host toolchain, and call it. You inherit a real optimiser. Good when the DSL is fixed at deploy time, not edited live.
- **AST → SQL.** The dominant case for query/filter DSLs. Push the work into the database engine. The database's planner, indexes, and parallelism are yours for free.
- **AST → LLVM IR → native.** The heavyweight option: generate LLVM IR and let LLVM produce optimised machine code. Justified only for compute-heavy DSLs run at scale (numerical/financial expression languages, query JITs). Most DSLs never need it.

Choosing among these is an explicit trade of build complexity against runtime speed and operability.

### 2. Sandboxing untrusted DSLs — the core senior skill

If outsiders supply DSL source, you must treat the evaluator as a security boundary. The guarantees you need:

- **No arbitrary code execution.** The DSL must *not* be implemented by translating to `eval()` of host code, by reflecting into host functions, or by exposing the host's standard library. Every operation the DSL can perform is one *you* explicitly implemented. This is the decisive advantage of an external DSL: its powers are exactly the opcodes/builtins you wrote.
- **Bounded CPU / steps.** Enforce a **fuel/gas** counter or a step limit; abort when exceeded. Without this, `while true {}` (if you were unwise enough to add loops) or even a deep expression can hang a worker.
- **Bounded memory.** Cap allocation — list sizes, string lengths, recursion depth — so a crafted input cannot OOM the process.
- **Bounded time.** A wall-clock deadline as a backstop, ideally enforced out-of-process or via cooperative checks.
- **No ambient authority.** The DSL cannot open files, make network calls, spawn processes, or read environment variables unless you *explicitly* expose a narrow, audited capability (e.g. a `lookup(customerId)` builtin that only reads one table).
- **Allow-list, not deny-list.** Grant the small set of fields/functions the DSL needs. Never start from "everything" and try to subtract dangerous things — you will miss one.

The cleanest sandbox is a **terminating (total) language**: no unbounded loops or recursion at all, so it provably halts. Dhall and CUE are designed this way precisely so untrusted config cannot loop forever. If your domain allows it, *not* having loops is the strongest sandbox you can ship.

### 3. Versioning and evolving the grammar

Once files exist in the wild, the grammar is an API. Treat changes like API changes:

- **Add, don't reshape.** New optional keywords/clauses are usually backward-compatible; renaming or removing breaks files.
- **Version markers.** A `version = 2` header (or file extension, or schema field) lets the parser select grammar rules and lets you run old and new in parallel.
- **Deprecation with warnings.** Emit a warning (with position) for soon-to-be-removed syntax before deleting it.
- **Mechanical migration.** Because you own the parser, you can write a tool that parses v1, transforms the AST, and *prints* v2 — automatic upgrades for users. Your formatter and your migrator share the AST-to-source printer.
- **A conformance test corpus.** Keep a frozen set of real-world files and their expected results; run them on every grammar change to catch regressions.

### 4. The tooling burden

A DSL people live in needs more than a parser:

- **Syntax highlighting.** A TextMate grammar / Tree-sitter grammar / regex set for editors. Cheap but expected.
- **A formatter.** Canonical layout (your AST-to-source printer again). Eliminates style arguments; enables clean diffs.
- **A language server (LSP).** Reuses your front end to provide *as-you-type* errors, completion (you know the valid keywords/fields), hover docs, and go-to-definition — across VS Code, Neovim, JetBrains, etc., from one server. This is where most of the maintenance cost of a successful DSL goes.
- **Documentation and a playground.** A browser REPL that runs the interpreter on sample input shortens the learning curve enormously.

The honest senior framing: **a DSL is not the parser; it is the parser plus a language to maintain plus tooling, forever.** That total cost is the real "build a DSL vs use a library/config" decision.

### 5. The accidental-programming-language trap

Config formats famously slide into Turing-completeness: someone adds variables "for DRY," then conditionals "for environments," then functions, then loops. The endpoint is a slow, untyped, untooled, *unsandboxable* programming language that nobody designed. Real-world lineage includes templating languages that grew control flow and YAML-based CI configs that sprouted expression mini-languages. The defenses:

- **Decide up front whether the language is total** (no loops/recursion) and *enforce* it in the grammar.
- **Push computation out.** If users need real logic, give them a way to call out to *reviewed host functions*, not a way to write logic inside the config.
- **Say no.** Each feature request is weighed against the permanent cost and the loss of safety/analysability. "Use a real programming language for that" is often the right answer.

---

## Code Examples

### A bytecode VM for an expression DSL

Compile the AST once to opcodes, then run a stack machine. This is the standard performance upgrade from tree-walking.

```python
# --- compile AST -> bytecode ---
def compile_expr(node, code):
    kind = node[0]
    if kind == "number":
        code.append(("PUSH", node[1]))
    elif kind == "var":
        code.append(("LOAD", node[1]))
    elif kind == "binop":
        compile_expr(node[2], code)         # left
        compile_expr(node[3], code)         # right
        code.append(("OP", node[1]))        # +, -, *, /
    return code

# --- the VM: a stack machine with a fuel limit (sandbox) ---
def run_vm(code, env, fuel=10_000):
    stack = []
    for op, arg in code:
        fuel -= 1
        if fuel <= 0:
            raise RuntimeError("execution budget exceeded")   # bound CPU
        if op == "PUSH":  stack.append(arg)
        elif op == "LOAD":
            if arg not in env:                                # allow-list vars
                raise RuntimeError(f"unknown variable {arg}")
            stack.append(env[arg])
        elif op == "OP":
            b = stack.pop(); a = stack.pop()
            stack.append({"+":a+b,"-":a-b,"*":a*b,"/":a/b}[arg])
    return stack.pop()

tree = ("binop", "+", ("var", "x"), ("binop", "*", ("number", 4), ("number", 2)))
code = compile_expr(tree, [])
print(code)                       # [('LOAD','x'),('PUSH',4),('PUSH',2),('OP','*'),('OP','+')]
print(run_vm(code, {"x": 3}))     # 11
```

Notice the two sandbox controls baked into the VM: a **fuel counter** bounding CPU, and **variable access through an allow-listing env** — there is no opcode that touches the file system, the network, or host code, by construction.

### Sandboxing a customer-supplied rules DSL

A formula/rules language evaluated on untrusted input. The whole defense is: *the only things it can do are the things this evaluator implements.*

```python
import time

class Sandbox:
    def __init__(self, fields, *, step_limit=5000, time_limit=0.05):
        self.fields = fields                 # allow-listed, read-only inputs
        self.step_limit = step_limit
        self.time_limit = time_limit

    def eval(self, node):
        self.steps = 0
        self.deadline = time.monotonic() + self.time_limit
        return self._eval(node)

    def _tick(self):
        self.steps += 1
        if self.steps > self.step_limit:
            raise RuntimeError("step limit exceeded")
        if time.monotonic() > self.deadline:
            raise RuntimeError("time limit exceeded")

    def _eval(self, node):
        self._tick()
        kind = node[0]
        if kind == "number":  return node[1]
        if kind == "field":                  # ONLY the allow-listed inputs
            name = node[1]
            if name not in self.fields:
                raise RuntimeError(f"field not allowed: {name}")
            return self.fields[name]
        if kind == "and":  return self._eval(node[1]) and self._eval(node[2])
        if kind == "or":   return self._eval(node[1]) or  self._eval(node[2])
        if kind == "cmp":
            _, op, a, b = node
            x, y = self._eval(a), self._eval(b)
            return {">":x>y, "<":x<y, "=":x==y, ">=":x>=y, "<=":x<=y}[op]
        # NOTE: there is deliberately NO node type for calling host functions,
        # importing, file I/O, loops, or recursion. The language is total.
        raise RuntimeError(f"illegal node {kind}")

sb = Sandbox(fields={"age": 25, "country": "US"})
rule = ("and", ("cmp", ">", ("field", "age"), ("number", 18)),
               ("cmp", "=", ("field", "country"), ("number", "US")))
print(sb.eval(rule))   # True
```

The security argument is *enumerable*: the `_eval` switch lists every power the language has. There is no path to host code, so there is nothing to escape into. Step and time limits bound cost; the field allow-list bounds reach. This is what "no arbitrary code execution" looks like in practice — and why it is far easier to guarantee for an external DSL than for an internal one embedded in the host.

### A formatter / migrator via an AST-to-source printer

One printer powers the formatter *and* the version-2 migrator.

```python
def to_source(node):
    kind = node[0]
    if kind == "number": return repr(node[1])
    if kind == "field":  return node[1]
    if kind == "cmp":    return f"{to_source(node[2])} {node[1]} {to_source(node[3])}"
    if kind == "and":    return f"{to_source(node[1])} and {to_source(node[2])}"
    if kind == "or":     return f"{to_source(node[1])} or {to_source(node[2])}"

# formatter: parse(text) -> to_source(ast)  yields canonical layout
# migrator:  parse_v1(text) -> transform(ast) -> to_source(ast)  yields v2 text
```

Because you own the parser and the printer, automatic, lossless upgrades for thousands of user files become a small program rather than a manual slog.

---

## Coding Patterns

### Pattern: AST → bytecode → stack VM

Compile once, execute many. Carry a fuel counter in the VM loop for an always-on CPU bound.

### Pattern: enumerable-capability evaluator

Implement the evaluator as an explicit switch over node types with *no* fall-through to host code. The switch *is* the security model and the audit surface.

### Pattern: resource budget threaded through evaluation

A `_tick()` called at every node decrements steps and checks a deadline. Wall-clock as a backstop; step count as the primary, deterministic limit.

### Pattern: allow-list capabilities, not deny-list

Inject the exact fields/functions the DSL may use. New powers require an explicit, reviewed addition.

### Pattern: one AST-to-source printer, many consumers

Formatter, version migrator, and "fix-it" suggestions all reuse it. Keep it total and round-trip-safe (`parse(to_source(ast)) == ast`).

### Pattern: conformance corpus in CI

Freeze representative real files plus expected outputs; run on every grammar/evaluator change to catch breakage and silent semantic drift.

---

## Best Practices

- **Treat the evaluator as a trust boundary** the instant any input is not fully controlled by your team. Allow-list, resource limits, no ambient authority — all three.
- **Prefer a total language.** If the domain does not need iteration, forbid it in the grammar and gain provable halting for free.
- **Compile only when measured.** Tree-walk until profiling shows the evaluator is hot; then move to bytecode. Don't pre-build a VM you don't need.
- **Transpile onto mature engines** (SQL, the host language) when semantics align — it is usually less code and more performance than a bespoke runtime.
- **Version the grammar from v1.** Ship a version marker and a conformance corpus before you have users, not after.
- **Own the AST-to-source printer.** It unlocks formatter, migrator, and fix-its, and it is the backbone of grammar evolution.
- **Budget for tooling.** If the DSL will be used daily, plan the LSP/highlighting/formatter as part of the project, not a someday. If you cannot fund tooling, reconsider building the DSL at all.
- **Defend the scope.** Write down what the language deliberately cannot do and review every feature request against it.

---

## Edge Cases & Pitfalls

- **The sandbox escape via a "helpful" builtin.** A `now()`, `lookup()`, or `http()` builtin added for convenience can reintroduce ambient authority or side channels. Every builtin is a security review; audit what it can reach.
- **Resource limit at the boundary.** What happens *exactly* when fuel hits zero mid-operation? Partial state, half-written output, or a misleading result are all hazards. Abort cleanly and atomically.
- **Step limits that aren't deterministic.** Wall-clock-only limits make the same input pass on a fast machine and fail on a slow one. Prefer a deterministic step/fuel count as the primary bound; use time only as a backstop.
- **Recursion depth as a DoS.** Even without loops, deeply nested expressions can blow the host stack during parsing or evaluation. Cap nesting depth in the parser.
- **Transpiler injection.** Emitting SQL/HTML/shell by string concatenation reintroduces injection. Parameterise or escape; never interpolate untrusted values into generated code.
- **Breaking changes disguised as additions.** A "new optional keyword" that changes the meaning of an existing one is a breaking change. Run the conformance corpus to prove backward compatibility.
- **Turing-completeness creep, one PR at a time.** Each feature looks harmless in isolation. The aggregate turns your safe config into an unsandboxable language. Re-evaluate the *whole* against the original scope, not just the diff.
- **Tooling rot.** A language server that lags the grammar gives wrong errors and erodes trust. Generate highlighting/completion data from the same grammar source where possible so they cannot drift.
- **Assuming the GIL or host VM bounds cost.** Host-level safety (a GIL, a memory-managed runtime) does not bound *your DSL's* execution. You must impose limits yourself.

You can now run an external DSL as a real product: compiled for speed where it matters, sandboxed for untrusted input, versioned for evolution, and tooled for daily use — without letting it metastasise into an accidental programming language. The `professional.md` level steps back to the *strategic* view: the org-wide build-vs-buy decision, total cost of ownership, governance of a DSL used by many teams, ANTLR-vs-hand-written at production scale, and the long-term maintenance and deprecation of a language your company depends on.

---

## Apply it

1. State the system invariant that **DSLs in Practice** must protect.
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

- Which invariant must remain true when DSLs in Practice fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
