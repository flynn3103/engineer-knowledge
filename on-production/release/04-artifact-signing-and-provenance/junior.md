# Artifact Signing & Provenance — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Artifact Signing & Provenance** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Release Engineering](../README.md) → Artifact Signing & Provenance

*Proving that the artifact you downloaded is the real one — and that nobody tampered with it on the way to you.*

---

## Core Concept 1 — The trust problem

- Scenario: you run `docker pull registry.example.com/app:1.4.0`. The image arrives. Should you run it?
- Honest answer: you have no idea who built it or whether it's the same image the author published.
- What sits between the author and you, and can hand you tampered bytes:
  - **The registry** could be breached, and an attacker could replace `1.4.0` with a backdoored image under the same tag.
  - **A CDN or mirror** could serve a cached, tampered copy.
  - **Your own proxy** could be misconfigured or compromised.
  - **The tag** `1.4.0` is just a mutable pointer — anyone with push access can move it to different bytes.
- Key insight: **transport security (HTTPS) only protects bytes in motion between two hops.** It does not tell you the *source* was honest or the *storage* was untouched. TLS proves you are talking to `registry.example.com`; it does not prove `registry.example.com` is serving the author's real image.
- Signing flips the model: instead of trusting the channel, you trust a **cryptographic proof attached to the artifact itself**. The proof is verified on your machine, so a compromised middle box cannot fake it.

---

## Core Concept 2 — Hashes prove integrity

- A cryptographic hash function (SHA-256) turns any bytes into a fixed-length fingerprint.

```bash
# Hash a file
sha256sum app-1.4.0-linux-amd64
# a1b2c3...e9f0  app-1.4.0-linux-amd64
```

- Two properties make this useful:
  1. **Deterministic** — the same bytes always produce the same hash.
  2. **Tamper-evident** — flip a single bit and the hash changes completely. You cannot feasibly craft different bytes with the same SHA-256.
- If a project publishes the expected hash on a trusted page, you can verify what you downloaded:

```bash
# Verify a downloaded file against a published checksum file
sha256sum -c SHA256SUMS
# app-1.4.0-linux-amd64: OK
```

- Container images use the same idea — a tag is mutable, but a **digest** is not:

```bash
# Pin to immutable bytes, not a movable tag
docker pull registry.example.com/app@sha256:5d41402abc4b2a76b9719d911017c592...
```

- Limitation: a hash alone is weak as *origin* proof. If the attacker controls both the artifact and the page listing its checksum, they can publish a matching hash for their tampered file. A hash answers "did the bytes change since this hash was taken?" — it does **not** answer "who took it?" For that you need a signature.

---

## Core Concept 3 — Signatures prove origin

- A signature binds a hash to an **identity** using a private key. The flow:
  1. The publisher hashes the artifact.
  2. The publisher signs that hash with their **private key**.
  3. You receive the artifact, the signature, and the publisher's **public key**.
  4. You verify the signature against the public key. If it checks out, only the holder of the private key could have produced it.
- The classic tool is GPG (GNU Privacy Guard):

```bash
# Publisher signs (creates a detached .sig file)
gpg --detach-sign --armor app-1.4.0-linux-amd64
# produces app-1.4.0-linux-amd64.asc

# Consumer verifies
gpg --verify app-1.4.0-linux-amd64.asc app-1.4.0-linux-amd64
# gpg: Good signature from "Release Bot <release@example.com>"
```

- What a signature adds over a bare hash: **assurance about the source**.
- The hard question it raises: how do you get the *right* public key, and trust it belongs to the real publisher?
- GPG made this painful in practice — developers lost keys, forgot passphrases, or signed with keys nobody had verified. Keyless signing (next concept) was invented largely to fix this human problem.

---

## Core Concept 4 — Your first signature with cosign

- `cosign` (part of the Sigstore project) lets you sign without managing a long-lived key file.
- Instead, you authenticate with an identity provider (Google, GitHub, Microsoft) and Sigstore issues a **short-lived certificate** tied to your identity. This is **keyless signing**.

