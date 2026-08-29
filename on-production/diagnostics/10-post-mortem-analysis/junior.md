# Post-Mortem Analysis — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Post-Mortem Analysis** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Post-Mortem Analysis Roadmap](README.md)
> **Focus:** What a post-mortem is — both senses. Why blameless. The basic incident timeline. The 5 Whys. Reading a crash dump after the fact.

---

## Core Concepts

### 1. A Post-Mortem Is About Learning, Not Punishing

The single most important idea. The purpose is to extract a *lesson the system can keep*, so the next person doesn't fall into the same hole. If the post-mortem turns into "whose fault was it," people stop reporting incidents honestly, and the organization goes blind. **The output of a post-mortem is a changed system, not a named culprit.**

### 2. The Evidence Is Frozen — Collect It Before It Melts

The dead process's state, the logs from the incident window, the dashboard graphs — these are **perishable**. Logs rotate. Metrics age out of the dashboard. A restarted process overwrites its core file. The first reflex when something breaks badly is: *grab the evidence before it's gone.* Take the core dump, screenshot the graph, export the chat. You analyze later; you collect now.

### 3. Symptom Is Not Cause

"The site returned 500 errors" is a symptom. "We ran out of database connections because a code path leaked them" is closer to a cause. A post-mortem that stops at the symptom ("we restarted it and it went away") has not done its job — the cause is still in the system, waiting.

### 4. A Timeline Turns Chaos Into a Story

During an incident, everything is noise: pages firing, people typing in Slack, dashboards flickering. Afterward, you impose order by building a **timeline** — a simple time-sorted list of "at 14:02 X happened, at 14:05 Y happened." The timeline is the backbone of every incident post-mortem. Most of the analysis falls out of getting the timeline right.

### 5. The Dead Process Still Has a Last Known State

When a program crashes, it doesn't vanish — if you've enabled core dumps, the OS writes its memory to disk. That file is a **frozen snapshot** of the exact moment of death: which line, which variables, which thread. Reading it is "program post-mortem debugging." You're not running the program; you're examining its corpse in a debugger.

---

## The Two Senses of "Post-Mortem"

Because this topic lives in *diagnostics*, you must hold both meanings at once. Here's how they line up.

| Dimension | Incident Post-Mortem | Program Post-Mortem |
|---|---|---|
| **What died** | A service / a feature / a business process | A single process |
| **The corpse** | The incident's logs, metrics, chat, deploys | A core dump / crash log / heap dump |
| **Main artifact** | A written document | A debugger session over a dump file |
| **Main question** | "Why did the system fail, and how do we prevent it?" | "Why did this process crash, and on which line?" |
| **Main technique** | Timeline + 5 Whys + action items | `gdb`/`dlv` over the dump, read the stack |
| **Output** | Action items the org acts on | A bug fix + (often) a regression test |
| **Audience** | The whole org, future engineers | You and the code's maintainers |

They meet constantly. A core dump is often *the key piece of evidence* in an incident post-mortem: *"the process crashed; here's the dump; the stack shows a nil-pointer dereference in the refund path."* Live debugging is covered in [`../01-debugging/`](../01-debugging/README.md); automated capture of crashes (the thing that *produces* the dump) is [crash-reporting](../07-crash-reporting/README.md); the request-flow forensics side is [tracing](../05-tracing/README.md).

---

## Why Blameless

This deserves its own section because it is the load-bearing idea of incident post-mortems, and the one juniors most often misunderstand.

**The cardinal rule:** *Given what they knew at the time, the people involved acted reasonably.* If that turns out not to be true, the question is not "why were they careless?" but "why did the system let a reasonable person make that mistake?" — which is a system problem (bad docs, no guardrails, a confusing UI), not a character flaw.

Why this is not just being nice:

- **Honesty depends on safety.** The moment one engineer is named-and-shamed in a post-mortem, *everyone* learns the lesson "hide your mistakes." The next incident gets quietly swept under the rug, and the organization loses the data it needs to improve. Blameless is not a feel-good policy; it is a *survival strategy for the learning loop*.
- **People are rarely the cause.** Humans make mistakes constantly. A system that goes down because one human made one ordinary mistake is a *fragile system*. The interesting question is always "why was a single human error enough to cause an outage?"
- **It changes what you fix.** Blame leads to "be more careful" (which fixes nothing). Blamelessness leads to "add a confirmation step / a canary / a lint rule / better docs" (which fixes the class of problem).

