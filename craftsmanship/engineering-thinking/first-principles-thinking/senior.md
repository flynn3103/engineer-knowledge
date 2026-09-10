# First-Principles Thinking — Senior

**Your question:** How do I apply first-principles reasoning to a system-level redesign under real, hard constraints?

At middle level you rebuilt one component from its fundamentals and compared it to a precedent. At senior level the scope is a whole system, and the constraints are a tangle: some genuinely non-negotiable (cost ceilings, physical infrastructure limits, regulatory obligations), others just organizational habit dressed up as if they were physics. Getting the classification wrong is expensive at this scale — treating a real constraint as negotiable can trigger an outage or a compliance breach; treating a habit as a hard constraint locks a whole system into a shape it doesn't need.

## The method: Classify every system constraint before redesigning

For each constraint the current design honors, sort it into one bucket:

| Bucket | Test | Example |
|---|---|---|
| **Physical / infrastructure** | Would this still hold if you rebuilt the system today, on any vendor? | Network round-trip time between two regions; storage cost per GB; a database's write-throughput ceiling |
| **Regulatory / compliance** | Is this required by a law, auditor, or signed agreement? | 7-year immutable retention for financial records; data residency requirements |
| **Business-contractual** | Is this in a signed SLA or contract with a real party? | "Respond to the client's API call within 5 seconds," per the enterprise contract |
| **Organizational habit** | Would this still hold if a different team, with no memory of how we got here, designed this today? | "Each service deploys on its own weekly cadence"; "we always put a cache in front of Postgres" |

The question that separates the first three buckets from the fourth: **"If we started this system today with a blank slate, would this constraint still exist?"** Genuine constraints survive a blank-slate rebuild. Organizational habits don't — they exist because of how the system evolved, not because of what it must do. That doesn't make habits worthless (changing them has real migration cost) — it means they belong in the cost column of the decision, not the constraint column.

## A worked scenario

**Proposal on the table:** move order-processing from synchronous request/response to a fully async, event-driven architecture, because two other teams in the org already did.

**Classify the constraints:**

- **Business-contractual (genuine):** the enterprise API contract requires a response to the client's order-placement call within 5 seconds. Non-negotiable without a contract renegotiation.
- **Regulatory (genuine):** transaction records must be retained 7 years, immutable, with an audit trail. Non-negotiable.
- **Physical/infrastructure (genuine, but closer than it looks):** the current DB connection pool caps at 500 concurrent connections; measured peak load is 350. Real today, but only 30% of headroom — worth watching, not yet a governing constraint.
- **Organizational habit (not genuine):** "each service deploys independently, on its own weekly cadence." This was a 2021 decision made when the team was smaller and coordination overhead was the dominant concern. Nothing external requires it; a blank-slate team today might choose a different cadence entirely. It carries real migration cost to change, but it is not a constraint the redesign must honor.

**Separate the well-precedented piece from the genuinely novel piece:**

- Durable, ordered message delivery between services is a solved problem — other teams in the org have already built and hardened this. Re-deriving it from scratch here would be reasoning-by-first-principles applied where reasoning-by-analogy is the right tool: use the existing message infrastructure.
- Preserving the 5-second client-facing response SLA while making the *write path* itself async is not solved anywhere in the org — no existing pattern combines "respond fast" with "commit slow, and commit correctly, to a system with a 7-year audit requirement." That combination is genuinely novel here, and it's the piece that actually needs first-principles reasoning: derive the write-acknowledgment design from the fundamentals (what must be durably true within 5 seconds vs. what can resolve later), rather than copying either other team's approach wholesale.

**Decision:** adopt the org's existing message infrastructure for delivery (analogy, low risk, already proven). Design the write-acknowledgment path from scratch, explicitly deriving it from the SLA and audit fundamentals (first principles, because nothing precedented fits). Leave the "independent weekly deploy cadence" habit alone for this redesign — flag it as a separate, lower-priority decision with its own cost/benefit case, not something this redesign is required to fix.

## Choose analogy vs. first principles on purpose

Both are legitimate tools. The senior-level skill is choosing between them deliberately, not by default or by mood.

| Favors reasoning-by-analogy | Favors reasoning-by-first-principles |
|---|---|
| The problem is solved elsewhere under matching constraints | The constraints don't match any precedent you can point to |
| Getting it wrong is cheap and easily reversed | Getting it wrong is expensive, slow to detect, or hard to reverse |
| Someone has already verified the precedent's constraints transfer | The combination of constraints is genuinely new for this system |
| Speed matters more than optimality (a known-good answer today beats a perfect answer next month) | The decision will be load-bearing for years, or other teams will copy it |
| The domain is stable and well-understood | The domain, scale, or regulatory environment is actively changing |

A redesign this size almost never falls cleanly into one column. Decompose it — as in the worked scenario above — and assign each piece to the column it actually belongs to, instead of picking one mode for the whole project.

## Common mistakes at senior level

| Mistake | Why it hurts | Fix |
|---|---|---|
| Treating organizational habit as if it were a hard constraint | Locks a system-wide redesign into an unnecessary shape, foreclosing better options | Apply the blank-slate test to every constraint before the design starts, not after |
| Treating a real constraint (compliance, contract) as negotiable because it's inconvenient | Produces a design that looks elegant on paper and fails an audit or breaches an SLA | Verify contractual and regulatory constraints against the actual document, not memory |
| Applying first-principles reasoning to the entire system uniformly | Wastes months re-deriving solved problems (message delivery, auth, storage) that were never in question | Decompose the redesign; reserve first-principles effort for the genuinely novel pieces |
| Applying reasoning-by-analogy to the one piece that's actually novel | Silently imports assumptions from a system with different constraints, producing a design that fails under real load or audit | Name the piece with no true precedent explicitly, and budget real design time for it |
| Presenting "we did it this way at my last company" as evidence for a system-wide choice | Skips verifying that the org's actual constraints (contract, compliance, infra) match | Require the constraint classification table before the proposal is approved |

## Hands-on exercise

Take a system-level redesign your team is currently considering or recently completed.

1. List every constraint the current or proposed design honors.
2. Classify each into physical/infrastructure, regulatory/compliance, business-contractual, or organizational habit, using the blank-slate test.
3. For each organizational-habit constraint, name the migration cost of changing it — separately from whether it's "required."
4. Decompose the redesign into pieces. For each piece, decide: analogy (name the matching precedent) or first principles (name why no precedent fits).
5. Write one paragraph describing what would have gone wrong if you'd applied first principles to the well-precedented pieces, or analogy to the novel one.

## Verify your thinking

- [ ] Can you sort every constraint in this redesign into one of the four buckets, with a reason for each?
- [ ] Did you apply the blank-slate test to constraints that "feel" hard-coded, not just the ones that are obviously habit?
- [ ] Have you decomposed the redesign so first-principles effort goes only to the genuinely novel pieces?
- [ ] For each piece where you chose analogy, can you name the precedent and confirm its constraints actually match yours?
- [ ] For each piece where you chose first principles, can you name specifically why no existing pattern fits?

Continue to [`professional.md`](professional.md).
