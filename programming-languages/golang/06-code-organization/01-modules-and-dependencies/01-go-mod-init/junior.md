# `go mod init` — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **`go mod init`** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
## Core Concepts

### A module is just "a folder with a `go.mod` in it"

There is no magic. A module is a directory tree whose root contains a `go.mod` file. That is the entire definition. Move the folder, and you have moved the module. Delete the `go.mod`, and the module is gone — the folder reverts to just being a folder.

### `go mod init <path>` writes that file for you

You could write `go.mod` by hand. The two-line minimum is trivial:

```
module github.com/alice/hello

go 1.22
```

But `go mod init` does it for you, picks a sensible Go version line, and verifies the module path is plausible. That is its entire job. Everything else (`require`, `go.sum`, downloading dependencies) happens later, mostly automatically.

### The module path matters more than you think

The module path is **the name your code is known by everywhere**. If your module is `github.com/alice/hello`, then:

- Inside a sub-folder `greet/`, the import path of that package is `github.com/alice/hello/greet`.
- Anyone who wants to use your module writes `import "github.com/alice/hello"` in their code.
- The Go toolchain expects to be able to reach that path over the network if it needs to download the module.

Pick the module path carefully — changing it later means editing every import in every project that depends on you. We will come back to this in Best Practices.

### `go mod init` is a one-time event

You run `go mod init` once per module, on the day you create it. After that, you almost never touch `go.mod` directly — `go get`, `go mod tidy`, and the compiler edit it for you.

If you ever find yourself running `go mod init` a second time on the same directory, something has gone wrong. (We will cover the recovery path in Edge Cases & Pitfalls.)

### What `go mod init` does NOT do

- It does **not** create source files. No `main.go`, no `cmd/`, nothing.
- It does **not** create folders. The directory you run it in is the only one touched.
- It does **not** download anything from the network.
- It does **not** create `go.sum`. That file appears later, when you have dependencies.
- It does **not** initialise a Git repository. `go mod` and `git` are independent.

---

## Code Examples

### Example 1 — Minimal hello module

```bash
mkdir hello
cd hello
go mod init example.com/hello
```

Resulting `go.mod`:

```
module example.com/hello

go 1.22
```

That is a complete, valid Go module. Add a `main.go`:

```go
package main

import "fmt"

func main() {
    fmt.Println("hello, world")
}
```

Then:

```bash
go run .
```

Output:

```
hello, world
```

Notice you ran `go run .`, not `go run main.go`. The `.` means "the package in the current directory," and Go knows what package that is because of `go.mod`.

### Example 2 — Module on GitHub

```bash
mkdir cooltool
cd cooltool
go mod init github.com/alice/cooltool
```

`go.mod`:

```
module github.com/alice/cooltool

go 1.22
```

Now if you have a sub-folder `greet/greet.go`:

```go
package greet

import "fmt"

func Hello(name string) {
    fmt.Println("hello,", name)
}
```

You can use it from `main.go` at the module root:

```go
package main

import "github.com/alice/cooltool/greet"

func main() {
    greet.Hello("Alice")
}
```

The import path is `<module path>/<folder>`. Always.

### Example 3 — Module with a hyphenated name

```bash
go mod init github.com/alice/web-tool
```

`go.mod`:

```
module github.com/alice/web-tool

go 1.22
```

The module path can contain hyphens — but the **package name** inside Go source still has to be a valid Go identifier (no hyphens). So inside `web-tool` your `main.go` is still `package main`, and a sub-folder `pretty-print/` would have to declare `package prettyprint` (or any valid identifier) inside its `.go` files.

### Example 4 — Throwaway local module

If you never plan to publish:

```bash
go mod init scratch
```

`go.mod`:

```
module scratch

go 1.22
```

This works locally. Other people cannot `go get` your module (`scratch` is not a URL), and you cannot use it as a dependency in another project unless you `replace` it. But for personal experiments it is fine.

### Example 5 — Just looking at what changed

```bash
$ ls
$ go mod init example.com/hello
go: creating new go.mod: module example.com/hello
$ ls
go.mod
$ cat go.mod
module example.com/hello

go 1.22
```

That is the entire state change.

---

## Coding Patterns

### Pattern: One module, one repository

A single Git repository contains a single `go.mod` at the root. This is the default and the path of least resistance. Tools, IDEs, and CI assume this layout. Do not deviate without a reason.

### Pattern: Import-path-equals-folder-path