How a sentence drifts from blameless to blameful:

| Phrasing | Verdict |
|---|---|
| "The deploy at 14:02 introduced the change." | ✅ Blameless — describes the event. |
| "Alice deployed the change at 14:02." | ⚠️ Drifting — names a person unnecessarily. |
| "Alice deployed it without running the canary." | ⚠️ Leaning toward blame. |
| "Alice should have known the canary was required." | ❌ Blameful — accuses. |
| "The deploy pipeline did not enforce a canary step; this was not visible to the deploying engineer." | ✅ Blameless — fixes the system. |

> **Junior takeaway:** When you write a post-mortem, do a find-and-replace in your head: every time you've written a person's name as the *cause* of something, rewrite the sentence to describe the *system* that allowed it.

---

## Building a Timeline

The timeline is the skeleton of an incident post-mortem. Get it right and the analysis writes itself.

Rules a junior should follow:

1. **Use UTC.** Always. Time zones in a timeline cause hours of confusion when people are in different regions. Write `14:02 UTC`.
2. **One line per event.** "14:02 — deploy of checkout v2.317 completed." Terse, factual.
3. **Include both the failures and the responses.** When the alert fired, when a human ack'd, when the rollback started, when recovery completed.
4. **Source every entry.** Where did "14:02" come from — the deploy bot, a log line, the chat? A timeline built from memory is a fiction.
5. **Mark detection and recovery clearly.** Two numbers fall out: *time to detect* (incident start → someone noticed) and *time to recover* (start → back to normal, your MTTR for this one).

A worked micro-timeline:

```text
13:58 UTC  Cache TTL config change merged (PR #4412).
14:02 UTC  Deploy of checkout-service v2.317 completes in us-east-1.
14:11 UTC  Background catalog refresh fires; all caches invalidated at once.
14:12 UTC  ALERT: checkout error rate > 5% for 1 min. Page sent to on-call.
14:13 UTC  On-call acknowledges; opens incident channel.        ← detected (~1 min)
14:14 UTC  Hypothesis: the 14:02 deploy is the trigger.
14:15 UTC  Rollback to v2.316 started.
14:18 UTC  Rollback complete; error rate drops to baseline.      ← recovered (MTTR ~6 min)
14:20 UTC  Incident downgraded; diagnosis continues.
```

From this skeleton, the impact line ("checkout errors elevated 14:11–14:18, ~6 minutes"), the trigger, and the first hypothesis are all obvious. **The timeline did most of the work.**

---

## The 5 Whys — First Contact

The 5 Whys is the entry-level root-cause technique. You ask "why did that happen?" of each answer, peeling layers until you reach something you can actually change.

> **Worked example.**
>
> 1. **Why did checkout error out?** Because it couldn't reach the pricing service.
> 2. **Why couldn't it reach pricing?** Because pricing's connection pool was exhausted.
> 3. **Why was the pool exhausted?** Because 1,200 requests hit it simultaneously when every cache entry expired at once.
> 4. **Why did every entry expire at once?** Because the new 300s TTL meant the periodic invalidate cleared a full cache instead of a sparse one.
> 5. **Why did a full-cache clear cause a stampede?** Because the cache has no request coalescing (no "singleflight") to collapse simultaneous misses.
>
> **The change you can make:** add request coalescing to the cache, and/or jitter the TTLs. *That* is a fix. "We'll be more careful with TTLs" is not.

Two cautions even at junior level (developed fully in `senior.md`):

- **"Five" is not magic.** Stop at the deepest cause you have the *agency to change*. Sometimes that's why #3; sometimes it's why #7. Going further lands you in philosophy ("why did we build a monolith?").
- **It can become a witch hunt.** Ask "why" of the *system*, never the *person*. "Why did the author not use the shared helper?" → "Because the helper is undocumented and the linter doesn't flag the raw call" — a system answer. Not "because the author was sloppy."

---

## Reading a Crash Dump After the Fact

