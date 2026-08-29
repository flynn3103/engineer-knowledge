# ASLR & Mitigations — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **ASLR & Mitigations** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Entropy economics: bits per dollar

Treat randomization bits like a budget with non-linear returns.

- **The cheap, decisive win is 64-bit + PIE.** Moving from 32-bit (~16 mmap bits, brute-forceable) to 64-bit (~28+ bits) is the single largest improvement, at near-zero runtime cost. Everything else is marginal by comparison.
- **Marginal bits have diminishing security value against the dominant threat.** The dominant real-world bypass is the **info leak**, which is *entropy-independent* — it doesn't matter whether you had 28 or 40 bits if one pointer is disclosed. So past a brute-force-resistant threshold, spending engineering effort on *more entropy* is usually worse value than spending it on **leak resistance** (enforcement layer, OOB-read elimination, re-randomization).
- **Where extra entropy *does* pay:** against the **brute-force/BROP** class on forking servers and against **side-channel** narrowing — but even there, *layout non-reuse* (re-exec) and side-channel mitigations (KPTI) dominate raw bit count.

The professional framing: **bits stop brute force; they do nothing against leaks. Budget accordingly — buy the cheap bits (64-bit PIE), then invest in leak resistance, not in shaving more entropy.**

### 2. The cross-platform mitigation matrix

Each platform implements the same *concepts* with different defaults, opt-ins, and gaps. You must track them per platform.

**Linux / glibc:**
- ASLR via kernel `randomize_va_space` (default 2); stack/mmap/brk + PIE load bias.
- PIE/PIC via `-fPIE -pie`; many distros default to PIE for system binaries.
- NX via `-z noexecstack`; RELRO via `-z relro -z now` (Full); canaries via `-fstack-protector-strong`; FORTIFY via `-D_FORTIFY_SOURCE=2/3`.
- CET via `-fcf-protection=full` + `-z shstk` (kernel + hardware support required).
- Kernel: KASLR (default on), KPTI, optional FGKASLR.

**Windows:**
- ASLR per-image via `/DYNAMICBASE` (default on for modern toolchains); **HEASLR** via `/HIGHENTROPYVA` for 64-bit; **Mandatory ASLR / Bottom-up ASLR** via Exploit Protection (system or per-app), the successor to **EMET**.
- DEP via `/NXCOMPAT`.
- Stack cookies via `/GS`; SafeSEH / SEHOP for exception-handler integrity; **CFG (Control Flow Guard)** via `/guard:cf` (forward-edge CFI), **XFG** (extended), and hardware **CET shadow stack** support.
- Caveat: **Mandatory ASLR without Bottom-up ASLR can relocate to a low-entropy fixed slot** — a known footgun; enable both together.

**macOS / iOS:**
- ASLR on by default; all system binaries position-independent; the **dyld shared cache** gets a per-boot **slide**.
- DEP/W^X enforced; **`MAP_JIT`** + `pthread_jit_write_protect_np` is the sanctioned JIT W^X path (especially on Apple Silicon, which enforces W^X strictly).
- **Pointer Authentication (PAC)** on Apple Silicon is pervasive (return addresses, function pointers) — a deterministic enforcement layer that holds even when ASLR is leaked. **BTI** likewise.
- iOS adds platform constraints (code signing, restricted JIT entitlements) that shrink the JIT-spray surface.

**Android:**
- Linux kernel underneath: KASLR, ASLR for native code; PIE has been *required* for executables for years.
- **Zygote**: apps fork from a pre-initialized template process, so they **share the zygote's per-boot layout** — a deliberate startup optimization with an ASLR consequence (analogous to fork-without-exec). Mitigated by per-boot re-randomization of the zygote and the app-process model, but worth knowing.
- ARM PAC/BTI/MTE on modern devices; **MTE (Memory Tagging Extension)** is the strategic memory-safety hardware play, tagging allocations to catch OOB/UAF probabilistically.
- SELinux, seccomp, and scudo/hardened allocator round out the native-hardening story.

### 3. Measurement and enforcement at fleet scale

Policy you can't measure is aspiration. Build the pipeline:

