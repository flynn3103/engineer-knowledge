# Character & String Internals (Unicode) — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Character & String Internals (Unicode)** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Canonical equivalence: one character, two spellings

`é` can be:
- **Precomposed:** `U+00E9` (LATIN SMALL LETTER E WITH ACUTE) — one code point.
- **Decomposed:** `U+0065 U+0301` (`e` + COMBINING ACUTE ACCENT) — two code points.

These are **canonically equivalent**: Unicode declares they represent the same character and must display and sort identically. But their *byte sequences differ*, so naive `==` returns false. This is the single most common cause of "two identical-looking strings are not equal." The fix is to **normalize both sides to the same form** before comparing.

Decomposition can stack: Vietnamese `ệ` may be `e` + circumflex + dot-below, and the combining marks have a defined canonical ordering (by combining class) so that `e◌̂◌̣` and `e◌̣◌̂` normalize to the same thing.

### 2. The four normalization forms

| Form | Decompose? | Recompose? | Compatibility? | Use it for |
|------|-----------|-----------|----------------|-----------|
| **NFD** | yes | no | no | filesystem (macOS HFS+), algorithms that strip accents |
| **NFC** | yes | yes | no | **storage, transport, web, the default** |
| **NFKD** | yes | no | yes (lossy) | search indexing, aggressive matching |
| **NFKC** | yes | yes | yes (lossy) | identifiers, security canonicalization |

- **NFC** prefers precomposed forms; it is the W3C recommendation for the web and what most systems should store.
- **NFD** keeps base + marks separate; Apple's filesystem historically stored filenames in a near-NFD form, so a file named `é` on macOS may come back as `e`+combining-mark, breaking string comparison against a Linux copy.
- **NFKC/NFKD** also fold *compatibility* equivalents: the ligature `ﬁ` (`U+FB01`) becomes `fi`, the full-width `Ａ` becomes `A`, `①` becomes `1`, superscript `²` becomes `2`. This is **lossy** (you cannot recover the ligature) and **dangerous if misapplied** — but essential for security canonicalization, where `Ａdmin` must be recognized as `Admin`.