Now the program-post-mortem side. When a native program crashes, the OS can write a **core dump** — a file containing its memory and registers at the moment of death. You open it in a debugger and read the crime scene.

### Step 0 — Make sure dumps are even enabled

By default many systems suppress core dumps. Turn them on in your shell:

```bash
ulimit -c unlimited      # allow unlimited-size core files in this shell
# Where does the kernel write them? Look here:
cat /proc/sys/kernel/core_pattern
```

If the pattern points at `systemd-coredump` (common on modern Linux), dumps go into the journal:

```bash
coredumpctl list                 # recent crashes the system captured
coredumpctl info  <pid|exe>      # metadata: signal, command line, timestamp
coredumpctl gdb   <pid|exe>      # open the latest matching dump in gdb directly
```

### Step 1 — Open the dump and read the stack

For a C/C++ program:

```bash
gdb ./myprog ./core            # binary + core file
(gdb) bt                       # backtrace: the stack at the crash point
(gdb) frame 2                  # move to frame 2
(gdb) print myStruct           # inspect a variable's frozen value
(gdb) info registers           # CPU registers at death
```

For a Go program (build with debug info, set `GOTRACEBACK=crash` so it dumps on panic):

```bash
dlv core ./myprog ./core
(dlv) bt                       # stack of the crashing goroutine
(dlv) goroutines               # all goroutines (huge in concurrent code)
(dlv) print myVar
```

The top of the stack is where the program died. Read **down** the stack (older frames) to see who called this and with what arguments. Just like a live stack trace — except the program will never run again, so this snapshot is all you get. **Collect it carefully; you can't take another.**

### Step 2 — A dump without symbols is half-useless

If the backtrace looks like this, you're missing **symbol files**:

```text
#0  0x0000000000401a3f in ?? ()
#1  0x0000000000402b81 in ?? ()
```

Those `?? ()` are functions whose names were *stripped* from the production binary. To read the dump you need the **unstripped binary** (or its separate debug-symbol file) from the *same build*. Keep it. A stripped binary plus a core dump is fingerprinting a ghost. (More in `middle.md` and `senior.md`; the dedicated topic is [symbolication](../01-debugging/middle.md).)

---

## Code Examples

### Make a program crash and read its corpse (C)

```c
// crash.c — dereference a null pointer on purpose
#include <stdio.h>

int deref(int *p) {
    return *p;            // SIGSEGV when p == NULL
}

int main(void) {
    int *p = NULL;
    printf("about to crash\n");
    return deref(p);      // crash here
}
```

```bash
$ gcc -g -O0 crash.c -o crash      # -g keeps symbols, -O0 keeps lines honest
$ ulimit -c unlimited
$ ./crash
about to crash
Segmentation fault (core dumped)

$ gdb ./crash ./core
(gdb) bt
#0  deref (p=0x0) at crash.c:5
#1  main ()       at crash.c:11
#  ^ p was NULL at line 5. The bug is one frame up at line 11, where p = NULL.
```

The dump told us *exactly* where and *why*: `p=0x0` at `crash.c:5`. The cause is in `main` at line 11. That is a complete program post-mortem.

### Trigger a crash dump on a Go panic

```go
// crash.go — index out of range, with crash-style traceback
package main

func boom(s []int) int { return s[5] } // panic: index out of range

func main() {
    boom([]int{1, 2, 3})
}
```

```bash
$ GOTRACEBACK=crash go run crash.go
panic: runtime error: index out of range [5] with length 3

goroutine 1 [running]:
main.boom(...)
	/app/crash.go:3            ← where it died
main.main()
	/app/crash.go:6 +0x18      ← who called it
exit status 2
```

Even without opening a core file, the *crash log* is itself a post-mortem artifact: it preserves the exact stack at the moment of death. Read it top-down (Go style): the panic, then the innermost frame, then the caller.

### Python — `faulthandler` dumps the stack on a fatal crash

```python
import faulthandler
faulthandler.enable()    # on segfault / fatal signal, print all thread stacks
# ... your program ...
```

When a Python process dies from a C-level fault, `faulthandler` writes every thread's Python stack to stderr — the post-mortem record for a crash that would otherwise leave no traceback.

---

## A Minimal Post-Mortem Template

You don't need the full Google SRE template yet (that's in `professional.md`). For your first incident write-ups, fill in this:

