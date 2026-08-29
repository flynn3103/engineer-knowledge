# Macros — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Macros** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Homoiconicity: Code Is a List

In most languages, source code is text, and the parser converts it into an internal tree you never see. In Lisp, the tree *is* the surface syntax. `(if test then else)` is a four-element list: the symbol `if`, and three sub-expressions. There is nothing else. The parser's job is trivial because the programmer already wrote the tree.

This means you can take a piece of code and treat it as data with a single operation — `quote`:

```lisp
(+ 1 2)        ; => 3        (evaluated: a function call)
'(+ 1 2)       ; => (+ 1 2)  (quoted: a list of three elements)
(first '(+ 1 2))  ; => +     (the symbol +)
(rest  '(+ 1 2))  ; => (1 2) (the arguments, as a list)
```

Because code is just lists, **a macro is a function that takes lists and returns a list.** That returned list *is* code, and the compiler substitutes it for the macro call. No separate template engine, no text munging — just list processing.

### 2. `defmacro`: A Function from Code to Code

Here is a macro that defines a `when`-style conditional (run the body only if the test is true):

```lisp
(defmacro my-when (test &rest body)
  (list 'if test (cons 'progn body)))
```

When you write `(my-when (> x 0) (print x) (incr count))`, the macro receives:
- `test` bound to the *unevaluated* list `(> x 0)`
- `body` bound to the list `((print x) (incr count))`

and returns the list:

```lisp
(if (> x 0) (progn (print x) (incr count)))
```

which the compiler then compiles. Notice the macro received **unevaluated** code — `(> x 0)` was *not* run before the macro saw it; that is exactly what lets a macro control evaluation. A function could never do this: `(my-when-function (> x 0) (print x))` would evaluate `(print x)` *before* the function ran, defeating the point.

That is the deep reason macros exist and functions are not enough: **macros control whether and when their arguments are evaluated.** `if`, `and`, `or`, `while`, `loop` — every short-circuiting or control-flow construct *must* be a macro (or a built-in special form), because a function always evaluates all its arguments first.

### 3. Quasiquotation: Templates for Code

Building lists by hand with `list`, `cons`, and `'` gets unreadable fast. Quasiquotation is a templating syntax that makes the *output code* look like the code it produces. Three pieces:

- **`` ` ``** (backquote / quasiquote): start a template. Everything is literal *unless* marked.
- **`,`** (unquote): "evaluate this and drop the result in here."
- **`,@`** (unquote-splicing): "evaluate this to a list and splice its elements in here."

Rewriting `my-when` with quasiquote:

```lisp
(defmacro my-when (test &rest body)
  `(if ,test (progn ,@body)))
```

Read it as: *"produce the code `(if … (progn …))`, where `,test` is replaced by the actual test expression and `,@body` splices in the body forms one by one."* The template *looks like* the generated code, which is exactly what makes quasiquotation the single most important macro-writing tool. The difference between `,` and `,@`:

```lisp
(let ((xs '(1 2 3)))
  `(list ,xs))     ; => (list (1 2 3))   ; xs dropped in as ONE element