**Rule of thumb:** store in **NFC**; for identifier/security comparison use **NFKC** (or the specialized UTS #39 / NFKC_Casefold); never store NFKC where you need to round-trip the exact input.

### 3. Grapheme clusters: counting like a human

A grapheme cluster is what UAX #29 defines as one "user-perceived character." Examples that are **one grapheme but many code points**:

- `é` as `e`+`U+0301` — 2 code points, 1 grapheme.
- 👍🏽 (thumbs-up + medium skin tone `U+1F3FD`) — 2 code points, 1 grapheme.
- 🇺🇸 (two regional indicators) — 2 code points, 1 grapheme.
- 👨‍👩‍👧‍👦 (man ZWJ woman ZWJ girl ZWJ boy) — 7 code points, 1 grapheme.
- `각` Korean syllable when typed as jamo `ᄀ ᅡ ᆨ` — 3 code points, 1 grapheme.

**No fixed-width encoding ever makes a grapheme one unit.** Counting graphemes requires running the segmentation algorithm (UAX #29), available via `Intl.Segmenter` (JS), ICU `BreakIterator` (Java/C++), `unicode-segmentation` (Rust), or `\X` in a Unicode-aware regex engine. "Maximum 20 characters" for a display name should count *graphemes*; truncation and reversal that respect grapheme boundaries are the only ones that keep emoji intact.

### 4. Case folding ≠ lowercasing, and it is locale-sensitive

For caseless comparison, use **case folding** (`String.prototype.toLowerCase` is not it; ICU/`unicodedata` provide `casefold`). Case folding is designed to be stable and locale-independent for *matching*, whereas `toUpperCase`/`toLowerCase` are for *display* and are locale-sensitive. The traps:

- **Turkish/Azeri dotted/dotless i:** uppercase `i` is `İ` (dotted) and lowercase `I` is `ı` (dotless) in Turkish locale. So `"I".toLowerCase("tr")` is `"ı"`, not `"i"`. A case-insensitive comparison done with the Turkish locale will treat `FILE` and `file` as *different*. This has broken real authentication and config code (the "Turkish-i bug").
- **German ß:** historically `"ß".toUpperCase()` was `"SS"` (one char becomes two), and only in 2017 did the capital `ẞ` (`U+1E9E`) get official status. Case folding handles `ß` ↔ `ss` for matching.
- **Greek final sigma:** `Σ` lowercases to `σ` mid-word but `ς` at word end — a *context-dependent* lowercasing rule. So lowercasing is not a pure per-character map.
- **Expansion:** some characters change length when cased (`ß`→`SS`, `ﬁ`→`FI`), so `s.length` is not preserved by casing.

**Discipline:** for *security/identity* comparison, use full Unicode case folding (ideally NFKC_Casefold) with the **root/invariant locale**, never the user's locale. For *display*, use the user's locale.

### 5. Collation: sorting is not code-point order

Sorting strings by code point gives nonsense to humans: `Z` (`U+005A`) sorts before `a` (`U+0061`), accented letters scatter to wherever their code points fall, and `10` sorts before `9`. The **Unicode Collation Algorithm (UCA)** defines a multi-level comparison:

1. **Primary:** base letter (`a` = `á` = `A` at this level).
2. **Secondary:** accents (`a` < `á`).
3. **Tertiary:** case (`a` < `A`).
4. **Quaternary:** punctuation/variants.

On top of UCA, each **locale tailors** the order: Swedish sorts `å ä ö` *after* `z`; German phonebook order treats `ä` like `ae`; Spanish once treated `ll` as one letter. There is no single "correct" sort — it depends on the user's language. Use a locale-aware collator (`Intl.Collator`, ICU `Collator`, `golang.org/x/text/collate`), never `<` on raw strings, for anything a user will read as "alphabetical."

---

## Code Examples

### The "café ≠ café" problem and its fix

```python
import unicodedata

a = "café"          # café  (precomposed é, U+00E9)
b = "café"         # café  (e + combining acute U+0301)
print(a == b)            # False  ← different code points!
print(len(a), len(b))    # 4 5    ← even the lengths differ

# Fix: normalize both to NFC (or both to NFD) before comparing
print(unicodedata.normalize("NFC", a) == unicodedata.normalize("NFC", b))  # True
```

### Compatibility normalization (NFKC) flattens look-alikes

```python
import unicodedata
s = "ﬁle Ａdmin ②"            # ligature fi, full-width A, circled 2
print(unicodedata.normalize("NFKC", s))   # "file Admin 2"
# Essential for security: "Ａdmin" must canonicalize to "Admin"
```

### Counting and reversing by grapheme (JavaScript, Intl.Segmenter)

```javascript
const family = "👨‍👩‍👧‍👦";
console.log(family.length);              // 11  ← UTF-16 code units
console.log([...family].length);         // 7   ← code points
const seg = new Intl.Segmenter("en", { granularity: "grapheme" });
console.log([...seg.segment(family)].length); // 1  ← what a human sees

// Grapheme-safe reverse (keeps the family intact):
function reverseGraphemes(str) {
  const segs = [...new Intl.Segmenter().segment(str)].map(s => s.segment);
  return segs.reverse().join("");
}
console.log(reverseGraphemes("a👨‍👩‍👧‍👦b")); // "b👨‍👩‍👧‍👦a"  (family preserved)
```

### The Turkish-i trap

```java
String upper = "TITLE";
// Default/English locale:
System.out.println(upper.toLowerCase(Locale.ENGLISH)); // "title"
// Turkish locale: I -> ı (dotless), not i!
System.out.println(upper.toLowerCase(new Locale("tr"))); // "tıtle"

// Case-insensitive identity comparison MUST use a fixed locale (ROOT) or case folding,
// never the request's locale:
boolean same = "FILE".equalsIgnoreCase("file");          // true in most locales...
// ...but equalsIgnoreCase is locale-independent in Java; the danger is toLowerCase(userLocale).
```

### Locale-aware sorting (collation)

```javascript
const words = ["zebra", "äpfel", "apple", "Über", "apfel"];
console.log([...words].sort());                       // code-point order: ["Über","apfel","apple","zebra","äpfel"]  — wrong for humans
const de = new Intl.Collator("de");
console.log([...words].sort(de.compare));             // German order, ä grouped with a
const sv = new Intl.Collator("sv");
console.log([...words].sort(sv.compare));             // Swedish order, ä/ö after z — DIFFERENT result
```

### Case folding for safe comparison (Python)

```python
# str.casefold() is stronger than str.lower() for matching:
print("ß".casefold())            # "ss"
print("ß".lower())               # "ß"  (no change)
print("Σ".casefold(), "ς".casefold())  # both fold toward sigma for matching
# Identity comparison: normalize THEN casefold
import unicodedata
def identity_key(s):
    return unicodedata.normalize("NFKC", s).casefold()
print(identity_key("Ａdmin") == identity_key("admin"))  # True
```

---

## Coding Patterns

**Pattern 1: The canonicalization pipeline.** For identities: `NFKC → casefold → confusable-skeleton check`. For general comparison: `NFC → compare`. Build this once, reuse everywhere, and make raw `==` on user text a code-review red flag.

**Pattern 2: Normalize at the boundary, store canonical.** Normalize on the way in (API/form) and store the canonical form, so every downstream comparison is already consistent. Keep the raw input separately only if you must render it back exactly.

**Pattern 3: Carry the locale explicitly.** Pass locale into every case/collation call. Use the *invariant* (`ROOT`/`und`) locale for machine comparisons and the *user* locale only for human-facing display and sorting.

**Pattern 4: Use a grapheme iterator for any "per character" UI work.** Counting, truncating with an ellipsis, cursor movement, and reversal all use the segmenter, not indexing.

**Pattern 5: Pick NFC vs NFKC by intent, and document it.** NFC preserves meaning-bearing distinctions; NFKC erases formatting distinctions. Choosing wrong either lets spoofs through (too lenient) or merges legitimately different text (too aggressive).

---

## Best Practices

1. **Normalize before you compare, hash, sort, or store.** Untreated Unicode equality is a bug waiting to happen.
2. **Store NFC; canonicalize identities with NFKC_Casefold.** Keep them as separate, intentional steps.
3. **Never lowercase with the user's locale for security decisions.** Use case folding with the invariant locale to dodge the Turkish-i and Greek-sigma traps.
4. **Sort with a locale-aware collator,** never `<` on strings, for anything users read alphabetically.
5. **Count and slice by grapheme** for user-facing length and truncation.
6. **Re-normalize filenames** when comparing paths that may have crossed macOS.
7. **Pin your Unicode/ICU version** and know that segmentation and case data change between Unicode releases — test fixtures may need updating.
8. **Add a confusable/homoglyph check** to identity canonicalization (foreshadowing `professional.md`'s security section).

---

## Edge Cases & Pitfalls

**The decomposed-é equality failure.** `"é" == "é"` is `false` when one is precomposed and one is decomposed. Every cache, set, dedupe, and `==` over user text is suspect without prior normalization. This is the canonical bug of this page.

**The Turkish-i authentication bug.** `username.toLowerCase()` on a Turkish-locale server turns `ADMIN` into `admın`, so a comparison against `admin` fails — or, worse, lets a different string match. Real systems have shipped this. Use case folding with `ROOT`.

**Grapheme-blind truncation.** Cutting a display name at code point 20 can split 👨‍👩‍👧‍👦 into orphaned people, or strip a skin-tone modifier and change the meaning. Truncate at a grapheme boundary.

**NFKC destroying meaning.** Applying NFKC to mathematical or stylized text destroys distinctions: `ℌ` (mathematical H) becomes `H`, superscripts collapse, the math symbol `∑` may merge with Greek sigma in some contexts. Do not NFKC content you must render faithfully.

**macOS filename round-trip.** A file created as `é` (NFC) may be listed back by the OS as `e`+combining-mark (NFD). String-compare against your in-memory NFC name and it "does not exist." Normalize both sides.

**Collation is not transitive across locales.** A list sorted "correctly" for German is "wrong" for Swedish. There is no global order; caching a sort and serving it to all locales is a defect.

**Combining-mark stacking and ordering.** Multiple combining marks on one base have a canonical order. Two visually identical strings with marks in different source order are canonically equal only after normalization; comparing them raw fails.

**`toUpperCase` changes length.** `"ß".toUpperCase()` → `"SS"`. Code that assumes case operations preserve length (buffer sizing, column alignment) breaks.

**Zalgo / unbounded combining marks.** A base character can carry arbitrarily many combining marks (the "Zalgo text" effect). This is valid Unicode but can be abused to overflow rendering or inflate length; some systems cap the number of combining marks per base.

---

## Apply it

1. State the system invariant that **Character & String Internals (Unicode)** must protect.
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

- Which invariant must remain true when Character & String Internals (Unicode) fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
