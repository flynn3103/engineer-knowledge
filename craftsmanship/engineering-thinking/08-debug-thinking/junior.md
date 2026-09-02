# Debug-Thinking — Junior

**Your question:** How do I reliably find and fix one bug instead of guessing and hoping the change worked?

"The upload sometimes fails" is not a bug report you can act on. It hides which uploads, how often, and what "fails" actually looks like (error shown? silent data loss? wrong file stored?). Debugging from a vague description wastes cycles on hypotheses that were never testable in the first place.

## The method: Reproduce, hypothesize, test, verify

1. **Reproduce it on demand.** A bug you can't trigger reliably, you can't verify you fixed. Find the smallest input and steps that trigger it every time (or find the trigger *rate*, if it's intermittent — see [middle.md](middle.md) for that case).
2. **State expected vs. actual precisely.** Not "it's broken" — "I expected the response to be `{status: 200, url: "..."}`; I got `{status: 500}`."
3. **Read the evidence literally before theorizing.** The stack trace names a file, a line, and an exception type. Read it before guessing — most junior-level bugs are solved by the error message alone, not by intuition.
4. **Form exactly one falsifiable hypothesis.** "Something with the database" is not falsifiable — there's no observation that would prove it wrong. "The `save()` call is failing because the file size exceeds the 5MB limit and the size check happens after, not before, the write" is falsifiable: check the code order, check the file size.
5. **Test the hypothesis cheaply.** Add one log line, one breakpoint, or one assertion that would prove or disprove it — don't rewrite code yet.
6. **Fix the cause, not the symptom.** A `try/catch` that silences the error is not a fix; it's the bug wearing a disguise.
7. **Verify the fix closes the *actual* gap.** Re-run the exact reproduction steps from step 1. If you can't re-run them, you didn't actually verify anything.

## A concrete example

**Symptom:** "Profile picture upload sometimes fails with a 500 error."

**Reproduce:** Uploading a 6MB JPEG fails every time. Uploading a 2MB JPEG always succeeds. Reproducible, not intermittent — the trigger is file size.

**Expected vs. actual:** Expected a 413 (Payload Too Large) response for files over 5MB, per the API spec. Actual: a 500 (Internal Server Error) with no useful message.

**Read the evidence:** The stack trace points to `image_processor.py:47`, inside `resize(file)`, with `MemoryError`.

**Hypothesis:** The 5MB size check happens *after* the file is already loaded into memory for resizing, so an oversized file crashes the resize step before validation ever runs.

**Test cheaply:** Add one log line before the resize call, printing `len(file.read())`. Upload the 6MB file. Confirm the log fires *before* any size-rejection code runs.

**Fix the cause:** Move the size check to before the file is read into memory — reject at the boundary, not after doing the expensive work.

**Verify:** Re-upload the same 6MB file. Confirm it now returns 413, not 500. Re-upload the 2MB file. Confirm it still succeeds (you didn't break the working case).

## Recognize common bug patterns

Most junior-level bugs are one of a small set of recurring shapes. Learning to recognize the shape narrows the hypothesis space immediately:

| Pattern | Signature | Where to look first |
|---|---|---|
| Off-by-one | Loop misses the first or last element, or runs one time too many | Loop bounds, `<` vs `<=`, array index math |
| Null / undefined reference | Crash on a field access, "cannot read property of undefined" | The step right before the crash — what should have set that value? |
| Stale state / cache | Works after a restart, fails after some data changes | Anywhere a value is cached, memoized, or read from a variable set earlier |
| Wrong assumption about order | Works alone, fails when combined with other operations | Whether the code assumes something already happened that didn't |
| Type or unit mismatch | Numbers look "close but wrong" (100x off, negative when should be positive) | Units (ms vs. s, cents vs. dollars), string vs. number comparison |
| Shared mutable state | Fails only under concurrent access or repeated calls | Anything written to a variable, object, or file that more than one path touches |

## Common beginner mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Changing code before reproducing the bug | You can't tell if your change fixed it or just changed timing | Reproduce first, every time |
| Testing multiple hypotheses at once (change 3 things, re-run) | If it works, you don't know which change mattered — the bug can resurface later | One hypothesis, one test, one variable changed |
| Trusting your mental model over the actual output | The program is doing exactly what the code says, not what you assume it says | Print or log the actual value at the point you're unsure about |
| Fixing the first thing that looks wrong | Might be a real bug, but not *the* bug that causes this symptom | Fix must explain the specific symptom you started with — verify it does |
| Declaring victory without re-running the reproduction steps | The "fix" may not touch the actual failing path at all | Always re-run step 1's exact trigger after the fix |

## Hands-on exercise

Pick a bug from your backlog (or reproduce a small one on purpose — comment out a bounds check, introduce an off-by-one).

1. Write the exact steps to reproduce it, and confirm it fails every time you follow them.
2. Write expected vs. actual in one sentence each.
3. Read the actual error output (stack trace, log, or wrong value) word by word before forming a theory.
4. Write one falsifiable hypothesis — a sentence that names the file/function and could be proven wrong.
5. Add the smallest possible check (one log line or one debugger breakpoint) to test it.
6. Fix, then re-run your exact steps from #1 to verify.

If you can't write a falsifiable hypothesis in step 4, you don't have enough evidence yet — go back and read more of the actual output.

## Verify your thinking

- [ ] Can you reproduce the bug on demand, not just "it happened once"?
- [ ] Did you read the actual error message/output before forming a theory?
- [ ] Is your hypothesis falsifiable — is there an observation that would prove it wrong?
- [ ] Did you change exactly one thing before re-testing?
- [ ] Did you re-run the original reproduction steps to verify the fix, not just "look right" in the code?

Continue to [`middle.md`](middle.md).
