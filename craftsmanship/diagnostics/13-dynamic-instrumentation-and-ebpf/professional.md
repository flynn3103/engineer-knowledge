# Dynamic Instrumentation & eBPF — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Dynamic Instrumentation & eBPF** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Dynamic Instrumentation & eBPF Roadmap](README.md)
> **Focus:** At fleet scale, eBPF is the substrate beneath a whole ecosystem — Cilium for networking, Tetragon and Falco for runtime security, Parca/Pixie/Pyroscope for continuous profiling and auto-instrumentation — and the professional job is to wield dynamic tracing as a governed, overhead-budgeted, kernel-skew-aware diagnostic capability that complements (never replaces) in-app APM and OpenTelemetry spans.

---

## Core Concepts

### 1. eBPF is a platform substrate, not just a tracing tool

The same `bpf()` syscall, verifier, JIT, and maps power tracing, networking (XDP/tc), and security (LSM). Diagnostics is one consumer. Recognizing this means you can read the whole landscape with one mental model: *a sandboxed program attached to a kernel hook, communicating with userspace via maps and ring buffers.*

### 2. Agents vs ad-hoc, at scale

A single `bpftrace` invocation is *ad-hoc*: one human, one node, one question, attached then detached. A production deployment is an *agent*: a long-lived DaemonSet that loads pinned, CO-RE programs and exports to a backend. The professional decision is which question deserves an always-on agent (continuous profiling) and which deserves a transient, governed ad-hoc run (incident debugging).

### 3. CO-RE/BTF is the portability contract across a fleet

Across thousands of nodes you will not have matching kernel headers. CO-RE + BTF is what lets one `libbpf` object load on 5.10, 5.15, and 6.6 alike. Where BTF is missing (older or stripped kernels), you fall back to BTFHub-generated BTF or you simply cannot run modern CO-RE agents — this is a hard fleet constraint, not a footnote.

### 4. Overhead is a budget you spend per-event, fleet-wide

Per-event cost (a few hundred nanoseconds for a kprobe) is negligible on one box and enormous when multiplied by a hot syscall × thousands of nodes × always-on. Overhead is a *fleet budget*; you allocate it deliberately and measure it, never assume it.

### 5. Privilege is the central governance lever

Loading BPF historically required `CAP_SYS_ADMIN` (effectively root). `CAP_BPF` + `CAP_PERFMON` (5.8+) narrow that; BPF LSM, program signing, and BPF tokens narrow it further. Who holds these capabilities *is* your security posture.

### 6. eBPF's blind spots are structural, not temporary

eBPF sees syscalls, packets, function entry/exit, and CPU stacks. It does **not** see application-level intent (which customer, which feature flag, which business transaction), and it cannot decrypt TLS payloads without explicit integration (uprobes on the TLS library, or kernel TLS hooks). These limits define where APM/OTel still wins.

## The Broader eBPF Ecosystem

Three pillars sit beside diagnostics. Know them; they share your nodes and your overhead budget.

**NETWORKING — Cilium / XDP / tc.** Cilium is an eBPF CNI that replaces `iptables`-based kube-proxy with eBPF maps for service load balancing, enforces network policy in the datapath, and uses **XDP** (driver RX hook) for DDoS mitigation and line-rate load balancing. The diagnostic payoff is **Hubble**, Cilium's flow-observability layer, which gives L3–L7 visibility into pod-to-pod traffic with zero application changes.

**SECURITY — Falco / Tetragon / BPF LSM.** **Falco** detects threats by matching syscall streams against rules ("a shell spawned in a container", "a write to `/etc/shadow`"). **Tetragon** does runtime security observability *and* in-kernel enforcement via TracingPolicies — and crucially can **kill** a process from kernel context (`Sigkill` action) rather than racing userspace. **BPF LSM** attaches policy programs to LSM hooks. For diagnostics, these produce extremely high-fidelity process and syscall event streams you can correlate during incidents.