```markdown
# Post-Mortem: <short title>            (date, in UTC)

## Impact
Quantified. "X% of users could not check out for 6 minutes."

## Timeline (UTC)
- 14:02 — ...
- 14:12 — ALERT ...
- 14:18 — recovered

## What happened (the causes)
Plain-English story of the failure. Trigger + contributing factors.

## 5 Whys
1. Why ...? Because ...
   ... down to a cause we can change.

## Action items
- [ ] <concrete, owned, dated task>   (owner: role, due: date)

## What went well / what we got lucky on
Honest notes for next time.
```

Keep it short. A post-mortem nobody reads is wasted work. One to two pages at this level is plenty.

---

## Best Practices

1. **Collect evidence before you clean up.** Take the core dump, screenshot the graph, export the chat — *then* restart and recover.
2. **Write the timeline in UTC, sourced from logs, not memory.**
3. **Keep it blameless.** Describe the system, never accuse the person.
4. **Stop the 5 Whys at the deepest cause you can change** — not at the symptom, not in philosophy.
5. **Every post-mortem ends with action items** that are concrete, owned, and dated. No action items = no learning.
6. **Keep your binaries and symbol files** from every release, so a future core dump is readable.
7. **Enable core dumps** (`ulimit -c unlimited` / systemd `LimitCORE`) on services where post-mortem matters.
8. **Read other people's post-mortems.** It's the cheapest way to learn the shapes of failure.

---

## Edge Cases & Pitfalls

- **A restarted process overwrites or loses its core file.** Capture the dump *before* the orchestrator restarts the pod.
- **Stripped production binaries** make a dump unreadable. Keep the unstripped build artifact.
- **Core dumps contain memory** — passwords, tokens, customer data. Treat them as sensitive: store encrypted, delete after use.
- **Optimized builds (`-O2`)** inline functions and reorder code, so the dump's line numbers can mislead. A debug build (`-O0 -g`) is honest but may not reproduce the bug.
- **Time-zone soup in the timeline.** Mixing local times across regions produces "impossible" orderings. UTC only.
- **A post-mortem written from memory** invents a timeline that never happened. Source every line.
- **`coredumpctl` only has what `systemd-coredump` captured** — and the kernel may have truncated huge dumps.

---

## Common Mistakes

1. **Stopping at the symptom.** "We restarted it and it's fine" is not a post-mortem; the cause is still in the system.
2. **Naming a person as the cause.** The fastest way to make your team hide future incidents.
3. **No action items**, or action items so vague ("improve monitoring") that nobody can do them.
4. **Action items written but never tracked**, so they silently rot and the incident recurs.
5. **Throwing away the core dump** before anyone has read it.
6. **Trying to read a stripped binary's dump** and concluding "the dump is useless" — it's the *symbols* that are missing, not the dump.
7. **Treating the trigger as the root cause.** "We deployed at lunchtime" — banning lunchtime deploys fixes nothing.
8. **Writing a 12-page post-mortem nobody reads.** Length is not depth.
9. **Forgetting UTC** in the timeline.
10. **Doing the post-mortem only for huge outages.** Small incidents and near-misses teach cheaply too.

---

## Tricky Points

1. **The two senses share a name but not a method.** Incident post-mortems are mostly *human and written*; program post-mortems are mostly *technical and tooled*. Don't let a reviewer who wanted one hand you the other.
2. **The core dump shows where it *died*, not always where the *bug* is.** The crash site is often a victim; the bug is a few frames up where bad data was created.
3. **A crash log and a core dump are different.** A crash log (Go panic text, Java `hs_err_pid.log`) is a human-readable summary; a core dump is the full binary memory image. The dump has more, but needs more to read.
4. **"Blameless" does not mean "no accountability."** The team still owns fixing the system; it means we don't punish individuals for honest mistakes.
5. **The first "why" answer feels like the cause but rarely is.** "It ran out of connections" feels complete. Keep going.
6. **Detection time matters as much as recovery time.** An incident the team didn't notice until a customer reported it has a *detection* problem worth its own action item.

---

## Apply it

1. Choose one small, known input for **Post-Mortem Analysis**.
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

- What problem does Post-Mortem Analysis solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
