# Module Graph Pruning — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Module Graph Pruning** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### What the module graph is

Imagine your project requires module `A`. `A`'s `go.mod` requires `B` and `C`. `B`'s `go.mod` requires `D`. The module graph is the whole web:

```
you → A → B → D
        → C
```

To pick the correct versions, Go reads `go.mod` files along these edges. The question pruning answers is: *how many of these `go.mod` files does Go actually need to read?*

### The full graph (pre-1.17): read everything

Before Go 1.17, Go loaded *every* `go.mod` in the transitive closure — `A`, `B`, `C`, `D`, and everything below them, even modules that only mattered for `D`'s own tests or `D`'s own niche features that your code never reaches.

On a small project this is fine. On a large one (think Kubernetes, or any service with hundreds of dependencies), it meant loading thousands of `go.mod` files for *every* `go` command. Slow, and full of irrelevant detail.

### The pruned graph (1.17+): read only what matters

Pruning says: load the `go.mod` files of your **direct** dependencies, plus enough of their dependencies to cover what you actually import — and stop there. The deep, irrelevant parts of the graph are *pruned away*.

The trade-off: for the graph to stay *self-contained* (so the build is reproducible without loading those pruned parts), your own `go.mod` must now record a few more `// indirect` requirements than before. Go writes them for you. That is why modern `go.mod` files are bigger.

### The `go` directive is the switch

```
go 1.17
```

- `go 1.17` or higher → **pruned** graph. Bigger `go.mod`, faster commands.
- `go 1.16` or lower → **full** graph. Smaller `go.mod`, slower commands, old behaviour.

You opt in by bumping the directive and running `go mod tidy`. Go fills in the extra indirect requirements automatically.

### Why `go.mod` grew: the second `require` block

In a pruned module, `go.mod` must list enough indirect dependencies to describe the build on its own — without Go having to load the deep graph to find them. So a tidy modern `go.mod` typically has **two** `require` blocks:

```
require (
    github.com/spf13/cobra v1.8.0   // your direct deps
    github.com/google/uuid v1.6.0
)

require (
    github.com/inconshreveable/mousetrap v1.1.0 // indirect
    github.com/spf13/pflag v1.0.5 // indirect
    // ... more indirect deps ...
)
```

The first block is what *you* import. The second block, all marked `// indirect`, is what your dependencies pull in — recorded so the pruned graph is complete. This convention (direct in one block, indirect in another) is what `go mod tidy` produces.

### Pruning does not change *which* versions you get

This is the key reassurance. Pruning changes *how much of the graph Go loads*, not *which versions it selects*. MVS still picks the same versions. Your build is the same — it is just computed faster. (There are rare deepening cases, covered at higher levels, but for everyday work: same versions, faster.)

---

## Code Examples

### Example 1 — Create a pruned module and look at `go.mod`

```bash
mkdir prunedemo
cd prunedemo
go mod init example.com/prunedemo
cat go.mod
```

A fresh `go.mod` on a modern Go:

```
module example.com/prunedemo

go 1.23
```

The `go 1.23` directive means this module is pruned from the start.

### Example 2 — Add a dependency and watch the indirect block appear

Write `main.go` using `cobra`, which has several transitive dependencies:

```go
package main

import (
    "fmt"

    "github.com/spf13/cobra"
)

func main() {
    root := &cobra.Command{
        Use: "demo",
        Run: func(cmd *cobra.Command, args []string) {
            fmt.Println("hello from demo")
        },
    }
    _ = root.Execute()
}
```

Tidy:

```bash
go mod tidy
cat go.mod
```

You will see something like:

```
module example.com/prunedemo

go 1.23

require github.com/spf13/cobra v1.8.0

require (
    github.com/inconshreveable/mousetrap v1.1.0 // indirect
    github.com/spf13/pflag v1.0.5 // indirect
)
```

The single direct dependency (`cobra`) is in the first `require`. The two indirect dependencies that `cobra` needs are recorded in the second block. This is pruning in action: `go.mod` lists what is needed so the deep graph does not have to be loaded.

### Example 3 — Read the two blocks

```
require github.com/spf13/cobra v1.8.0
```

This is **direct**: your `main.go` imports `github.com/spf13/cobra`.

```
require (
    github.com/inconshreveable/mousetrap v1.1.0 // indirect
    github.com/spf13/pflag v1.0.5 // indirect
)
```

These are **indirect**: you never import them, but `cobra` does, so they are recorded to keep the pruned `go.mod` self-contained.

### Example 4 — See the pruned graph

```bash
go mod graph
```

Each line is `from@version to@version`, one edge of the graph. On a pruned module this output is shorter and more focused than it would have been pre-1.17.

### Example 5 — Compare against an old `go` directive

Temporarily downgrade the directive to see the difference (do not commit this):