(let ((xs '(1 2 3)))
  `(list ,@xs))    ; => (list 1 2 3)     ; xs SPLICED, parens removed
```

### 4. The Capture Problem and `gensym`

Common Lisp's `defmacro` is **not hygienic**: names you introduce in the expansion live in the caller's namespace and can collide. Consider a macro that swaps two places using a temporary:

```lisp
(defmacro swap (a b)
  `(let ((tmp ,a))      ; <-- introduces a binding named 'tmp'
     (setf ,a ,b)
     (setf ,b tmp)))
```

This looks fine until the caller's code *also* uses `tmp`:

```lisp
(let ((tmp 10) (x 1))
  (swap tmp x))   ; BROKEN: the macro's 'tmp' shadows the caller's 'tmp'
```

The expansion binds a `tmp` that captures the caller's variable, and the swap goes wrong. This is **variable capture** — the syntactic-macro version of the C `tmp`-collision bug. The Common Lisp fix is **`gensym`**, which mints a fresh symbol guaranteed not to appear anywhere else:

```lisp
(defmacro swap (a b)
  (let ((tmp (gensym "TMP")))   ; a unique symbol, e.g. TMP4271
    `(let ((,tmp ,a))
       (setf ,a ,b)
       (setf ,b ,tmp))))
```

Now the temporary has a name no human could have typed, so capture is impossible. Every experienced Common Lisp macro author reaches for `gensym` reflexively when introducing a binding. The lesson: **even syntactic macros need a discipline to avoid capture — unless the language enforces hygiene for you.**

### 5. Scheme's `syntax-rules`: Hygiene for Free

Scheme took a different design path. Its `syntax-rules` macros are **declarative** (you write pattern → template pairs, no list-building code) and **automatically hygienic** (the system renames introduced identifiers so capture *cannot happen*). The same `swap`, in Scheme:

```scheme
(define-syntax swap!
  (syntax-rules ()
    ((swap! a b)
     (let ((tmp a))
       (set! a b)
       (set! b tmp)))))
```

There is no `gensym` here, yet `(let ((tmp 10) (x 1)) (swap! tmp x))` works correctly. The `tmp` introduced *by the macro* is automatically distinct from the `tmp` in the caller — the macro expander renames it behind the scenes. This automatic renaming is the essence of **hygiene**, and it is the headline feature that makes Scheme macros (and, later, Rust's) safe by default.

A `syntax-rules` definition is a set of `(pattern template)` clauses. The pattern matches the *shape* of the macro call; the template is the replacement, with pattern variables filled in. Ellipsis `...` handles repetition:

```scheme
(define-syntax my-or
  (syntax-rules ()
    ((my-or) #f)
    ((my-or e) e)
    ((my-or e1 e2 ...)              ; e2 ... matches "zero or more"
     (let ((t e1))
       (if t t (my-or e2 ...))))))  ; recursive, and 't' is hygienic
```

Note `my-or` is recursive *and* introduces `t` — and hygiene guarantees `t` never collides with any expression the caller passes. (In Common Lisp you would `gensym` that `t`.)

### 6. Macroexpansion Is a Phase Before Evaluation

It is worth being precise about *when* macros run. Compilation proceeds roughly:

1. **Read**: parse text into s-expressions (lists/symbols/numbers).
2. **Macroexpand**: repeatedly replace each macro call with its expansion, until no macros remain. (Expansion can produce more macro calls, which are expanded in turn.)
3. **Compile / evaluate**: process the fully-expanded, macro-free code.

Macros live entirely in step 2. By the time the program runs, every macro is gone, replaced by ordinary code. You can watch step 2 directly: `macroexpand-1` (Common Lisp) or `(syntax->datum (expand …))`-style tools (Scheme/Racket) show you the expansion, the Lisp analog of `gcc -E`.

---

## Code Examples

### A `unless` macro (Common Lisp), with quasiquote

```lisp
(defmacro unless (test &rest body)
  `(if (not ,test)
       (progn ,@body)))

(unless (member x banned)
  (process x)
  (log-success x))
;; expands to:
;; (if (not (member x banned))
;;     (progn (process x) (log-success x)))
```

### `gensym` in action: a `with-timing` macro

```lisp
(defmacro with-timing (&rest body)
  (let ((start (gensym "START"))     ; fresh symbols so we never
        (result (gensym "RESULT")))  ; capture the caller's names
    `(let ((,start (get-internal-real-time)))
       (let ((,result (progn ,@body)))
         (format t "took ~D ticks~%"
                 (- (get-internal-real-time) ,start))
         ,result))))

(with-timing (slow-computation))   ; runs body, prints elapsed, returns its value
```

Without `gensym`, a caller who happened to use a variable named `start` or `result` inside the body could be silently broken. With it, the macro is robust.

### Seeing the expansion

```lisp
(macroexpand-1 '(unless done (cleanup)))
;; => (IF (NOT DONE) (PROGN (CLEANUP)))   ; the macro's output, before compile
```

`macroexpand-1` expands one level; `macroexpand` expands fully. This is your `gcc -E` for Lisp.

### Scheme `syntax-rules`: `swap!`, `my-list-of`, and recursion

```scheme
;; Hygienic swap — no gensym needed.
(define-syntax swap!
  (syntax-rules ()
    ((_ a b) (let ((tmp a)) (set! a b) (set! b tmp)))))

;; Repetition with ellipsis: build a list, doubling each element.
(define-syntax doubled-list
  (syntax-rules ()
    ((_ x ...) (list (* 2 x) ...))))   ; (doubled-list 1 2 3) => (2 4 6)

;; Recursive, hygienic 'and'.
(define-syntax my-and
  (syntax-rules ()
    ((_) #t)
    ((_ e) e)
    ((_ e1 e2 ...) (if e1 (my-and e2 ...) #f))))
```

The `_` is a conventional placeholder for the macro's own name in the pattern. `...` after a pattern variable means "zero or more," and using `...` in the template repeats the surrounding template once per match.

---

## Coding Patterns

**Pattern: `with-X` resource wrapper (controls evaluation of a body).**

```lisp
(defmacro with-lock ((lock) &rest body)
  `(progn (acquire ,lock)
          (unwind-protect (progn ,@body)
            (release ,lock))))
```

`unwind-protect` guarantees `release` runs even if the body throws — only a macro can wrap the body like this.

**Pattern: always `gensym` an introduced binding (Common Lisp).**

```lisp
(let ((g (gensym))) `(let ((,g ,init)) ... ,g))
```

**Pattern: prefer `syntax-rules` when the transformation is structural (Scheme).** Reach for procedural `syntax-case` only when pattern/template is insufficient.

**Pattern: recursive macro with a base case (`syntax-rules`).** Multiple clauses, terminating clause first or last, recurse on the "rest."

---

## Best Practices

- **Write expansions with quasiquote**, not hand-assembled `list`/`cons` — readability is correctness here.
- **Always `gensym` (Common Lisp) or rely on hygiene (Scheme/Racket)** for any binding the macro introduces. Treat "I am introducing a variable" as a red flag to check capture.
- **Expand the macro during development** (`macroexpand-1`) and read the output — confirm it is what you intended.
- **Evaluate each macro argument exactly once** in the expansion if it could have side effects: bind it to a `gensym`med variable first, then use that variable.
- **Document the macro's *expansion contract*** — what shape of call it accepts and what code it produces — because callers cannot infer it from a function signature.
- **Prefer a function unless you need to control evaluation or transform syntax.** Macros are a sharp tool; do not reach for them out of habit.

---

## Edge Cases & Pitfalls

- **Evaluating an argument more than once.** If a macro template uses `,x` in two places and `x` has a side effect, it runs twice — the *same* double-evaluation bug as C, just at the AST level. Bind it once: `` `(let ((,g ,x)) ... ,g ... ,g) ``.
- **Capturing a caller's variable (Common Lisp).** Forgetting `gensym`. Silent and nasty.
- **Being captured *by* a caller's macro/redefinition.** Hygienic systems protect against this too; unhygienic ones do not.
- **Phase confusion.** A macro runs at compile time and cannot see run-time values. Trying to "pass a run-time number to a macro" reflects a misunderstanding of *when* macros execute.
- **`,@` vs `,`.** Splicing vs inserting. Using `,` where you needed `,@` puts a list where you wanted its elements (or vice versa). A very common beginner slip.
- **Macros that look like functions but are not.** A reader who assumes `(my-when c a b)` evaluates all of `c`, `a`, `b` will mis-reason about side effects. Macros change evaluation order; that is their power and their footgun.
- **Recursion that does not terminate** in a `syntax-rules` macro will hang the *compiler*, not the program.

---

## Common Mistakes

1. **Forgetting `gensym`** and shipping a capture bug in Common Lisp.
2. **Using `,` instead of `,@`** (or vice versa) and producing malformed code.
3. **Evaluating an argument multiple times** by repeating `,x` instead of binding it once.
4. **Writing a macro where a function would do** — losing readability and tooling for no benefit.
5. **Confusing compile-time and run-time** — expecting a macro to react to data that only exists at run time.
6. **Not expanding the macro to check it** before assuming it is correct.

---

## Apply it

1. Find a real component where **Macros** affects an interface or dependency.
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

- Which boundary is most affected by Macros?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