If your module is `github.com/alice/cooltool`, and you have a folder `internal/cache/`, the import path is exactly `github.com/alice/cooltool/internal/cache`. Always. There is no aliasing at the module level. Resist creating mental indirection.

### Pattern: Run `go mod init` from a fresh, empty folder

The cleanest workflow:

```bash
mkdir mything
cd mything
go mod init github.com/me/mything
git init
git add go.mod
git commit -m "init module"
```

Then start adding code. Doing it in this order avoids the next-most-common bug: `go.mod` written with the wrong path because someone ran the command from the wrong folder.

### Pattern: Module path as future URL

Even if you have not created the GitHub repository yet, choose the module path *as if* you had. This way, when you do push to GitHub, nothing has to change in `go.mod`. Future-you will thank present-you.

---

## Clean Code

- **The module path should match the canonical URL of the repository.** `github.com/alice/cooltool`, not `Cool-Tool` or `cooltool` or `cool_tool`.
- **Lowercase only.** Mixed-case module paths technically work but cause platform-portability headaches (Windows and macOS have case-insensitive filesystems by default; Linux does not).
- **No trailing slash.** Never `github.com/alice/cooltool/`.
- **No `.git` suffix.** Never `github.com/alice/cooltool.git`. The Go tools strip it but it looks unprofessional.
- **Pick a meaningful name.** `github.com/alice/util` is a poor choice; `github.com/alice/csvkit` is better.

A good module path is short, all lowercase, hyphenated when needed, and matches the repository URL.

---

## Error Handling

`go mod init` itself rarely fails, but here are the failure modes a junior will see:

### "go: cannot determine module path for source directory"

You ran `go mod init` with no argument inside a folder that does not look like a known repository. Fix: provide an explicit path:

```bash
go mod init github.com/alice/mything
```

### "go.mod already exists"

You ran `go mod init` twice. Fix: either accept the existing file (do nothing), or — if you need to change the path — open `go.mod` in an editor and change the first line manually. Do not delete `go.mod` to "start over" if you already have dependencies.

### "malformed module path"

You included characters that are not allowed (uppercase domain, spaces, etc.). Fix: use lowercase letters, digits, dots, hyphens, and forward slashes only.

### "missing dot in first path element"

You wrote `go mod init mything` — no domain. Go assumes that means a *local-only* module. This is fine for experiments but warns you that it is not a network-resolvable name. Choose `example.com/mything` if you want a namespace without going public yet. (`example.com` is a reserved domain that will never collide with anything real.)

---

## Security Considerations

- **The module path is public if you publish.** Do not encode secrets, internal hostnames, or company-confidential identifiers into the module path. It will end up in dependency lists, build logs, and possibly the public Go module proxy.
- **Avoid typosquatting risk.** A module path that closely matches a popular project (`github.com/golamg/...` instead of `github.com/golang/...`) invites user confusion and supply-chain attacks. Choose distinctive names.
- **Internal-only modules need an internal-looking path.** If your company runs a private proxy, use `corp.example.com/team/repo`, not `github.com/...`.
- **`go mod init` does not authenticate.** It is a local file-creation operation. No credentials are exchanged. So nothing leaks at this step — the leaks happen later when you push the repository.

---

## Performance Tips

- `go mod init` finishes in milliseconds. There is nothing to tune.
- The cost of a *bad* module path is later — every `go get` of your module pays a network round-trip to a path that may not exist or may be ambiguous. Choose well now to spend nothing later.
- A module that is split into too many sub-modules (advanced topic) will pay a coordination cost. Default to one module per repository.

---

## Best Practices

1. **Always specify the module path explicitly.** Do not rely on auto-detection. `go mod init github.com/alice/thing` is clearer than bare `go mod init`.
2. **Match the path to the repository.** If GitHub, use `github.com/<user>/<repo>`. If GitLab, `gitlab.com/<group>/<repo>`. Self-hosted? Use the canonical hostname.
3. **Lowercase only.** Always.
4. **Pick a name a stranger could pronounce.** `csvkit` beats `cs8k`; `httpclient` beats `httpclnt`.
5. **Run `go mod init` before writing code, not after.** Every minute you write `.go` files without a `go.mod` is a minute spent with a tooling experience that is slightly worse.
6. **Commit `go.mod` immediately.** Even if it is only two lines.
7. **Do not nest modules unless you mean to.** A sub-folder with its own `go.mod` is a separate module. This is occasionally what you want, but never accidentally.

---

## Edge Cases & Pitfalls