```bash
go mod edit -go=1.16
go mod tidy
cat go.mod
```

With `go 1.16`, Go uses the **full** graph. The `go.mod` `tidy` produces records *fewer* indirect dependencies (only those needed for completeness under the old rules), because the full graph is loaded to fill gaps at build time instead of being recorded up front. Restore it:

```bash
go mod edit -go=1.23
go mod tidy
```

### Example 6 — Confirm the build is identical

```bash
go build ./...
go list -m all
```

`go list -m all` prints the build list — the selected version of every module. Pruning did not change these versions; it only changed how Go computed them. Same build, faster.

---

## Coding Patterns

### Pattern: bump the `go` directive deliberately

When you want pruning (you almost always do), set a modern directive and tidy:

```bash
go mod edit -go=1.21
go mod tidy
git add go.mod go.sum
git commit -m "Enable module graph pruning (go 1.21)"
```

Do this as its *own* commit. The `go.mod` diff will be large (the indirect block grows); isolating it keeps that diff out of feature reviews.

### Pattern: tidy after every dependency change

```bash
go get example.com/foo@v1.5.0
go mod tidy
```

`tidy` re-derives the indirect block for the pruned graph. Skipping it leaves `go.mod` inconsistent.

### Pattern: CI verification that `go.mod` is tidy

```bash
go mod tidy
git diff --exit-code go.mod go.sum
```

If `tidy` would change anything, a contributor forgot to run it. This catches stale indirect blocks.

### Pattern: do not hand-curate the indirect block

The second `require` block is generated. Resist the urge to delete `// indirect` lines you "do not recognise" — they are there to keep the pruned graph complete. `go mod tidy` owns that block.

---

## Clean Code

- **Keep the `go` directive current.** A modern directive (`go 1.21`+) gives you pruning and clearer `go.mod` files.
- **Let `go mod tidy` manage the indirect block.** Never hand-edit `// indirect` lines.
- **Commit `go.mod` and `go.sum` together.** They are a pair; splitting them leaves the repo inconsistent.
- **Isolate `go`-directive bumps** in their own commit so the large `go.mod` diff is reviewable on its own.
- **Run `tidy` before pushing.** A CI gate (above) makes this non-optional.
- **Read `go.mod`, not just diffs.** The two-block structure tells you direct-vs-indirect at a glance.

---

## Error Handling

Pruning itself rarely produces errors; the surrounding `go.mod` discipline does.

### "go.mod file indicates go 1.16, but maximum version supported by tidy is ..."

You ran `go mod tidy` flags incompatible with your directive. Fix: align the `-go` flag (or the directive) with your toolchain. Usually just `go mod tidy` with no extra flags.

### "missing go.sum entry for module providing package ..."

A package's module is in the graph but its hash is missing from `go.sum`. Fix: `go mod tidy` (or `go mod download`) to populate `go.sum`.

### "updates to go.mod needed; to update it: go mod tidy"

You built with `-mod=readonly` (the default) and the pruned `go.mod` is missing a required indirect entry. Fix: `go mod tidy`, commit the result.

### `go.mod` keeps growing on every `tidy`

Not an error — expected. Each new dependency can add indirect entries. If it grows *unexpectedly*, a dependency added a new requirement; check `go mod why` for the surprising module.

### Inconsistent `go.mod` after a merge

A merge brought in `require` lines from another branch without re-tidying. Fix: `go mod tidy`, resolve, commit.

---

## Security Considerations

- **`go.sum` still protects you.** Pruning changes which `go.mod` files load, not the integrity guarantees. Every module that ends up in your build is still hash-verified against `go.sum`.
- **A self-contained `go.mod` is auditable.** The indirect block makes the *recorded* dependency set explicit, which helps reviewers and SBOM tools see what is in scope.
- **Do not delete indirect entries to "clean up."** Removing a `// indirect` line can make the pruned graph incomplete and, at worst, change which versions get selected. Let `tidy` manage it.
- **Vulnerability scanning is unaffected.** `govulncheck` analyses the actual build, which pruning does not change. Run it as usual.
- **Smaller graphs reduce attack surface for graph-load tooling**, but the real security boundary remains `go.sum` plus your review of dependency changes.

---

## Performance Tips

- **The whole point is performance.** Being on a `go 1.17+` directive is the single biggest "optimization" — it makes graph loading cheap.
- **Keep dependencies tidy.** Unused requires bloat the indirect block and the graph. `go mod tidy` regularly.
- **Prefer modern dependencies.** Libraries whose own `go.mod` is at `go 1.17+` participate in pruning better, keeping the deep graph small.
- **Use `go mod graph | wc -l`** to see how many edges your graph has. A pruned module's number is much smaller than the equivalent unpruned one.
- **Do not downgrade the directive** to shrink `go.mod`. You would trade a small file for a slow, full-graph build. The pruned, larger `go.mod` is the faster choice.