- **Per-build attestation:** capture the exact compiler/linker flags into provenance metadata; reject artifacts missing the required set.
- **Binary-level verification:** `checksec`/`readelf` (Linux), `dumpbin /headers` and `/dependents` or BinSkim (Windows), `otool`/`codesign` (macOS) — run on *every* artifact, including **vendored and transitive** binaries, not just first-party.
- **Fleet telemetry:** sample running processes for `/proc/pid/maps` randomization, RELRO status, KPTI state, KASLR-on, CET enablement — to catch *runtime* regressions (a misconfigured host, a disabled sysctl).
- **Gate on the weakest link:** a product's hardening posture is the *minimum* across all loaded objects. CI must fail if any module (including a vendored DLL/.so) drops below policy.

### 4. Residual-risk modeling

Mitigations don't make exploitation impossible; they change its *cost and prerequisites*. Model it explicitly:

- **Given a memory-corruption bug, what does the attacker still need?** With NX+ASLR+Full RELRO+canary+CET, they typically need: an info leak (for ASLR), a corruption primitive that satisfies CET/CFI (much harder than plain ROP), and possibly a way around shadow stacks for returns. Enumerate which of your bugs supply which capabilities.
- **Score by bypass class, not by "mitigation on/off."** A forking server with all flags on but fork-without-exec is *brute-forceable* despite a perfect checksec report. A JIT process with all flags on still has the JIT surface. The matrix that matters is bug-class × mitigation, per component.
- **Track the leak surface as a first-class asset.** Out-of-bounds reads, uninitialized-memory disclosure, verbose diagnostics, side-channel exposure — these are your ASLR's real adversary. Reducing them often beats adding bits.

### 5. The trade-off conversations you own

