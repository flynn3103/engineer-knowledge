# Security and Ethics - Professional

Agent assurance spans application security, distributed authorization,
privacy engineering, model evaluation, safety governance, and incident
response. No single classifier, policy prompt, or framework covers the system.

## Real frameworks and systems

**OWASP Top 10 for LLM Applications** catalogs prompt injection, sensitive
information disclosure, excessive agency, insecure output handling, and other
recurring risks. Use it as a threat-model checklist, not proof of compliance.

**NIST AI RMF** organizes work around Govern, Map, Measure, and Manage. It helps
connect technical evaluations to ownership, impact context, monitoring, and
risk treatment across the lifecycle.

**Google's SAIF** applies secure-by-design principles to AI systems, including
supply-chain integrity, automated defenses, and adapting controls to AI threat
models. It complements rather than replaces standard infrastructure security.

**gVisor and Firecracker** create stronger execution boundaries for hostile
tools through a user-space kernel or microVM. Sandboxing must also remove
ambient credentials, restrict egress, cap resources, and audit artifacts.

## Scale and systemic failure

At 10x, manual approval queues and safety-classifier latency become product
bottlenecks. At 100x, one policy/model rollout can affect every tenant, and
adversaries can distribute probes to evade per-user thresholds. Use canaries,
tenant and global abuse aggregation, kill switches, and independent policy
services with fail-safe behavior.

Privacy failures propagate through prompts, traces, vector stores, caches,
fine-tuning datasets, exports, and backups. Data lineage and deletion must
cover derived artifacts. Security logs need enough evidence for investigation
without becoming a second sensitive-data warehouse.

## Assurance and operations

Dashboard critical policy violations, denied/approved high-impact actions,
cross-tenant canary hits, injection-eval success, sandbox violations, egress,
PII detection/redaction failures, safety quality by slice, human overrides,
and unresolved findings age.

An incident runbook must revoke credentials, disable capability classes,
quarantine affected runs, preserve restricted evidence, notify owners, assess
data exposure, and turn root causes into controls and regression evaluations.

## Design and operations checklist

- [ ] Threat models cover model, tools, data, identity, supply chain, and humans.
- [ ] Authorization, validation, and isolation are deterministic controls.
- [ ] High-impact actions have meaningful, non-bypassable oversight.
- [ ] Privacy lineage and deletion include derived stores and telemetry.
- [ ] Safety and fairness are evaluated by relevant population/risk slices.
- [ ] Red-team findings have owners, deadlines, retests, and release gates.
- [ ] Kill switches and credential revocation are tested operationally.

## Cheat sheet

```text
prompt guidance = behavioral influence, not enforcement
least privilege = smallest data/action scope for the task
defense in depth= independent preventive and detective controls
meaningful review= informed authority to change or reject
assurance       = evidence that controls work over time
```

## Test yourself

1. Design containment for a remote-code tool exploited across multiple tenants.
2. How do you verify deletion of PII that entered embeddings and traces?
3. Which evidence would justify launching an agent in a high-impact workflow?

## Further reading

- OWASP, "Top 10 for Large Language Model Applications"
- NIST, "Artificial Intelligence Risk Management Framework"
- Google, "Secure AI Framework (SAIF)"
- MITRE ATLAS knowledge base
- NIST Privacy Framework and relevant sector-specific regulation
