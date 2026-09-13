---
name: generate-knowledge
description: Use when writing or restructuring a topic in this repo (e.g. under craftsmanship/professionalism/problem-solving/) into the problem / mistake / best-practise format. Triggers on requests like "rewrite <topic> as problem/mistake/best-practise", "generate a 3-level guide for <concept>", "research <topic> and write it up", or "viết lại <topic> với 3 level problem/mistake/best-practise". Produces a research-backed, bullet-list-heavy, minimal-diagram 4-file set (README + problem + mistake + best-practise) grounded in real web sources rather than invented from memory.
---

# Generate Knowledge Skill

## Overview

Organizes a topic into **3 levels of understanding**, each with a distinct job.
Content is **researched from real web sources first**, then synthesized — never
invented purely from the model's own memory.

Reference example already in the repo:
`craftsmanship/professionalism/problem-solving/first-principles-thinking/`.

## The 3 levels

- **`problem.md`** — first contact with the idea. What problem does this
  actually solve, and how does it work? Written so the reader understands it
  *immediately*: plain terms, one concrete example carried through, no hedging
  or caveats yet. The reader should finish this file able to explain the idea
  back in their own words.
- **`mistake.md`** — the evaluation layer. Now that the reader gets the
  mechanism, help them use it well: pros and cons that decide *when* to reach
  for this vs. not, and the common mistakes people make once they start
  applying it (mistake → why it hurts → fix). This is where judgment lives.
- **`best-practise.md`** — the fluency layer. Package the idea into a best
  practice or pattern precise enough that anyone on a team could follow it
  without re-deriving it from scratch: a repeatable checklist, a named
  pattern, or a practice routine that turns the concept into a habit.

## Process, in order

1. **Research the topic on the web before writing anything.** Fetch 2-4 real sources
   (encyclopedic overview + a source with concrete simple examples + a source on
   common failure modes if one exists). Do not synthesize purely from memory — the
   whole point of this format is that content is grounded in citable material.
2. **Check repo conventions before touching files:**
   - Read the existing folder (any old files, `.pages` nav) to see what's being
     replaced.
   - Verify sibling links you plan to reuse actually resolve (`ls` the target
     folder) — don't copy a "Related" link forward without checking it isn't
     already broken (numbered-prefix links like `01-foo/` are a common stale
     pattern in this repo).
3. **Write `problem.md`** — the problem it solves and the mechanism, explained simply.
4. **Write `mistake.md`** — pros/cons and common mistakes, grounded in the same research.
5. **Write `best-practise.md`** — the best-practice pattern and how to build fluency in it.
6. **Write `README.md` last** — pure routing, no explanation, no diagram.
7. **Update `.pages`** nav order to the new filenames.
8. **Delete any old files this format replaces** — this format is a replacement
   for a topic folder's content, it doesn't sit alongside a previous structure.

## File structure

```
<topic-folder>/
  README.md          # routing only: 1-line definition + table linking the 3 guides + Related links. No diagram, no explanation.
  problem.md     # problem + mechanism: what it solves, how it works, in plain terms
  mistake.md    # pros/cons and common mistakes when applying it, and the fix for each
  best-practise.md    # the best-practice pattern, and how to practice it until it's automatic
  .pages              # nav: [README.md, problem.md, mistake.md, best-practise.md]
```

## Content rules

- **Plain, everyday words — no jargon, no academic vocabulary.** Write like
  you're explaining it to a teammate out loud, not writing a paper. Prefer
  short, common words over impressive ones ("makes it worse" not "amplifies";
  "waiting in line" not "queueing"; "keeps happening on its own" not
  "self-reinforcing"). If a technical term is genuinely unavoidable (a named
  concept the reader needs, like "reinforcing loop"), define it in one plain
  clause the first time it appears, then you may reuse the term.
- **Every sentence earns its place by being actionable or explainable.**
  Actionable: tells the reader what to do or check. Explainable: tells the
  reader *why*, simply enough that they could repeat it to someone else
  without notes. If a sentence is neither, cut it.
- **Bullet-list style throughout `mistake.md` and `best-practise.md`.**
  Mistake → why it hurts → fix, as a flat bullet, not prose paragraphs.
- **Max 2 Mermaid diagrams across the whole 4-file set**, and put them where a
  diagram earns its place (a real mechanism flow), not decoratively on every page.
  `README.md` gets zero diagrams — it's routing, not explanation.
- **One worked example beats several thin ones.** Pick one concrete scenario and
  carry it through `problem.md`; reuse the same scenario in
  `mistake.md`'s mistakes where it fits, instead of inventing a new example
  per bullet.
- **Ground every non-obvious claim in what you actually fetched.** If research
  surfaced a named result (e.g. a documented principle, a named rule of thumb, a
  quote from a primary source), use it — that's the difference between this
  format and writing from unverified memory.
- **Keep it short.** If a file is growing past what a bullet list can carry,
  that's a sign to cut, not to add prose.

## Research checklist (do before writing)

- [ ] Fetched at least one source that gives the mechanism in plain, simple terms
      (an encyclopedic or educational source with a concrete everyday example
      beats an academic paper for this).
- [ ] Fetched at least one source on how the concept fails in practice or common
      misconceptions about it, if one exists for the topic.
- [ ] Can name, for at least one non-obvious claim in the final files, which
      fetched source it came from.
- [ ] Did not fabricate a named principle, quote, or statistic that wasn't in a
      fetched source.

## Common mistakes

| Mistake | Fix |
|---|---|
| Writing from memory and skipping the web research step | Fetch real sources first; this format's value is being grounded, not just short |
| Putting a diagram in `README.md` "for context" | README is routing only — move any diagram into `problem.md` |
| Turning `mistake.md` into prose paragraphs | Every mistake is a bullet: mistake, why it hurts, fix — no exceptions |
| Reusing a broken sibling link from the old README without checking it resolves | `ls` the target path before linking to it |
| Silently leaving old files alongside the new ones when replacing a folder's content | Delete them — this is a replacement, not an addition |
| Writing in academic or corporate vocabulary that assumes prior expertise | Rewrite with everyday words; define any unavoidable term once, in plain language, the first time it's used |
| A sentence that just restates the topic ("this is important for X") with no action or reason attached | Cut it, or turn it into a concrete instruction or a one-line "why" |

## Reference example

Read `craftsmanship/professionalism/problem-solving/first-principles-thinking/{README,problem,mistake,best-practise}.md`
in this repo before writing a new topic in this format — match its tone, bullet
density, single-example-per-file approach, and the fact that `README.md` there
is routing only: a short table plus a Related section, nothing else.