- **Full RELRO vs. startup latency:** eager binding resolves all symbols up front. For short-lived, frequently-forked processes this can matter; for long-lived services it's noise. Default Full; exempt only with data.
- **CET / shadow stack / KPTI vs. cycles:** generally low (shadow stack is cheap; KPTI's cost is context-switch-bound and workload-dependent). Measure on *your* workload; these are usually worth it for anything attack-exposed.
- **Re-randomization vs. complexity:** powerful against leaks but requires consistent live-pointer fixup; mostly research-grade in general-purpose software. Know it exists; deploy where a productized form is available.
- **High-entropy ASLR vs. address-space reservations:** apps that reserve huge contiguous virtual ranges (some databases, GC runtimes) can interact with HEASLR placement; validate.
- **Mandatory ASLR pitfalls (Windows):** force-relocation without bottom-up randomization can *reduce* entropy. The trade-off is "compatibility with legacy non-ASLR DLLs" vs. "low-entropy fixed slot." Prefer enabling both, or fixing the DLL.

### 6. Governance: keeping hardening from regressing

The recurring failure mode is *silent regression*: a build flag dropped during a refactor, a vendored binary added without ASLR, a sysctl reverted on a host, a Mandatory-ASLR policy that quietly relocated to low entropy. Govern it:

- **Codify policy** as machine-checkable rules (required flags per platform/artifact class), with an explicit, reviewed exception register.
- **Block on regression** in CI and at deploy-time (admission control for container images checking their binaries).
- **Inventory and re-scan continuously** — supply-chain artifacts change; re-verify on every ingest.
- **Treat a hardening regression as a security incident**, not a build warning.

---

## Code Examples

Operational and defensive only.

### Fleet-wide Linux hardening audit (fail on weakest link)

```bash
#!/usr/bin/env bash
# Fail if ANY ELF in the tree is missing PIE / Full RELRO / NX / canary.
set -euo pipefail
fail=0
while IFS= read -r -d '' f; do
  json=$(checksec --file="$f" --output=json 2>/dev/null) || continue
  echo "$json" | grep -q '"pie":"yes"'        || { echo "NO PIE: $f"; fail=1; }
  echo "$json" | grep -q '"relro":"full"'     || { echo "WEAK RELRO: $f"; fail=1; }
  echo "$json" | grep -q '"nx":"yes"'          || { echo "NO NX: $f"; fail=1; }
  echo "$json" | grep -q '"canary":"yes"'      || { echo "NO CANARY: $f"; fail=1; }
done < <(find ./dist -type f -name '*.so*' -o -type f -perm -u+x -print0)
exit $fail
```

### Verifying CET / shadow-stack property in shipped binaries

```bash
# GNU property note advertises SHSTK / IBT support.
readelf -n ./program | grep -iE 'SHSTK|IBT' \
  || echo "WARN: no CET properties — built without -fcf-protection?"
```

### Windows: confirm DYNAMICBASE / HIGHENTROPYVA / NXCOMPAT / CFG

```text
:: dumpbin reveals the image's opted-in mitigations.
dumpbin /headers app.exe | findstr /i "Dynamic NX High Entropy"
::   "Dynamic base"        -> /DYNAMICBASE (ASLR)
::   "NX compatible"       -> /NXCOMPAT (DEP)
::   "High Entropy Virtual Addresses" -> /HIGHENTROPYVA
:: dumpbin /loadconfig app.exe | findstr /i "Guard"   -> CFG (/guard:cf)
:: Microsoft BinSkim is the policy-grade scanner for CI.
```

### macOS: confirm PIE and signing/JIT entitlements

```bash
otool -hv ./app | grep -i PIE          # MH_PIE flag present => position-independent
codesign -d --entitlements :- ./app    # inspect allow-jit / restricted entitlements
```

### Detecting a hardening regression in CI (concept)

```bash
# Compare current artifact's mitigation set against a stored baseline.
# Any downgrade (e.g., full->partial RELRO, pie yes->no) fails the build.
diff <(scan_mitigations ./build/app) ./policy/app.baseline \
  || { echo "HARDENING REGRESSION DETECTED"; exit 1; }
```

### Linux runtime posture check (host fleet)

```bash
echo "randomize_va_space=$(cat /proc/sys/kernel/randomize_va_space)"   # want 2
echo "kpti: $(cat /sys/devices/system/cpu/vulnerabilities/meltdown)"
grep -qw nokaslr /proc/cmdline && echo "WARN: KASLR disabled" || echo "kaslr: on"
```

---

## Coding Patterns

### Pattern 1: Policy-as-code, enforced at two gates

Encode required mitigations per platform/artifact-class as machine-checkable rules. Enforce at **build** (provenance attestation) *and* **deploy** (admission control re-scans the actual bytes). Two gates catch both build regressions and post-build tampering/substitution.

### Pattern 2: Cover the whole inventory, not the first-party subset

Scan vendored binaries, transitive `.so`/`.dll`, base-image libraries, and JIT/runtime components. The weakest link is almost never your main binary.

### Pattern 3: Budget bits once, then invest in leak resistance

Standardize 64-bit PIE; stop optimizing entropy past the brute-force threshold; redirect effort to enforcement-layer deployment, OOB-read elimination, and side-channel mitigations.

### Pattern 4: Re-exec, don't re-fork, for crash-respawn workers

Across all platforms with a fork/zygote/template model, ensure crashed workers re-randomize (re-exec / fresh process) rather than reusing a shared layout. Audit fork-without-exec, zygote-shared layout, and snapshot/restore paths.

### Pattern 5: Sanction the JIT path per platform

Use the platform's blessed W^X JIT mechanism (`MAP_JIT` + write-protect toggling on macOS/iOS; dual-mapping on Linux), apply constant blinding and randomized placement, and minimize JIT entitlements (iOS).

---

## Best Practices

- **64-bit + PIE as a non-negotiable baseline**, enforced in CI for every artifact.
- **Full RELRO, NX, canaries, FORTIFY** by default; per-platform control-flow enforcement (CET/CFG/PAC/BTI) where supported.
- **Enforce on the weakest link** across the *entire* loaded-object inventory, including vendored/transitive.
- **Measure both build-time flags and runtime posture** (sysctls, KPTI, KASLR, CET) across the fleet.
- **Budget entropy for the brute-force threshold, then invest in leak resistance** — it's where residual risk actually lives.
- **Re-randomize crash-respawned workers** (no fork-without-exec / shared zygote / snapshot reuse).
- **Govern regressions as incidents**; keep a reviewed exception register with expiry dates.
- **Drive toward memory safety** (safe languages, MTE on ARM, sanitizer-verified C/C++) as the strategic endgame; mitigations buy time.
- **On Windows, enable Bottom-up *with* Mandatory ASLR**; never force-relocate into a low-entropy slot.

---

## Edge Cases & Pitfalls

- **Mandatory ASLR without bottom-up randomization (Windows)** relocates legacy DLLs to a *predictable low-entropy* slot — worse than honest about the gap. Enable both, or fix the DLL.
- **Zygote-shared layout (Android)** means app processes inherit the zygote's per-boot randomization; a leak in one app context can have layout relevance until re-randomization. Know the model when threat-modeling mobile.
- **dyld shared cache slide (macOS/iOS)** randomizes the whole system-library cache as a unit per boot — strong, but a single leaked system-library pointer reveals the slide for *all* cached libraries (the "shared cache" amplifies the move-the-deck weakness).
- **`MAP_FIXED`, hugepages, and huge VA reservations** create predictable regions and can interact with HEASLR. Audit allocators, GC runtimes, and databases.
- **Container base images** can ship un-hardened libraries that your scanner misses if it only checks your layer. Scan the *flattened* image.
- **FORTIFY level mismatch:** `_FORTIFY_SOURCE=3` (newer) catches more than `=2` but needs toolchain support; verify which level actually applied (compiler may silently downgrade).
- **CET/PAC coverage gaps:** shadow stack protects returns not forward edges; PAC has signing-gadget and key-management caveats; coarse CFG/IBT still permits some reuse. Don't represent them as absolute.
- **Disabled ASLR in performance/debug images leaking to prod** (golden images built with `nokaslr` or `setarch -R`). Verify the *production* artifact's runtime posture.

---

## Common Mistakes

1. **Auditing only first-party binaries.** The weakest link is usually vendored/transitive or the base image.
2. **Optimizing entropy past the brute-force threshold** while leaving a large leak surface — spending where it doesn't matter.
3. **Passing checksec but shipping fork-without-exec** — a brute-forceable server with a perfect report.
4. **Enabling Mandatory ASLR without bottom-up on Windows** and getting a low-entropy fixed slot.
5. **Treating CET/PAC/shadow stacks as complete control-flow protection** — they have edges and gaps.
6. **No runtime posture telemetry** — a reverted sysctl or `nokaslr` host goes unnoticed.
7. **Hardening regressions handled as build warnings**, not incidents — they silently un-protect products.
8. **Assuming the JIT is covered by process-wide flags** — it's a distinct surface needing W^X + blinding.

---

## Tricky Points

- **Leaks make entropy nearly irrelevant past a threshold.** This inverts naive intuition ("more random = more safe"). Past brute-force resistance, the marginal bit buys almost nothing against the dominant (leak) threat. Communicate this to stakeholders who want "stronger ASLR" when they should want "fewer leaks + enforcement."
- **A perfect checksec report can hide a brute-forceable design.** Tooling verifies *flags*, not *architecture*. Fork-without-exec, shared zygotes, and snapshot reuse are invisible to binary scanners.
- **Shared caches/zygotes amplify the move-the-deck weakness.** When many libraries share one slide/layout, one leaked pointer de-randomizes *all* of them at once — higher blast radius than per-library randomization.
- **Mandatory ASLR can reduce entropy.** A force-relocate that lands in a fixed slot is a relocation, not randomization. The Windows case is the canonical example.
- **The durable metric is residual exploitability, not mitigation count.** Two products with identical checksec output can have very different real risk depending on their bug surface (especially leaks) and architecture (forking, JIT).
- **Memory safety changes the whole equation.** MTE/safe languages remove the OOB reads/writes the bypass tree needs; where deployed, the mitigation matrix matters far less. Track adoption as the strategic line, not a side note.

---

## Apply it

1. Define the user or business outcome that **ASLR & Mitigations** should improve.
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

- Which measurable outcome justifies investing in ASLR & Mitigations?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