### Pitfall 1 — Running it from a parent folder

```bash
cd ~/projects        # NOT inside the project!
go mod init github.com/alice/hello
```

You just turned `~/projects` into a module. Every existing project below it is now a sub-folder of one giant unintended module. **Always `cd` into the target directory first.**

### Pitfall 2 — Picking a name you cannot push to

Naming your module `github.com/alice/hello` when no such repository exists is fine *today*. But the moment you try to publish, you must create exactly that repository. Mismatched names produce runtime download errors with messages like "could not find module" — at the time someone else tries to use your code.

### Pitfall 3 — Re-running `go mod init` after dependencies exist

If your `go.mod` already lists `require` lines, running `go mod init` again will error out. Good. If you delete `go.mod` and re-run, you will lose the dependency list and the version pins. Bad. Just edit the first line of `go.mod` instead.

### Pitfall 4 — Whitespace in folder paths

The module path itself cannot contain spaces. Folder paths on disk can — `/Users/alice/My Projects/hello` is fine. Just make sure the module path argument is quoted only if your shell needs it (it usually does not).

### Pitfall 5 — Modules inside Git submodules

A Git submodule that contains its own `go.mod` is its own Go module. The Go toolchain does not look "up the tree." This is rarely a problem but surprises people who expected one big module.

### Pitfall 6 — The Go version line

The `go 1.22` line is not just decoration — it is a *minimum* Go version for the module's source. If you write code using a feature added in Go 1.21 (like `min`/`max`), the line should be at least `go 1.21`. `go mod init` picks the version of the tool you used; if you upgrade later, run `go mod tidy` to keep the directive sensible.

---

## Common Mistakes

- **Not running `go mod init` at all.** Trying to use `go run`, `go build`, or import packages without it. This used to "kind of work" via GOPATH; it does not anymore.
- **Choosing a single-word name.** `go mod init hello` works, but the name is local-only. Future-you cannot publish `hello` — there is no domain for it. Use `github.com/<user>/hello` even if `<user>` is a placeholder.
- **Putting the module path in CamelCase.** `go mod init github.com/Alice/Hello` works on macOS, breaks on Linux, confuses Windows. Always lowercase.
- **Running `go mod init` and immediately running `go mod tidy`.** Tidy is for when you have dependencies. With a fresh init, there is nothing to tidy. Harmless but unnecessary.
- **Manually editing the `go` directive** to a version that is newer than the installed toolchain. The build will fail with a confusing version-mismatch error.
- **Editing `go.mod` to remove the `go` directive.** It is required.
- **Adding files outside the module root and expecting them to be importable.** Only `.go` files in folders *under* the module root are part of the module.

---

## Common Misconceptions

> *"`go.mod` lists my packages."*

No. `go.mod` lists your **dependencies** and the **module path**. Your packages are detected automatically by walking the directory tree.

> *"I have to use GitHub for the module path."*

No. The module path is just a string. It conventionally looks like a URL because Go's default proxy expects to find it on the public internet, but for local-only or company-internal modules any consistent path works (use `replace` directives in consumers).

> *"I can rename a module by editing one line."*

You can edit the `module` line of `go.mod`, yes — but every project that depends on the old name still depends on the old name. Renames are coordinated, breaking changes.

> *"`go mod init` is just for libraries."*

It is for **everything** in modern Go: applications, libraries, scripts, plugins, prototypes. If it has a `.go` file, it lives in a module.

> *"The `go.sum` file is part of `go mod init`."*

`go.sum` does not exist after `go mod init`. It appears the first time you add a dependency.

---

## Tricky Points

- **The `go` directive enforces source compatibility, not toolchain version.** `go 1.22` means "this code uses features no older than Go 1.22"; it does not pin you to that exact toolchain.
- **The implicit module path of a sub-folder is *not* the module's path.** A folder `pkg/cache/` inside module `github.com/alice/foo` has *import* path `github.com/alice/foo/pkg/cache`. There is no separate module path.
- **`example.com` is special.** It is reserved by IANA and will never resolve to a real server, so it is safe to use as a placeholder module path forever.
- **A module path is case-sensitive at lookup time.** Even if your filesystem is not. So `github.com/Alice/Repo` and `github.com/alice/repo` are different modules to the Go proxy.
- **`go mod init` does not validate that the network path exists.** You can type a typo and the file gets written anyway. Errors only appear later.

---

## Apply it

1. Choose one small, known input for **`go mod init`**.
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

- What problem does `go mod init` solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