**PROFILING — parca-agent / Pixie / Pyroscope.** **parca-agent** samples whole-system CPU stacks via eBPF perf events and ships them for flame-graph analysis — continuous, fleet-wide, no app instrumentation, no symbols-in-binary requirement beyond what frame-pointer/DWARF unwinding needs. **Pyroscope** (Grafana) is the storage/query backend ingesting eBPF and SDK profiles. **Pixie** auto-instruments protocols (HTTP, gRPC, MySQL, Redis, DNS) with uprobes/kprobes for instant service-level telemetry.

> Anchor reminder: this topic is **diagnostics**. Cilium and Tetragon are context because they run on your nodes and emit data you'll use — but your charter is *observing running programs*, not building a CNI or an IPS.

## eBPF Observability Platforms

| Platform | What it auto-instruments (zero app change) | Honest limits |
|----------|--------------------------------------------|---------------|
| **Pixie** | HTTP/gRPC/SQL/Redis/DNS/Kafka via kprobes+uprobes; CPU profiles; service maps | uretprobe protocol parsing is version-fragile; TLS needs uprobe on the SSL lib; data stays node-local by default (limited retention) |
| **Coroot** | Service map, latency/error SLOs, network maps from kernel-level eBPF | infers topology, not business semantics; needs recent kernels/BTF |
| **Parca** | Whole-system continuous CPU profiling | CPU-centric; off-CPU and memory profiling are weaker; needs unwind info |
| **Cilium Hubble** | L3–L7 network flows, DNS, HTTP visibility | requires Cilium as CNI; L7 visibility needs Envoy/proxy or parser support |
| **Datadog / Grafana eBPF agents** | USM (universal service monitoring), network performance, profiling | vendor-coupled; the "zero code" L7 visibility shares the same TLS/version caveats |

The common thread: these platforms give you *infrastructure-level* observability — what is talking to what, how fast, how often, who is burning CPU — without touching application code. What none of them gives you for free is the *distributed-trace context* (a single trace ID following a request across ten services) or *business meaning*. They infer; SDK spans assert.

## Dynamic Tracing in Kubernetes and Containers

Containers complicate the two things tracing depends on: *which process* and *which file path*.

- **PID namespaces.** A process is PID 1 inside its container but some large PID on the host. `bpftrace` runs in the host/root PID namespace, so you target the **host PID**. Find it via `crictl inspect`, `nsenter`, or by reading the cgroup. eBPF maps record host PIDs; translate carefully when reporting.
- **Mount namespaces and uprobe path resolution.** A uprobe attaches to `binary:symbol`, but the container's `/usr/bin/app` does **not** exist at that path in the host's mount namespace. You must resolve the binary through the container's root, e.g. `/proc/<host_pid>/root/usr/bin/app`, or attach by inode. This is the single most common k8s uprobe failure.
- **Privilege.** A pod that loads BPF needs `CAP_BPF`+`CAP_PERFMON` (or `CAP_SYS_ADMIN`), often `hostPID: true`, and access to `/sys/kernel/btf` and `/sys/fs/bpf`. That is a *privileged* pod — treat it like one.
- **kubectl-trace** schedules a `bpftrace` program as a Job on a chosen node, handling the privileged pod spec for you. It is node-scoped: it sees every container on that node, so your script must filter by cgroup/PID.
- **Node vs pod scope.** eBPF is fundamentally a *node*-level (kernel) tool. "Tracing a pod" really means *tracing the node's kernel, filtered to that pod's processes*. There is no kernel-enforced pod boundary for a kprobe — you enforce it in your script.

## Relationship to APM and Auto-Instrumentation

eBPF auto-instrumentation and SDK-based APM are complements with a clean division of labor.