---

## Best Practices

1. **Stay on a modern `go` directive.** `go 1.21`+ in 2026. Pruning is automatic.
2. **Run `go mod tidy` after every dependency change.** It keeps the indirect block correct.
3. **Verify tidiness in CI** with `git diff --exit-code go.mod go.sum`.
4. **Isolate `go`-directive bumps** in dedicated commits.
5. **Trust the indirect block.** Do not hand-prune it.
6. **Read the two-block structure** to understand direct vs indirect at a glance.
7. **Commit `go.mod` and `go.sum` together.**
8. **Upgrade old modules.** A `go 1.16` module misses pruning entirely; bump and tidy.

---

## Edge Cases & Pitfalls

### Pitfall 1 — "My `go.mod` exploded, did I do something wrong?"

No. Bumping to `go 1.17+` and running `tidy` legitimately adds many `// indirect` lines. That is pruning making `go.mod` self-contained. The file is bigger *on purpose*.

### Pitfall 2 — Deleting indirect lines to shrink the file

Every junior tries this. Removing a `// indirect` entry can break the pruned graph's completeness and is undone (or flagged) by the next `tidy`. Leave the block alone.

### Pitfall 3 — Forgetting to tidy after `go get`

You add a dependency but skip `tidy`. The indirect block is now stale, and CI's `-mod=readonly` build fails with "updates to go.mod needed." Always `go get` then `go mod tidy`.

### Pitfall 4 — Confusing graph pruning with `tidy`'s pruning

`go mod tidy` removes *unused* requires. Module graph pruning trims what Go *loads*. Different operations; both involve the word "prune."

### Pitfall 5 — Expecting pruning to change versions

Pruning loads less of the graph but selects the same versions (except rare deepening cases at senior level). If a version changed, something else (a `go get`, a new requirement) caused it, not pruning.

### Pitfall 6 — Mixing old and new directives in a monorepo

A repo with some `go 1.16` modules and some `go 1.21` modules behaves inconsistently. Standardize on a modern directive everywhere.

### Pitfall 7 — Reading `go mod graph` and expecting the old size

A pruned graph is intentionally smaller. If you remember a huge graph from pre-1.17, the new compact output is correct, not truncated.

---

## Common Mistakes

- **Hand-editing the `// indirect` block.** It is generated. Use `go mod tidy`.
- **Skipping `go mod tidy` after dependency changes.** Leaves the indirect block stale.
- **Staying on an old `go` directive** to keep `go.mod` small. You lose pruning's speed.
- **Assuming pruning changed your versions.** It almost never does.
- **Treating the two `require` blocks as a mistake** and merging or deleting them. The split is intentional.
- **Committing `go.mod` without `go.sum`** (or vice versa).
- **Mixing `go 1.16` and `go 1.21` modules** in one repo without realizing they load graphs differently.

---

## Common Misconceptions

> *"Pruning makes my project smaller."*

It makes the *graph Go loads* smaller, but it makes your `go.mod` file *bigger* (the indirect block). Net effect: faster commands, larger `go.mod`.

> *"The indirect block is bloat I should clean up."*

No. Those entries keep the pruned graph self-contained. Deleting them breaks the model; `tidy` owns them.

> *"Pruning changes which dependency versions I use."*

Almost never. It changes how the graph is loaded, not what MVS selects. (Rare deepening cases exist; see senior level.)

> *"I have to enable pruning manually."*

You enable it via the `go` directive — and `go mod init` already writes a modern one. It is on by default for new modules.

> *"Pruning is a build flag."*

No. It is governed by the `go 1.x` directive in `go.mod`, not by a command-line flag.

> *"My old `go 1.15` project is pruned too."*

No. Modules at `go 1.16` or lower use the full graph. Only `go 1.17+` modules are pruned.

---

## Tricky Points

- **The `go` directive is the switch.** `1.17`+ → pruned; `1.16`- → full. One line decides.
- **`go.mod` grew on purpose.** A self-contained pruned `go.mod` must list more indirect deps.
- **Two `require` blocks is the convention,** not a rule — `tidy` produces direct in one, indirect in another for readability. A single block also works.
- **Pruning is per-main-module.** Whether *you* prune depends on *your* `go.mod`'s directive, not your dependencies'.
- **`go mod graph` reflects pruning.** Its output is smaller for pruned modules.
- **MVS still runs.** Pruning feeds MVS a smaller graph; MVS still picks one version per module. See [04-minimal-version-selection-mvs](../04-minimal-version-selection-mvs/junior.md).
- **`go.sum` is independent.** Integrity hashing happens regardless of pruning.

---

## Apply it

1. Choose one small, known input for **Module Graph Pruning**.
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

- What problem does Module Graph Pruning solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