```bash
# Install (Homebrew shown; see Sigstore docs for other platforms)
brew install cosign

# Sign an image by its digest (keyless — opens a browser to log in)
cosign sign registry.example.com/app@sha256:5d41402abc4b2a76b9719d911017c592...
```

- What happens under the hood:
  1. cosign gets a token proving *who you are* from your identity provider (OIDC).
  2. Sigstore's CA (**Fulcio**) issues a certificate valid for a few minutes, stamped with your identity (e.g. `release@example.com`).
  3. cosign signs the image digest with the key in that short-lived cert.
  4. The signature is recorded in a public **transparency log** (**Rekor**) so anyone can later see that this signature was made, by whom, and when.
  5. The signature is stored alongside the image in the registry.
- Net effect: you never created, stored, or rotated a key file. The "key" lived for minutes and is gone. What persists is the *record* of who signed what, when.

> You will go deeper on Fulcio and Rekor at the **Middle** level. For now: keyless = "log in, sign, the proof is public."

---

## Core Concept 5 — Verifying before you trust

- Signing is only half the job. The value appears at **consume time**, when you verify before using the artifact.

```bash
# Verify a keyless signature: you must state WHO you expect signed it
cosign verify \
  --certificate-identity=release@example.com \
  --certificate-oidc-issuer=https://accounts.google.com \
  registry.example.com/app@sha256:5d41402abc4b2a76b9719d911017c592... | jq .
```

- Two flags carry the real meaning:
  - `--certificate-identity` — the identity you *require* to have signed (an email or a CI workflow URL).
  - `--certificate-oidc-issuer` — *which* login provider must have vouched for that identity.
- If you omit these, you only learn "*someone* signed this," which is nearly worthless — an attacker can sign their own malicious image too. **The point is to demand a specific, expected signer.**
- For GPG-signed downloads, verification is symmetric: you import the publisher's known public key, then `gpg --verify`. The hard part is getting that key from a trustworthy source in the first place.

> Critical caveat for every tier: a valid signature proves *who* and *unchanged*. It does **not** prove the artifact is safe, bug-free, or non-malicious. A compromised-but-authentic build will still sign perfectly. Authentic ≠ safe.

---

## Real-World Examples

- **Homebrew / GitHub release binaries.** Many projects publish a `SHA256SUMS` file plus a `.sig`. Users verify the checksum file's signature, then check each binary against it.
- **npm provenance.** Packages published from GitHub Actions can carry Sigstore-backed provenance. `npm audit signatures` checks that what you installed was signed.
- **Docker Official Images & cosign.** A growing number of base images are cosign-signed so platforms can refuse unsigned images.
- **The SolarWinds attack (2020).** A trusted vendor's *build system* was compromised and shipped malicious-but-signed updates — the cautionary tale that authentic does not mean safe, and that you must also trust the *build*, not just the signature.

---

## Common Mistakes

- **Trusting the tag.** `app:1.4.0` can be re-pointed. Sign and verify by **digest**.
- **Verifying without an identity.** `cosign verify` *with no* `--certificate-identity` accepts any signer. Always pin who you expect.
- **Confusing HTTPS with provenance.** TLS secures the pipe, not the source or the storage.
- **Treating a passing signature as a safety guarantee.** It proves origin and integrity only.
- **Publishing the checksum on the same untrusted surface as the artifact.** If an attacker can change both, the hash is meaningless. Sign the checksum, or use a transparency-logged signature.

---

## Apply it

1. Choose one small, known input for **Artifact Signing & Provenance**.
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

- What problem does Artifact Signing & Provenance solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
- Why isn't HTTPS enough to trust an artifact pulled from a registry?
- What's the difference between a hash and a signature?
- What does a valid signature NOT guarantee?
- Why did classic GPG/PGP signing fail in practice?
- What's wrong with running `cosign verify IMAGE` with no other flags?
- Should you sign and verify a tag or a digest, and why?