- **What eBPF auto-instrumentation gives you:** request rates, latencies, and error rates per service derived from syscalls and protocol parsing — *with zero code change and immediate fleet coverage.* Excellent for "is this service slow and where," for legacy/third-party binaries you can't instrument, and for the network/syscall layer APM can't reach.
- **What eBPF cannot do:**
  - **Distributed context propagation.** eBPF sees individual syscalls and connections; it cannot reliably stitch a single logical request across N services without the in-band trace/span IDs that an SDK injects into headers. Some platforms heuristically correlate, but it is best-effort, not the ground truth a propagated `traceparent` provides.
  - **Business semantics.** "This request was for customer 42's checkout with coupon X" lives in app memory, not in syscalls.
  - **Encrypted payloads.** With TLS terminating in the app, bytes on the socket are ciphertext. eBPF reads plaintext only by hooking *inside* the TLS library via uprobes (e.g. `SSL_read`/`SSL_write`) or via kTLS — both are integration work, not free.
  - **uretprobe-based HTTP parsing is fragile.** Parsing HTTP/2 or gRPC from buffer contents at function boundaries breaks across library versions, with HPACK compression, and with connection pooling/multiplexing.
- **Why in-app spans still win:** OpenTelemetry SDK spans carry propagated context, semantic attributes, and exact timing of *logical* operations (DB call, cache lookup, business step) regardless of encryption or library version. The professional pattern is **eBPF for breadth and the infra layer, OTel SDK spans for depth and distributed context** — and let them correlate (many platforms join eBPF data to trace IDs).

## Governance and Security of BPF in Production

Loading BPF means running verifier-checked code in the kernel. Verifier-safe is not the same as *trustworthy*. Governance:

- **Who can load.** Historically `CAP_SYS_ADMIN`. Since 5.8, **`CAP_BPF`** (load programs/maps) split from **`CAP_PERFMON`** (perf/tracing reads) lets you grant the minimum. Treat any pod with these as a privileged tenant.
- **Attack surface.** A malicious or buggy BPF program can read kernel memory it's allowed to touch, exfiltrate via maps, add latency to hot paths, or (with LSM/tc/XDP) alter behavior. Verifier limits memory safety, not intent.
- **BPF LSM + signing.** Use BPF LSM hooks to constrain *which* programs may load and from where; sign BPF objects and verify signatures at load. This is the kernel-side of supply-chain defense.
- **Supply-chain risk.** Running a third-party "observability agent" DaemonSet as root on every node is one of the highest-trust grants in your infra. Pin versions, verify provenance/attestation, read the program list, and prefer agents that document their probes.
- **Audit.** Log every `bpf()` load with who/what/when (auditd, or the agent's own audit trail). "An eBPF program was loaded on node X by Y" must be answerable.
- **BPF token (6.9+).** Delegates a *scoped* ability to load BPF into an unprivileged user namespace, so a workload can use BPF without the cluster handing out blanket `CAP_BPF`. This is how multi-tenant BPF gets safer.
- **Locked-down/secure-boot environments.** Lockdown mode and secure boot can restrict tracing (e.g. `kprobe` on arbitrary functions, reading kernel memory) entirely. Some regulated/hardened fleets simply forbid raw BPF tracing — plan for that.

## Fleet-Scale Operational Concerns

- **Overhead budgets.** Set an explicit budget (e.g. "tracing agents may consume ≤1% CPU and ≤200 MB RSS per node"). Measure with the agent on and off. A probe on a hot path (`tcp_sendmsg`, scheduler events) that's fine on one node can melt CPU at fleet scale.
- **Kernel version skew.** Thousands of nodes span many kernels. CO-RE handles most ABI drift, but new hook points, renamed structs, and missing BTF break things unevenly. Maintain a kernel/BTF support matrix.
- **BTF availability.** No `/sys/kernel/btf/vmlinux` → no CO-RE. Use **BTFHub** to ship external BTF, or gate the agent off on unsupported kernels rather than crash-looping.
- **Rollout/canary.** Roll BPF agents like any privileged code: canary on a small node pool, watch CPU/latency/verifier-load failures, then progress. A bad agent version can take down a node's hot path.
- **Pinned maps and bpffs lifecycle.** Pinning to `/sys/fs/bpf` lets programs survive loader restarts and lets tools share maps — but pins are *not* auto-cleaned. Orphaned pins leak kernel memory and confuse the next loader. Own the create/cleanup lifecycle.
- **What breaks on a kernel upgrade.** Attach points may move or disappear; BTF changes; verifier behavior tightens (programs that loaded before may be rejected); LSM/lockdown policy may change. Re-validate agents against the target kernel in your canary *before* a fleet kernel upgrade.

## Code Examples

```bash
# 1) kubectl-trace: run a bpftrace program as a Job on a specific node
#    (counts syscalls by name on that node's kernel)
kubectl trace run node/ip-10-0-3-21.ec2.internal \
  -e 'tracepoint:raw_syscalls:sys_enter { @[probe] = count(); }'
```

```bash
# 2) Trace a containerized process from the node with bpftrace.
#    Resolve the host PID, then filter the kprobe to it.
HOST_PID=$(crictl inspect --output go-template \
  --template '{{.info.pid}}' "$CONTAINER_ID")
bpftrace -e "kprobe:vfs_read /pid == $HOST_PID/ { @bytes = hist(arg2); }"
```

```bash
# 3) Cilium Hubble: observe L7 HTTP flows for a service, zero app change
hubble observe --namespace shop --protocol http \
  --to-pod shop/checkout --output compact --since 2m
# shows source/dest pods, verdict (FORWARDED/DROPPED), HTTP method/path/status
```

```yaml
# 4) Tetragon TracingPolicy: observe (and optionally act on) writes to
#    sensitive files from any process — real-shaped, diagnostics-first.
apiVersion: cilium.io/v1alpha1
kind: TracingPolicy
metadata:
  name: monitor-sensitive-writes
spec:
  kprobes:
    - call: "security_file_permission"
      syscall: false
      args:
        - index: 0
          type: "file"
        - index: 1
          type: "int"
      selectors:
        - matchArgs:
            - index: 0
              operator: "Prefix"
              values: ["/etc/shadow", "/etc/passwd"]
            - index: 1
              operator: "Mask"
              values: ["2"]   # MAY_WRITE
          # matchActions: [ { action: Sigkill } ]  # enforcement (opt-in)
```

```bash
# 5) Continuous profiling note: parca-agent runs as a DaemonSet, samples
#    CPU stacks fleet-wide via perf events, and pushes to Parca/Pyroscope.
#    No app changes; flame graphs per-container, always on.
helm install parca-agent parca/parca-agent \
  --set remoteStore.address=parca.observability.svc:7070 \
  --set sampling.frequency=19   # Hz; keep low for overhead budget
```

```bash
# 6) uprobe across a container's mount namespace: attach via /proc/<pid>/root
HOST_PID=$(crictl inspect --output go-template --template '{{.info.pid}}' "$CID")
bpftrace -e "uprobe:/proc/$HOST_PID/root/usr/local/bin/api:handleRequest \
  { @[comm] = count(); }"
# NOTE: the binary path lives in the container's mount ns, not the host's.
```

## Worked Example — Standing Up Production-Safe Dynamic Tracing

A platform team wants org-wide dynamic tracing for incidents across ~4,000 nodes (kernels 5.10–6.6, mixed BTF) without each engineer needing root on prod.

1. **Define the charter and budget.** Ad-hoc incident tracing only (continuous profiling already exists via parca-agent). Overhead budget: agent idle ≤0.3% CPU; an active trace must auto-expire.
2. **Build the kernel/BTF matrix.** Inventory kernels; confirm `/sys/kernel/btf/vmlinux` presence. For the ~6% of older nodes lacking BTF, ship BTFHub blobs; flag a small legacy pool as unsupported.
3. **Choose the access path.** Deploy `kubectl-trace`-style on-demand Jobs rather than an always-on tracing DaemonSet. Tracing pods are privileged but ephemeral and audited.
4. **Govern privilege.** Grant `CAP_BPF`+`CAP_PERFMON` (not `CAP_SYS_ADMIN`) to the trace Job's ServiceAccount via a dedicated PSP/Kyverno policy. Restrict who can create those Jobs via RBAC; require a ticket reference label.
5. **Audit and bound.** Every trace Job logs requester, node, script, and start/stop. A mutating policy injects an `activeDeadlineSeconds` so no probe outlives the incident. Scripts run from a vetted, signed library; arbitrary one-liners require break-glass approval.
6. **Canary the runner.** New trace-runner versions roll to a 50-node canary pool; watch verifier-load failures and node CPU before fleet-wide.
7. **Document blind spots.** Wiki: "eBPF tracing answers *what the kernel/process is doing*; for cross-service latency and business context use OTel traces in the APM." Prevents misuse as a distributed-tracing replacement.

Result: any on-call engineer can launch a governed, time-boxed, kernel-portable trace on any node, with full audit and a bounded overhead budget — and no standing root DaemonSet.

## A Real Incident, Walked Through

**Symptom.** A payments service shows P99 latency spiking to 4 s intermittently. APM (OTel spans) shows the *application* handler taking 30 ms — the span starts late and the slow time is *outside* the instrumented code. APM is blind to the gap.

**Hypothesis.** Time is lost before the app handler runs: TLS handshake, connection accept backlog, or DNS. The span boundary can't see it.

**Investigate with eBPF on the affected node:**

```bash
HOST_PID=$(crictl inspect --output go-template --template '{{.info.pid}}' "$CID")

# Where is time going in the kernel for this process? Off-CPU + syscall latency.
bpftrace -e '
tracepoint:syscalls:sys_enter_* /pid == '"$HOST_PID"'/ { @start[tid] = nsecs; }
tracepoint:syscalls:sys_exit_*  /pid == '"$HOST_PID"' && @start[tid]/ {
  @lat[probe] = hist(nsecs - @start[tid]); delete(@start[tid]); }'
```

The histogram shows `sys_exit_connect` and `sys_exit_recvfrom` (DNS) with a long tail. A follow-up DNS-specific trace confirms `getaddrinfo` occasionally blocking ~4 s.

**Root cause.** A node-local DNS cache (NodeLocal DNSCache) was crash-looping on a subset of nodes, forcing fallback to a throttled upstream resolver. The latency was entirely in name resolution — *before* any app span opened, and inside an encrypted/connection path APM never instrumented.

**Fix and proof.** Restart/repair NodeLocal DNSCache on the affected pool; the `sys_exit` DNS histogram collapses back to microseconds and P99 recovers. eBPF saw the syscall-level truth APM structurally could not.

## Coding Patterns

- **Time-box every ad-hoc probe** with `activeDeadlineSeconds` / an `interval` self-exit so nothing lingers fleet-wide.
- **Filter to a host PID/cgroup** in-script; never assume "pod scope" exists at the kernel level.
- **Resolve uprobe binaries via `/proc/<pid>/root/...`** to cross the mount namespace.
- **Ship CO-RE objects with BTFHub fallback** and a kernel allowlist gate.
- **Pin maps in bpffs only with an explicit cleanup owner**; treat pins as resources with a lifecycle.
- **Correlate, don't replace:** join eBPF infra data to OTel trace IDs rather than trying to rebuild traces from syscalls.

## Clean Usage

Keep agents minimal and declared: a small, audited probe set; documented overhead; signed objects; least-privilege capabilities (`CAP_BPF`/`CAP_PERFMON`, not `CAP_SYS_ADMIN`); and a clear boundary between always-on agents (profiling) and ad-hoc, time-boxed incident tracing. Every BPF load should be attributable to a human and a reason.

## Best Practices

- Establish and **measure** an overhead budget per node; reject probes that exceed it.
- Maintain a **kernel/BTF support matrix**; gate agents off unsupported kernels gracefully.
- **Canary** BPF agents and trace-runners; re-validate before fleet kernel upgrades.
- Enforce **least privilege**: `CAP_BPF`+`CAP_PERFMON`, BPF LSM, signed programs, BPF tokens for tenants.
- **Audit** every load (who/what/when); restrict who can create privileged trace Jobs via RBAC.
- Treat third-party BPF agents as **high-trust supply chain**: pin, verify, read the probe list.
- Document **blind spots** so teams don't misuse eBPF as a distributed-tracing replacement.

## Edge Cases and Pitfalls

- **Missing BTF** on older/stripped kernels silently disables CO-RE agents — gate, don't crash-loop.
- **Mount-namespace path mismatch** makes uprobes "attach" to the wrong/nonexistent binary.
- **Host vs container PID confusion** mislabels which workload owns an event.
- **Orphaned bpffs pins** leak kernel memory after a crashed loader.
- **Lockdown/secure-boot** can forbid kprobes/kernel-memory reads entirely.
- **Verifier tightening** on a new kernel can reject a program that loaded fine before.
- **Hot-path probes** (`tcp_sendmsg`, scheduler) that are cheap on one node are catastrophic fleet-wide.

## Common Mistakes

- Running an always-on, unaudited, root DaemonSet "for observability" on every prod node.
- Expecting eBPF auto-instrumentation to give true distributed traces — it gives correlated infra data, not propagated context.
- Attaching a uprobe by host path inside k8s and wondering why it does nothing.
- Ignoring kernel skew and shipping a non-CO-RE agent that loads on 12% of the fleet.
- Granting `CAP_SYS_ADMIN` when `CAP_BPF`+`CAP_PERFMON` would do.
- Leaving heavy ad-hoc probes attached after the incident ends.

## Tricky Points

- **"Pod-scoped tracing" is a fiction at the kernel layer** — it's node tracing filtered by you.
- **Verifier-safe ≠ trustworthy** — memory safety says nothing about intent or exfiltration via maps.
- **eBPF can read TLS plaintext** — but only by hooking *inside* the TLS library (uprobe `SSL_read`) or via kTLS; on the raw socket it's ciphertext.
- **CO-RE doesn't fix everything** — new hook points and removed symbols still break across kernels.
- **BPF token** delegates load ability without blanket capability — the path to safer multi-tenant BPF.

## Anti-Patterns at Professional Level

- **eBPF as a silver bullet.** Treating it as the answer to every observability gap; ignoring that it can't see business/distributed semantics.
- **Replacing in-app spans.** Ripping out OTel SDK instrumentation because "eBPF auto-instruments" — losing real distributed context.
- **Ungoverned BPF in prod.** No audit, no signing, blanket `CAP_SYS_ADMIN`, arbitrary one-liners on demand.
- **Ignoring kernel skew.** Assuming one agent build runs everywhere; no BTF matrix.
- **Leaving heavy probes running fleet-wide.** No time-box, no overhead budget — a self-inflicted incident.
- **Trusting third-party agents blindly.** Running someone else's kernel code as root with no provenance check.

## Diagrams and Visual Aids

eBPF as one substrate, many consumers:

```
                         ┌───────────────────────────┐
                         │   bpf() syscall + verifier │
                         │   + JIT + maps/ringbuf     │
                         └─────────────┬─────────────┘
            ┌───────────────┬──────────┼──────────┬────────────────┐
            ▼               ▼          ▼          ▼                ▼
      DIAGNOSTICS      NETWORKING   SECURITY   PROFILING       (focus)
   bpftrace/Pixie/    Cilium/XDP/  Tetragon/  parca-agent/    <- this topic
   Coroot/Hubble        tc        Falco/LSM   Pyroscope
```

Where each layer sees (and stops):

```
  Business intent / customer / coupon ......... ONLY app (OTel span attrs)
  Distributed trace (req across services) ..... OTel propagated context
  TLS plaintext ............................... app, or eBPF uprobe in SSL lib
  HTTP/gRPC/SQL on the wire ................... eBPF protocol parsing (fragile)
  Syscalls / IO / connect / DNS latency ....... eBPF (the gap APM misses)  ◀──
  CPU stacks / scheduling / off-CPU ........... eBPF perf events
```

k8s uprobe path resolution across namespaces:

```
   host mount ns                         container mount ns
   ─────────────                         ──────────────────
   /usr/bin/bpftrace                      /usr/local/bin/api   (PID 1 inside)
        │                                        ▲
        │ attach uprobe ─── WRONG: /usr/local/bin/api (not on host)
        └────────────────── RIGHT: /proc/<host_pid>/root/usr/local/bin/api
                                   (host PID via crictl inspect)
```

---

## Apply it

1. Define the user or business outcome that **Dynamic Instrumentation & eBPF** should improve.
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

- Which measurable outcome justifies investing in Dynamic Instrumentation & eBPF?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
