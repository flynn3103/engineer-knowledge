# Debugging — Professional (Staff / Principal) Level

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Debugging — Professional (Staff / Principal) Level** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Topic:** [Debugging Roadmap](README.md)
> **Focus:** Debugging as scientific method, incident response, RCA culture, organizational practice, and diagnosing systems you didn't write.

---

## Core Concepts

### 1. The unit of debugging is the *hypothesis*, not the *fix*

A junior thinks "I will try changing this line." A staff engineer thinks "I have four candidate explanations; the cheapest one to test is #3; what observation would falsify it?" The output of an investigation cycle is not a fix — it is a **shrinking set of possible causes**.

### 2. *Mitigation* and *diagnosis* are different jobs

During an incident, your customers want the bleeding stopped. Rolling back, flipping a feature flag, shedding traffic — these are mitigations. They do not require knowing why. Diagnosis can wait until the page is no longer firing. Conflating the two slows both.

### 3. Most outages are *multi-causal*

A single-root-cause outage is rare. The norm is: a latent bug introduced six months ago, a config change last week, a traffic pattern that arrived today, and a missing alert that should have caught it earlier. The Swiss cheese lined up. Looking for "the" root cause is usually a category error.

### 4. Debuggability is a *design property*, not an afterthought

A system that is hard to debug *was made* hard to debug, the same way a system that is hard to test was made hard to test. The fix is upstream of the incident: structured logs, request IDs, exemplars, snapshot endpoints, diagnostic modes, runbooks.

### 5. The org *learns* from incidents only if postmortems are taken seriously

A postmortem that is written and never read is wasted work. A postmortem whose action items don't get done is theater. A postmortem that names a person as "the cause" tells everyone else to hide mistakes. Culture eats process.

---

## Debugging as the Scientific Method

The cycle is **observation → hypothesis → experiment → confirm or falsify → narrow → next hypothesis**. Anyone who has done physics homework knows this; the trick is **applying it under stress**.

| Step | What you do | Common failure mode |
|------|-------------|---------------------|
| Observation | "Errors started at 14:02. They affect EU users only. p99 latency tripled." | Sloppy observation — "everything is broken" is not data. |
| Hypothesis | "Something deployed to the EU region at 14:00 changed behavior." | Vague hypothesis — must be testable. |
| Predict | "If the deploy is the cause, rolling back the EU deploy should restore p99 within 5 minutes." | No prediction → no falsifiability. |
| Experiment | Roll back. Watch p99. | Multiple variables changed at once. |
| Confirm/falsify | p99 returns to baseline → confirmed. Or stays elevated → falsified. | Confirmation bias: declaring victory on noise. |
| Narrow | If confirmed, *which* commit in the deploy? Bisect. | Skipping this — "the deploy was the cause" is not yet a root cause. |

**Falsifiability is the heart of it.** If your "hypothesis" is "I think it's flaky," you cannot test that — there is no observation that would prove you wrong. Re-state until you have something falsifiable: "I think the upstream service is randomly returning 500s on 5% of requests during peak; if so, a 5-minute sample of access logs from that service should show ~5% 5xx." Now it's a science problem.

### The notebook habit

Every production investigation gets its own document. Timestamps are in UTC. Hypotheses are written down *before* you test them, so you can't move the goalposts. Findings — including negative findings — go in. The doc lives next to the postmortem, gets linked from incident chat, and becomes the seed of the timeline.

The notebook serves four purposes:

1. Hand-off: if the on-call shift changes mid-incident, the next person reads the doc and is up to speed.
2. Memory: in the postmortem write-up two days later, you don't have to reconstruct from Slack.
3. Honesty: it's harder to delude yourself when your prior hypotheses are written down and crossed out.
4. Teaching: juniors who read old investigation docs learn how senior engineers think.

> "I'll just keep changing things" loses to disciplined hypothesis tracking because **the space of possible bugs is too large** to brute-force, and because each random change introduces new variables you now have to disentangle. By the third or fourth random change, you cannot tell if the system is broken because of the original bug or because of you.

---

## Root Cause Analysis Done Well

### Trigger vs. root cause

The **trigger** is the immediate event that flipped state: "deploy at 14:02," "leap second at midnight UTC," "a single Kafka broker rebooted." The **root cause** is the latent condition that made the trigger catastrophic instead of harmless: "no canary stage in the deploy pipeline," "leap second handling not tested," "Kafka replication factor was 1 in this cluster."

A common mistake — especially in young orgs — is to fix the trigger ("we'll never deploy at lunchtime again") and call it RCA. You haven't fixed anything. The next trigger will find the same hole.

### The Five Whys, done honestly

Toyota's technique: ask "why?" five times in succession.

1. Why did the site go down? → The payment service ran out of database connections.
2. Why? → A new endpoint opened a connection per request and never released it.
3. Why? → The endpoint was written without using the shared `DBPool` helper.
4. Why? → The author didn't know `DBPool` existed; there's no docs and the linter doesn't catch raw `sql.Open`.
5. Why? → We've never invested in onboarding documentation or guardrails for new contributors.

The fifth "why" is where the systemic insight lives. Stopping at #1 ("we ran out of connections") gives you a patch. Going to #5 gives you a program.

**Five Whys becomes toxic** when used in a meeting to interrogate the author: "Why did *you* write it that way?" That is not RCA, that is a witch hunt. The "why" is asked of the *system*, not the *person*.

### The Swiss cheese model

James Reason's analogy: each layer of defense (code review, tests, canary, alerting, runbook, on-call rotation) is a slice of Swiss cheese with holes in it. An incident happens when the holes happen to line up so a problem passes through every layer untouched. The RCA question is not "what was the hole?" — it is **"why did all five layers fail at once?"**

### Blameless postmortems

The cardinal rule: **"Given what they knew at the time, the people involved acted reasonably."** If that's not true, the question becomes "why did they not know what they should have known?" — which is a system problem (training, alerting, docs), not a person problem.

A postmortem becomes blameful in subtle ways. "Alice deployed the change" is blameless. "Alice deployed the change *without canary*" is starting to lean. "Alice should have known canary was required" is blameful. Rewrite to "The deploy pipeline did not enforce a canary step; this was not visible to the deploying engineer."

Once even one person reads a postmortem and feels personally accused, the *next* incident — at whatever org — gets quietly swept under the rug. Blameless is not feel-good. It is a survival strategy for the learning loop.

---

## Incident Response — The On-Call Discipline

### The phases, in order

```text
detection → triage → mitigation → diagnosis → fix → postmortem
```

**Fixing is not the priority during the incident.** This is the single most-missed lesson at the senior-to-staff transition. Read the order again. Mitigation comes before diagnosis comes before fix. Customers do not care if you understand the bug; they care if their orders are going through.

### Detection

How did you find out? Three options, in declining order of preference:

1. **Your own alerts fired.** SLO breach, error budget burn, anomaly detection. Best case.
2. **A human on your team noticed.** Acceptable.
3. **A customer told you.** Embarrassing. The postmortem must answer: why did *they* see this before *we* did?

### Triage

First five minutes: scope and severity.

- **Who** is affected? All users, one region, one customer, one feature?
- **What** is broken? Read errors, write errors, latency, partial data?
- **How bad**? Money / safety / reputation impact?
- **Is it getting worse?** A slow ramp behaves very differently from an instant cliff.

Triage outputs a **severity level** (SEV-1, SEV-2, SEV-3 — the org's scale) and decides who else gets paged.

### Mitigation patterns

Listed roughly in order of "try this first":

| Mitigation | When to use | Risk |
|------------|------------|------|
| **Roll back the last deploy** | Recent deploy, symptoms started right after | Loses the new feature; may not be the cause |
| **Flip a feature flag off** | Bad code path is gated behind a flag | Requires that someone added the flag |
| **Shed traffic** (rate-limit, return 503 to lowest-priority callers) | Overload; downstream is in retry storm | Customer impact, but bounded |
| **Scale up** | Capacity problem, no code bug | Slow; costs money; doesn't fix root cause |
| **Failover to standby region** | Regional issue | Disruptive; rehearse it first |
| **Block the offending caller** (one bad customer, one bad bot) | A small fraction of traffic is causing 100% of the problem | False positives — careful |
| **Restart the service** | Last resort during incident; almost never the right answer at staff level | Hides the bug; lose in-memory state |

The Incident Commander chooses which mitigation, says it out loud in the channel, and assigns one named person to do it.

### The Incident Commander role

The IC is the **single point of decision-making**, not the smartest engineer in the room. Their job:

- Run the incident channel. Keep timestamps and decisions written down.
- Decide between competing mitigations when engineers disagree.
- Decide when to escalate (more pages, exec notification, customer comms).
- Decide when the incident is over.

The IC is explicitly **not the person writing the fix.** Mixing those roles means the IC stops reading the chat. Hand off if you find yourself coding.

### "Wake people up" judgment

When to page another human at 3am:

- Their expertise is on the critical path *and* the incident is severe enough to justify the cost.
- You've tried the runbook for their service and it didn't resolve.
- You will not learn what you need to know from logs and metrics alone.

When not to page:

- You're curious. Curiosity is not severity.
- You're nervous and want backup. Page your fellow on-call peer, not the service owner.
- It's a SEV-3 and could wait until business hours.

### Stop the bleeding first

The classic anti-pattern: at minute 30 of an outage, an engineer says "wait, I think I see the bug — let me deploy a fix." STOP. Even if they are right, deploying a hotfix during an active incident introduces unbounded new risk. Mitigate first (rollback / flag), *then* take the time to write and test the real fix.

---

## Debugging at Architectural Scale

### Tracing a request across 12 services

The naïve approach: tail the logs of every service. This does not scale beyond three or four services. The professional approach:

1. **Distributed tracing must be in place before the incident.** OpenTelemetry, Jaeger, Tempo, Honeycomb. Every request gets a trace ID. Every internal call propagates it.
2. **Sample a slow request.** Pull its trace.
3. **Read the waterfall.** Each span is a unit of work. Look for the long one.
4. **Drill into the long span.** Is it CPU? Network? Lock contention? Each tier of the trace gives you a finer question.

If you don't have tracing, you don't have a debugger for your architecture. Adding it after the fact, under stress, is brutal.

### Why p99 latency matters more than p50

A user who experiences your system perceives the worst response they see — and they hit your service 50 or 100 times in a session. If p50 is 100ms but p99 is 4s, a user making 70 requests has a ~50% chance of seeing at least one 4-second wait. They will rate you as "slow."

Worse, p99 is where bugs hide. p50 averages out the rare-path code. p99 lights up the cold-start, the cache miss, the retried call, the GC pause. **A staff engineer looks at p99 first.**

### EXPLAIN ANALYZE and query plans

When a database query is slow, do not guess. Run `EXPLAIN ANALYZE` (Postgres) or equivalent. Read it bottom-up. You are looking for:

- **Sequential scans on tables with millions of rows.** Index missing.
- **Nested loops with huge inner-loop counts.** Often a missing join index.
- **Hash joins spilling to disk.** Memory misconfigured.
- **A planner row estimate that is 100× off.** Stale statistics — `ANALYZE`.

A real example: a query that took 4s in prod, 80ms in staging. Same data shape. Cause: the prod table had not been `ANALYZE`d in 3 months and the planner picked a nested loop where a hash join was 50× faster. Fix: scheduled `ANALYZE`. Root cause: nobody set up `autovacuum` thresholds for that table.

### Cache invalidation bugs

The classic: "user X says the page shows yesterday's data; user Y on the same page sees today's." Possible causes, in order of likelihood:

1. **Stale entry in a CDN edge** — different POPs cached at different times.
2. **In-process cache** is per-pod, and X and Y are on different pods.
3. **Invalidate-on-write missed an event** — the write path doesn't publish the invalidation.
4. **TTL is longer than nobody thought** — somebody set it to 24h instead of 24min.

Diagnostic move: have X include a debug header that bypasses the cache and reveals which layer served them. Compare to Y.

### Saga / workflow debugging

In a Temporal or Step Functions world, a "stuck" workflow is a different beast. The workflow is *waiting on something* — a signal, a timer, a child activity. Steps:

1. Open the workflow's execution history.
2. Find the last completed event. The next event is what it's waiting on.
3. If it's waiting on an activity, check whether the activity worker is healthy.
4. If it's waiting on a timer, check the fire time.
5. If it's waiting on a signal, check whether the signal sender ever ran.

Workflows do not "hang" in the OS sense — they are persisted state machines. The bug is always either "the next step is not being triggered" or "the next step has been triggered and is itself stuck."

---

## Reading Other People's Code Under Pressure

You will be paged for services you've never opened. You have 30 minutes to understand enough to be useful. The procedure:

1. **The README and the `cmd/` directory.** What does this service do, in one sentence? What is its entry point?
2. **The HTTP / gRPC / RPC handlers.** What endpoints does it expose? In Go, find `mux.Handle` calls. In Python/FastAPI, find `@app.get`/`@app.post`. In Java/Spring, find `@RestController`.
3. **The dependency graph.** What does it call? Databases, message queues, other services. Look at the config / env vars and the client constructors.
4. **The initialization.** What runs at startup? Caches preloaded? Background goroutines? Cron tasks? This is where state lives.
5. **The error paths.** Search for `return err`, `throw`, `raise`. Where do errors come from and where do they go?

### Following the wire

A "wire trace" is reading the code path of one request from socket to socket. Pick the endpoint that's failing. Trace: HTTP handler → business logic → DB call → external HTTP call → response. Each transition is a place a bug can live. Do not read the whole codebase. Read this one path.

### "What does this code believe about the world"

The fastest mental shortcut for understanding unfamiliar code is to identify its **implicit assumptions**:

- "Every order has at least one line item."
- "Customer IDs are immutable."
- "Redis is always reachable."
- "Time only moves forward."

When a bug shows up in production, it is almost always because **one of those assumptions just got violated.** A customer was deleted. A clock skew sent a timestamp backward. Redis had a 200ms blip. The bug isn't in the code — it's in the gap between what the code believes and what the world actually does.

---

## The Observability Triangle as a Debugging Interface

```text
                    METRICS
                   (what is happening)
                      /\
                     /  \
                    /    \
                   /      \
                  /  YOU   \
                 / ARE HERE \
                /            \
               /______________\
            LOGS             TRACES
       (what happened       (how requests
        in detail)           flow)
```

### What each is good for

| Signal | Good for | Bad for |
|--------|---------|---------|
| **Metrics** | "Is something wrong right now?" Trends. SLO tracking. Cheap at scale. | "Why is this one user's request slow?" High cardinality is expensive. |
| **Logs** | Detail. Stack traces. Audit. The "what exactly happened to request 123" question. | Aggregation. Without structure, you can't slice them. |
| **Traces** | "Where did the time go across services?" Causal chains. | Sampled — the trace you want is often the one that wasn't sampled. |

### Decision tree: where do I look first?

```text
                    Did an alert fire?
                       /         \
                     yes          no
                     /             \
              Look at METRIC      Customer report?
              that triggered           |
              the alert.              yes
                  |                    |
            See a pattern?      Do you have the
                  |             request/trace ID?
                  |                    |
                  v                    v
            Drill into a       Pull the TRACE for
            sampled trace      that ID.
            (exemplar) from    Read the waterfall.
            the metric.              |
                  |                  v
                  v            Find the longest span.
            Read LOGS for      Drill into LOGS for
            that trace ID.     that service.
```

The rule: **metrics tell you something is wrong, traces tell you where, logs tell you what.** Move down the triangle as your question narrows.

### Exemplars

Modern Prometheus + Tempo or Honeycomb setups attach a **trace ID** to selected metric data points. A spike on a "p99 latency" graph is a clickable link to *the actual trace* of one of those slow requests. This is the single biggest workflow improvement in observability over the last five years. If your stack doesn't have it, getting it is a high-leverage investment.

### "We have logs" is not "we have observability"

A system with 4TB of unstructured `printf` lines per day is *less* debuggable than a system with 40GB of structured, sampled, correlated telemetry. Volume is not signal. The question is: from a customer complaint, can you find the responsible request in under 60 seconds? If no, you do not have observability.

---

## Debugging Vendor and Closed-Source Systems

Sometimes the bug is in software you do not have source code for: a vendor SDK, a closed-source database driver, an old binary. The tools change.

### Binary inspection

| Tool | What it tells you |
|------|-------------------|
| `strings binary` | Embedded string literals — version strings, error messages, config keys. |
| `nm binary` | Exported symbols. What functions does this binary advertise? |
| `objdump -d` | Disassembly. Read the actual instructions if you must. |
| `ldd binary` | Shared library dependencies. What does it dynamically link against? |
| `otool -L` (macOS) | Same as `ldd` for Mach-O binaries. |
| `readelf -a` | ELF header detail, section info. |
| `file binary` | Quick "what kind of binary is this?" |

A real example: a vendor SDK's `connect()` was failing with "permission denied." `strings` on the binary revealed it was trying to open `/var/lib/vendor/license.lic`. The actual error was a misleading wrapper. Five minutes of binary inspection saved a support ticket.

### Network capture as ground truth

When the vendor says "the API does X" and your code says it returned Y, capture the wire. `tcpdump`, Wireshark, or `mitmproxy` for HTTPS (with TLS interception). Read what *actually* went over the wire. This wins arguments with vendor support.

### Behavioral fuzzing

Poke the closed system in controlled ways:

- Send malformed input. What error do you get?
- Send valid input with timing variations. Does it behave differently under load?
- Send concurrent requests. Are responses interleaved?
- Disconnect mid-request. Does the connection cleanly close?

You are building a mental model of the system by interrogating its behavior, since you can't read its code.

### Ethics and legality

Reverse engineering of software you've purchased for the purpose of debugging an interop problem is generally allowed (specific to jurisdiction; in the US, see DMCA §1201 exemptions). Distributing decompiled code, defeating copy protection, or violating the vendor's EULA is not. **When in doubt, talk to your legal team before you publish a decompilation in a blog post.**

### File a ticket or work around it?

Decision rule:

- **File a ticket** if the vendor will likely fix it in a release you can adopt; the bug is reproducible; the workaround is ugly or unsafe.
- **Work around it** if the vendor is slow / hostile; you cannot stop your incident waiting for them; you can keep the workaround small and well-commented.

Either way, write down the actual root cause so future engineers don't pay the cost twice.

---

## Building Debuggability INTO Your System

The single highest-leverage thing a staff engineer does. A debuggable system is the difference between a 20-minute incident and a 6-hour one.

### Internal dashboards

For every service you own, there should be one dashboard that answers: **"What is this service doing right now?"** Not "what was it doing yesterday." Right now. Live. Pinned to the on-call's screen.

It should show:

- Request rate (RPS) by endpoint.
- Error rate by endpoint.
- p50/p95/p99 latency by endpoint.
- Saturation: CPU, memory, disk, descriptors.
- Dependencies: latency and error rate of every downstream service.
- Queue depths, if any.
- Recent deploys / config changes.

If a new engineer cannot say "this service is healthy" or "this service is sick" by glancing at this dashboard for 10 seconds, the dashboard is wrong. Iterate.

### Per-request diagnostic mode

A pattern from Envoy, gRPC, and many internal frameworks: a special header (`X-Debug: true` or similar) flips the request into verbose mode. *For that request only*, the service produces:

- Full structured logs at DEBUG level.
- A full (non-sampled) trace.
- Timing breakdowns at every internal boundary.
- The raw input and output.

The on-call engineer adds the header to a curl, replays the customer's request, gets a complete picture without polluting prod logs. The cost is paid only when invoked.

> Authentication and authorization for this header matters. Anyone can DoS your logging pipeline if they can flip everyone into verbose mode. Restrict the header to internal traffic or signed requests.

### Snapshot / state-dump endpoints

A surprisingly underused pattern. Expose a `/debug/state` endpoint (gated by auth) that returns:

- Current in-memory cache contents (or summary).
- Active connection counts.
- Worker pool sizes and queue depths.
- Recent error counts.
- Config values currently in effect.

Now during an incident, instead of guessing what the service believes, you `curl` it and read.

Go's `net/http/pprof` package is the canonical example. The Java equivalents are JMX endpoints and Micrometer's `/actuator/*` (Spring Boot). In Python, `py-spy dump` against a running PID. In Rust, `tokio-console`.

### Backpressure visibility

If your system has queues — Kafka consumers, internal channels, worker pools — the depths must be visible as metrics. A blocked consumer that grows a queue silently is a time bomb.

Three numbers per queue:

1. Current depth.
2. Producer rate.
3. Consumer rate.

If consumer rate < producer rate, you have minutes-to-hours before something breaks. The alert fires *before* the symptoms.

### The "explain yourself" endpoint

Linkerd, Envoy, and well-built internal proxies expose an `/admin/` page where the service explains its own configuration and current behavior in human-readable form: what routes are loaded, what filters are applied, which upstreams are healthy, what TLS certs are in effect. Steal this idea.

A service that can explain itself is debuggable. A service that can only be inspected via its logs is not.

---

## Postmortem Culture

### The Google SRE template (compressed)

1. **Summary** — one paragraph.
2. **Impact** — quantified. "X% of EU users for 47 minutes; ~$Y revenue impact."
3. **Timeline** — UTC timestamps. Every important event.
4. **Root causes** — plural. The actual systemic conditions.
5. **Trigger** — the proximate event.
6. **What went well** — yes, even in a disaster. Detection? Comms? IC handling?
7. **What went poorly** — what we want to never repeat.
8. **Where we got lucky** — the holes that didn't line up but could have.
9. **Action items** — SMART, owned, dated.
10. **Lessons learned** — for the org, not just the team.

A good postmortem is **two to four pages**. Longer means nobody reads it. Shorter means you didn't do the work.

### SMART action items

Specific, Measurable, Achievable, Relevant, Time-bound. "Improve monitoring" is not an action item. "Add an alert on Kafka consumer lag > 10k for > 5min, owned by @alice, due by 2026-06-15" is.

Each action item is a **ticket in the same tracker as the team's normal work**. If it goes into a postmortem doc and not the backlog, it will be forgotten.

### The two-week follow-up

A scheduled meeting two weeks after the incident: walk through the action items list. How many done? Which slipped? Which got reprioritized away? Reprioritization is fine *if* it is conscious; the failure mode is silent decay.

### Sharing across the org

The team had the incident; the org needs to learn from it. Mechanisms:

- A monthly all-hands "incident review" — three postmortems, presented in 10 minutes each.
- A searchable wiki of every postmortem ever, tagged by cause class.
- A mailing list / channel where every postmortem gets cross-posted.
- A "wall of postmortems" near the eng kitchen at orgs that still have offices.

The point: a junior engineer in a totally different team should be able to read a postmortem and learn from it without context. Write for that audience.

---

## Career-Level Patterns

### What makes someone the "person teammates call at 3am"

It is not raw intelligence. It is:

- **Calm under pressure.** They don't panic, don't get loud, don't make rash changes.
- **Pattern recognition.** They've seen GC pauses, descriptor leaks, retry storms, cache stampedes, thundering herds, clock skews, and DNS bugs enough times to recognize the shape.
- **Knowing the unknowns.** They are quick to say "I don't know — let me look" rather than guess.
- **System-wide mental model.** They've read enough of the codebase to know what could be wrong.
- **Tool fluency.** They reach for `tcpdump`, `bpftrace`, `pprof`, or `EXPLAIN` without thinking.

A staff engineer's career goal is to make themselves *not* the person teammates need at 3am — because they have built the systems, dashboards, and runbooks that let teammates handle it themselves.

### The catalog of recurring failure modes

A staff engineer carries a mental catalog of bug *shapes* that recur across every system they've worked on:

| Shape | Symptom | First place to look |
|-------|---------|--------------------|
| **GC pause** | Periodic latency spikes correlated across endpoints | Heap size, GC logs |
| **Descriptor leak** | Service crashes after N days with `EMFILE` | `lsof`, `/proc/<pid>/fd` |
| **Retry storm** | Latency goes up, request count *also* goes up | Retry budget, idempotency keys |
| **Cache stampede** | Brief origin overload aligned with cache TTL | Cache hit rate, TTL config |
| **Thundering herd** | All clients reconnect at the same instant | Connection pool, reconnect jitter |
| **Clock skew** | "Impossible" ordering of events across machines | NTP sync, drift metrics |
| **DNS failure** | Mysterious timeouts to internal services | `dig`, resolver logs, TTLs |
| **Connection pool exhaustion** | Every request waits, but no individual call is slow | Pool size metric vs. usage |
| **N+1 query** | Latency scales with row count | Trace span count, query log |
| **Slow log replay** | Service starts up but is unresponsive for minutes | Startup tracing |
| **Resource limit breach** | Pod gets OOM-killed; container restarts | cgroups, `dmesg`, k8s events |
| **Backpressure absence** | Queue grows monotonically | Producer vs. consumer rate |

Recognizing the *shape* in 10 seconds shortcuts the next 4 hours of investigation.

### Teaching debugging to a junior

You cannot lecture a junior into being good at debugging. The training is:

1. **Sit next to them during an incident.** Narrate your thinking out loud.
2. **Have them drive the next incident.** You watch, don't take over.
3. **Review their investigation docs afterward.** Comment on the hypotheses, not the conclusion.
4. **Make them write the postmortem.** Write the postmortem for them once; have them write the next two.
5. **Pair on weird bugs.** The boring bugs they can solo.
6. **Encourage the catalog.** Have them keep a personal list of bug shapes they've seen.

The fast path is *not* a book. It is shadowed practice with a senior who narrates.

---

## Tools Beyond the IDE

### `bpftrace` one-liners

`bpftrace` lets you instrument the running kernel without recompiling anything. A few production-grade one-liners (Linux):

```bash
# Trace every file open by any process
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s -> %s\n", comm, str(args->filename)); }'

# Count system calls per process, every 5 seconds
bpftrace -e 'tracepoint:raw_syscalls:sys_enter { @[comm] = count(); } interval:s:5 { print(@); clear(@); }'

# Histogram of read() latency
bpftrace -e 'tracepoint:syscalls:sys_enter_read { @start[tid] = nsecs; } tracepoint:syscalls:sys_exit_read /@start[tid]/ { @us = hist((nsecs - @start[tid]) / 1000); delete(@start[tid]); }'

# Catch every TCP retransmit
bpftrace -e 'kprobe:tcp_retransmit_skb { printf("retrans on %d\n", pid); }'
```

These cost almost nothing at runtime and answer questions that would otherwise require a debug build.

### `perf` and flame graphs

```bash
# Sample CPU for 30 seconds
sudo perf record -F 99 -p <pid> -g -- sleep 30

# Generate flame graph (requires Brendan Gregg's FlameGraph scripts)
sudo perf script | ./stackcollapse-perf.pl | ./flamegraph.pl > flame.svg
```

A flame graph shows where CPU time is going as stacked bars. Wide bars = hot. The first time you read one, the answer to "why is my service CPU-bound" jumps out.

### `nettop`, `iotop`, `htop -t`

| Tool | Question it answers |
|------|---------------------|
| `htop -t` | Which threads in which processes are using CPU? |
| `iotop` | Which processes are doing disk I/O? |
| `nettop` (macOS) / `nethogs` (Linux) | Which processes are sending/receiving network traffic? |
| `iftop` | Per-connection network rate |
| `vmstat 1` | System-wide CPU / IO / paging at 1s resolution |
| `dstat -tdn 1` | Combined CPU, disk, network |
| `ss -tnp` | What TCP sockets are open, by process |

### Custom Wireshark dissectors

For proprietary protocols (binary RPCs, internal pub/sub), writing a Wireshark dissector in Lua takes an afternoon and pays back forever. Now everyone on your team can read your wire format in a packet capture.

### The "50-line Go tool" mindset

The hallmark of a staff engineer in debugging mode: when no existing tool answers the question, they write one. A 50-line Go program that polls a metric, reads from a queue, and diffs against expected — built in 20 minutes during an incident — has saved many companies hours of confusion. Carry the muscle of "I will write the diagnostic tool I need." Do not wait for a vendor to ship it.

---

## Code Examples

### Go — a diagnostic mode middleware

```go
package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
)

type ctxKey string

const debugKey ctxKey = "debug"

func DiagnosticMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		debug := r.Header.Get("X-Debug") == "true"
		// In real code, gate this on internal IP / signed header.
		ctx := context.WithValue(r.Context(), debugKey, debug)
		if debug {
			slog.InfoContext(ctx, "diagnostic mode on",
				"trace_id", r.Header.Get("X-Trace-Id"),
				"method", r.Method,
				"path", r.URL.Path,
				"headers", r.Header,
			)
		}
		next.ServeHTTP(w, r.WithContext(ctx))
	})
}

func IsDebug(ctx context.Context) bool {
	v, _ := ctx.Value(debugKey).(bool)
	return v
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{Level: slog.LevelDebug}))
	slog.SetDefault(logger)

	mux := http.NewServeMux()
	mux.HandleFunc("/api/order", func(w http.ResponseWriter, r *http.Request) {
		if IsDebug(r.Context()) {
			slog.DebugContext(r.Context(), "order handler start")
		}
		// ... normal work ...
		w.Write([]byte("ok\n"))
	})

	http.ListenAndServe(":8080", DiagnosticMiddleware(mux))
}
```

### Python — a snapshot endpoint

```python
import threading
import time
from collections import deque
from flask import Flask, jsonify

app = Flask(__name__)

# Live state we want to inspect.
_recent_errors = deque(maxlen=100)
_worker_queue: deque = deque()
_config = {"feature_x": True, "max_workers": 10}
_lock = threading.Lock()

def record_error(msg: str) -> None:
    with _lock:
        _recent_errors.append({"ts": time.time(), "msg": msg})

@app.get("/debug/state")
def debug_state():
    # In real life, require auth. Localhost-only at minimum.
    with _lock:
        return jsonify({
            "queue_depth": len(_worker_queue),
            "recent_errors": list(_recent_errors)[-20:],
            "config": _config,
            "now": time.time(),
            "goroutine_count_equivalent": threading.active_count(),
        })

@app.get("/healthz")
def healthz():
    return "ok", 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
```

### Java — instrumenting a method with Micrometer for exemplars

```java
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import io.micrometer.tracing.Tracer;
import org.springframework.stereotype.Component;

@Component
public class OrderService {
    private final Timer timer;
    private final Tracer tracer;

    public OrderService(MeterRegistry registry, Tracer tracer) {
        this.timer = Timer.builder("order.process")
                .description("Time to process an order")
                .publishPercentiles(0.5, 0.95, 0.99)
                .publishPercentileHistogram()
                .register(registry);
        this.tracer = tracer;
    }

    public Order process(OrderRequest req) {
        return timer.record(() -> {
            var span = tracer.nextSpan().name("order.process").start();
            try (var scope = tracer.withSpan(span)) {
                span.tag("customer.id", req.customerId());
                return doProcess(req);
            } finally {
                span.end();
            }
        });
    }

    private Order doProcess(OrderRequest req) {
        // ...
        return new Order(/* ... */);
    }
}

record OrderRequest(String customerId) {}
record Order() {}
```

### Rust — a request-scoped tracing span

```rust
use tracing::{info, instrument, Level};
use tracing_subscriber::FmtSubscriber;

#[derive(Debug)]
struct Order {
    id: u64,
    customer: String,
}

#[instrument(level = "info", fields(customer = %order.customer))]
fn process_order(order: &Order) -> Result<(), String> {
    info!(order_id = order.id, "processing order");
    validate(order)?;
    charge(order)?;
    fulfill(order)?;
    Ok(())
}

#[instrument]
fn validate(o: &Order) -> Result<(), String> {
    if o.customer.is_empty() { return Err("no customer".into()); }
    Ok(())
}

#[instrument]
fn charge(_o: &Order) -> Result<(), String> { Ok(()) }

#[instrument]
fn fulfill(_o: &Order) -> Result<(), String> { Ok(()) }

fn main() {
    let subscriber = FmtSubscriber::builder()
        .with_max_level(Level::DEBUG)
        .json()
        .finish();
    tracing::subscriber::set_global_default(subscriber).unwrap();

    let order = Order { id: 42, customer: "acme".into() };
    if let Err(e) = process_order(&order) {
        eprintln!("failed: {}", e);
    }
}
```

---

## A Worked Incident Timeline

A realistic SEV-2 incident, narrated end-to-end. All times UTC.

**14:02** — Deploy of `checkout-service` v2.317 completes in the `us-east-1` region. Two-line config change to default cache TTL: `30s` → `300s`. Author: an engineer who wanted to reduce DB load on a hot product-catalog query.

**14:05** — `checkout-service` p99 latency on the `POST /cart/checkout` endpoint is 180ms, normal.

**14:11** — A scheduled background job in `pricing-service` refreshes the product catalog. Catalog version changes. The cache invalidate event is published to Kafka. `checkout-service` consumes it and clears the relevant cache keys.

**14:11:08** — All `checkout-service` pods now have cold catalog caches. The next 1,200 concurrent `POST /cart/checkout` requests, on cache miss, fan out to `pricing-service` to refill. **Cache stampede.**

**14:11:30** — `pricing-service` p99 hits 4.2s. Its connection pool saturates. New requests queue. Latency further increases.

**14:11:45** — `checkout-service` requests, blocked on `pricing-service`, accumulate. Their own connection pool starts to back up. The retry-with-backoff client in `checkout-service` (configured with 3 retries, no jitter) starts firing. **Retry storm.**

**14:12:10** — Alert fires: "checkout-service: error rate > 5% for 1 minute." Page goes to the primary on-call, Alice.

**14:12:11** — Alice acknowledges. Opens the incident channel (`#inc-2026-05-29-checkout`). Pastes the alert. Opens the checkout dashboard.

**14:12:30** — Alice sees: error rate 18%, p99 7.2s. Most errors are `context deadline exceeded` from the `pricing-service` client. She declares SEV-2 and pages the secondary on-call (Bob) and the pricing-service on-call (Carol).

**14:13** — Bob joins. He becomes Incident Commander. Alice focuses on diagnosis.

**14:13:20** — Bob in channel: "**IC: Bob. Strategy: identify mitigation in < 5 min. Diagnosis after.**"

**14:14** — Alice spots the deploy notification at 14:02 in the deploy bot's channel. "Deploy of checkout-service v2.317 14:02. Config change: cache TTL 30s → 300s." Hypothesis: this somehow caused the issue.

**14:14:30** — Bob in channel: "**Decision: rollback checkout-service to v2.316. Owner: Alice. ETA: 4 min.**"

**14:15** — Alice triggers the rollback via the deploy tool.

**14:17** — Carol joins. She reports pricing-service p99 has been steady at 4s for 5 minutes; her dashboards show pricing-service is healthy *as a service* but overloaded.

**14:18** — Rollback to v2.316 completes. Within 30 seconds, checkout-service error rate drops to 2%. Within 90 seconds, pricing-service p99 recovers to baseline. **Bleeding stopped.**

**14:20** — Bob in channel: "**Mitigation succeeded. Incident downgraded to SEV-3. Now: diagnosis.**"

**14:22** — Alice opens the diff between v2.316 and v2.317. Two lines changed: the TTL constant. She still doesn't understand why a longer TTL caused a stampede — a longer TTL should reduce origin load, not increase it.

**14:35** — Carol checks the catalog-refresh code in `pricing-service`. The refresh publishes a cache-invalidate event every ~9 minutes. With a 30s TTL, the cache mostly expired naturally before the invalidate hit, spreading misses out. With a 300s TTL, almost every cache entry was *still alive* when the invalidate hit, so the invalidate cleared all of them simultaneously across all checkout pods. Then 1,200 concurrent requests stampeded.

**14:42** — Alice and Carol agree: the new TTL would have been fine *if the cache had request coalescing* (singleflight) or *if the catalog invalidate were spread over time*. The bug was latent — the invalidate path was always a stampede risk, masked by a short TTL.

**14:55** — Alice declares the incident closed. Customer comms team prepares a public note ("brief checkout disruption 14:11–14:18 UTC, no data loss").

**Next day (postmortem)**:

- **Trigger:** Deploy of v2.317 increasing TTL from 30s to 300s.
- **Root causes (plural):**
  1. The pricing-cache invalidate path has no thundering-herd protection (singleflight, jittered TTLs).
  2. The retry client in checkout-service has no jitter and no circuit breaker, so a downstream slowdown produces a retry storm.
  3. No canary or staged rollout for `checkout-service` deploys. The TTL change went 0% → 100% in one push.
  4. No alert on `pricing-service` connection-pool saturation. The first signal was the *symptom* (checkout errors), not the *cause* (pricing overload).
- **Action items (each a ticket):**
  - [PRICING-451] Add singleflight to pricing cache origin fetches. Owner: Carol. Due: 2026-06-12.
  - [CHECKOUT-882] Add jitter (50–150%) and a circuit breaker to the pricing-service client in checkout-service. Owner: Alice. Due: 2026-06-12.
  - [INFRA-203] Implement 10%/50%/100% canary stages for checkout-service deploys. Owner: SRE team. Due: 2026-07-01.
  - [MONITORING-119] Alert on pricing-service DB connection pool > 80%. Owner: Carol. Due: 2026-06-05.
- **What went well:** alert fired in 4 minutes. Mitigation decided and executed in < 6 minutes. Bob's IC discipline kept the channel clean.
- **What went poorly:** the change was reviewed and approved without anyone modeling its interaction with the invalidate path.
- **Where we got lucky:** the incident was 7 minutes. If the invalidate had landed during peak traffic instead of mid-afternoon, p99 could have been 30s and the retry storm could have brought down `inventory-service` too.

This is what a *good* incident looks like end-to-end.

---

## A Real-ish Cache Stampede Walk-through

The diagnostic path, retold as a problem you might face.

You get paged: `checkout-service error rate elevated`. You open the dashboard. Errors are `pricing-client: context deadline exceeded`. Your investigation steps:

1. **Metric:** open the `pricing-service` p99 graph. It is 4s and climbing.
2. **Exemplar:** click on a high data point. You get a trace ID.
3. **Trace:** open the trace. 4.1s spent in `pricing-service.fetchCatalog`. Inside, 4s spent waiting on `db.acquire()`. The DB call itself is fast (10ms). It is **pool exhaustion**, not slow queries.
4. **Hypothesis:** something caused a surge of `fetchCatalog` calls.
5. **Metric:** `pricing-service.fetchCatalog` call rate. It just spiked 30× in one second, then plateaued.
6. **What changed?** Check deploys: `checkout-service` deployed 9 minutes ago. Check config events: `pricing-service` published a `catalog.invalidate` Kafka event 1 minute before the spike.
7. **Cross-reference:** the spike in `fetchCatalog` aligns to the `catalog.invalidate` event by 50ms.
8. **Refined hypothesis:** the catalog invalidate triggered a cold-cache stampede in `checkout-service`.
9. **Confirm:** look at `checkout-service` cache-miss-rate metric. Normally <1%. At the spike, 100%. Consistent.
10. **But why now?** This event happens every 9 minutes — why is it stampeding only now? Diff the recent deploy. TTL changed 30s → 300s. With short TTL, the cache was sparse at any moment, so a full-cache-clear had less impact. With long TTL, almost every key was alive and the clear hit them all.

That is the **diagnostic path**. It takes ~10 minutes if you have exemplars, distributed tracing, and per-call metrics. Without them, it would take hours of `grep` across logs and might be misdiagnosed entirely.

---

## Pros & Cons of Heavy Process

Process around incidents (ICs, postmortems, runbooks) is not free. It is worth understanding the costs.

| Pros | Cons |
|------|------|
| Faster MTTR over time | Slow at first while culture is built |
| Org learns from incidents | Postmortems take engineer-hours |
| Reduced burnout (less 3am heroics) | Some engineers will see process as bureaucracy |
| Better customer comms | Requires senior buy-in or it dies |
| Better hiring narrative | Easy to do badly (theater postmortems) |
| Risk distributed across rotation | Requires investment in tooling (status pages, IM bots) |

The trap is **process theater** — going through the motions without the cultural commitment to follow up. A postmortem that nobody reads and an action item nobody owns are both worse than not having the meeting at all, because they consume hours and produce nothing.

---

## Coding Patterns

### Pattern: structured incident context

Every log line during an incident carries the **incident ID** so you can `grep` cleanly later.

```go
logger := slog.Default().With("incident_id", "INC-2026-05-29-001")
logger.Info("rolling back checkout-service", "from", "v2.317", "to", "v2.316")
```

### Pattern: feature flag kill switch

Every risky code path is behind a flag that can be flipped in < 30s without a deploy.

```python
if flags.is_on("new_pricing_path", default=False):
    return new_pricing_path(req)
return old_pricing_path(req)
```

### Pattern: jittered retry with budget

Never retry without jitter. Never retry without an overall budget.

```rust
let base = Duration::from_millis(100);
let jitter: u64 = rand::random::<u64>() % 100;
let delay = base * (1 << attempt) + Duration::from_millis(jitter);
```

### Pattern: snapshot endpoint behind auth

```java
@GetMapping("/admin/state")
@PreAuthorize("hasRole('INTERNAL_OPS')")
public Map<String, Object> state() {
    return Map.of(
        "queueDepth", workerPool.getQueue().size(),
        "activeWorkers", workerPool.getActiveCount(),
        "config", configSnapshot()
    );
}
```

---

## Clean Code

- Every prod service has a one-screen dashboard pinned to the on-call channel.
- Every prod service has a runbook for its top 3 known failure modes.
- Every prod service has a snapshot / state endpoint behind auth.
- Every deploy is gated by canary or staged rollout.
- Every log line is structured (key=value), not stringly.
- Every request has a propagated trace ID.
- Every critical path has SLO + alert + runbook.
- Every postmortem produces ticketed action items.
- Every incident channel timeline is preserved (export the chat).
- Every IC role is **explicit** — one person, named, in the channel topic.

---

## Best Practices

1. **Mitigate before you understand.** Stop the bleeding first.
2. **Write down your hypothesis before you test it.** No moving goalposts.
3. **Always look at "what changed" first.** Deploys, config, traffic, schema.
4. **p99, not p50.** That's where the bugs live.
5. **Exemplars on every metric.** Metric → trace → log in one click.
6. **Singleflight every hot cache fill.** No stampedes.
7. **Jitter every retry.** No retry storms.
8. **Circuit-break every downstream.** No cascading failure.
9. **Stage every deploy.** No 0→100 rollouts.
10. **Postmortem every SEV.** No exceptions for "we were busy."

---

## Edge Cases & Pitfalls

- The "phantom" recurrence: an incident that mostly recurs at 02:00 UTC — turns out a cron job runs then. Always overlay scheduled events on your incident timeline.
- The "Heisenbug" on observation: adding logging *changes the timing* and the bug disappears. Be skeptical of fixes that only work when the logger is on.
- The cross-region surprise: the incident affected only `eu-west-1` and you debug in `us-east-1`. Reproduce in the affected region.
- The "intermittent" that is actually deterministic on one specific input: collect more requests before declaring randomness.
- The pre-incident incident: a smaller version of this fired last week and was dismissed. Audit the last 30 days of "false alarm" alerts after every incident.
- The wrong-customer postmortem: an incident affected one big customer and the postmortem focuses on them, missing that 200 smaller customers were also affected.

---

## Common Mistakes

1. Declaring victory after the rollback. The rollback is the *mitigation*; the bug is still there.
2. Letting the IC also write the fix. The IC stops reading channel and the incident drifts.
3. Skipping the timeline because "we were all there." Two weeks later nobody remembers.
4. Naming a person in the postmortem. The author flinches; the next bug gets hidden.
5. "Improve monitoring" as an action item. Not SMART, won't get done.
6. Five Whys turning into Five Blames. Stop the meeting and reset.
7. Treating the trigger as the root cause. "We deployed at lunch" is not a fix.
8. Letting the action items list grow without ever closing it. After 50 unclosed items, nobody believes in the process.
9. Sharing only the wins. Hide the bad postmortems and the org stops learning.
10. Conflating SEV-1 process with SEV-3 process. Both need rigor, but the same heavyweight ceremony for a small bug burns people out.

---

## Tricky Points

- A single-cause incident is usually a misdiagnosed multi-cause incident.
- "We rolled forward" can be braver than "we rolled back" — but it requires a level of confidence you usually don't have during the incident.
- Alerts have a half-life: an alert that hasn't fired in 6 months is probably broken. Audit them.
- The on-call who never gets paged is *not* the team's hero — they're a sign your alerting is missing real signal or the system is over-engineered for stability at huge cost.
- A bug that recurs in production after being "fixed" was not fixed — it was patched. Real fixes change the *condition*, not the *instance*.
- The fastest mitigation is not always the right one. Restarting the service does fix many things but teaches you nothing.

---

## Anti-Patterns at Professional Level

1. **Hero culture.** "We pulled an all-nighter and saved it!" — applauded once, expected always. The hero is a single point of failure; you replace them with a system.
2. **"Restart fixes it."** Sometimes true, always lazy. Until you understand *why*, the next restart is on a 4-hour timer.
3. **Workarounds that become permanent.** The `# TODO: remove after Q3` comment from three years ago. Track workarounds in a ticket with a real owner and a real deadline.
4. **"We'll add monitoring after we ship."** You will not. Monitoring goes in the launch checklist or it never goes in.
5. **Skipping the postmortem because "we're busy."** You will have this incident again. Pay now or pay twice.
6. **The "war room" that becomes a war.** Yelling, blame, talking over each other. The IC has authority to mute or eject.
7. **Postmortems that name a person.** "Alice deployed without canary" — wrong. "The deploy pipeline did not require canary" — right.
8. **The "we're not Google" excuse.** You don't need 100 SREs to write a one-page postmortem template.
9. **Process for process's sake.** A SEV-3 about a typo in a log message does not need a 5-person retro.
10. **The "fix" merge that's also a refactor.** During an incident, the change should be minimal and reviewable in 30 seconds.

---

## Postmortem Template

A one-page template you'd actually use:

```text
INCIDENT: <short name>
ID: INC-YYYY-MM-DD-NN
SEV: 1 | 2 | 3
DURATION: <hh:mm>–<hh:mm> UTC (NN minutes)
DETECTED BY: alert | human | customer
INCIDENT COMMANDER: <name>
SCRIBE: <name>

=== SUMMARY ===
<2-3 sentences, customer-facing. What broke, who was affected, how long.>

=== IMPACT ===
- Users affected: <count or %>
- Revenue impact: $<approx>
- Data loss: yes | no | unknown
- SLO impact: <budget consumed>

=== TIMELINE (UTC) ===
HH:MM — <event>
HH:MM — <event>
...

=== ROOT CAUSES ===
1. <systemic cause>
2. <systemic cause>
3. ...

=== TRIGGER ===
<the proximate event that started the incident>

=== WHAT WENT WELL ===
- ...

=== WHAT WENT POORLY ===
- ...

=== WHERE WE GOT LUCKY ===
- ...

=== ACTION ITEMS ===
| ID       | Description                  | Owner | Due        |
|----------|------------------------------|-------|------------|
| TICKET-1 | ...                          | @x    | YYYY-MM-DD |
| TICKET-2 | ...                          | @y    | YYYY-MM-DD |

=== LESSONS LEARNED ===
<For the org, not just this team. What pattern do we want to remember?>
```

---

## First-30-Minutes-on-an-Unknown-Service Checklist

You've been paged for a service whose name you barely recognize.

1. [ ] Open the service's dashboard. Glance at: RPS, error rate, p99, CPU, memory.
2. [ ] Read the README. One-sentence summary of what it does.
3. [ ] Find the on-call team. Page them if it's not you.
4. [ ] Open the runbook for the alert that fired. Follow it if it exists.
5. [ ] Find the deploy history. Anything in the last 24h?
6. [ ] Find the config change history. Anything in the last 24h?
7. [ ] Open the trace explorer. Pull one slow / failing request.
8. [ ] Read the entry-point code (`cmd/main` or equivalent).
9. [ ] List the service's dependencies (DBs, queues, downstreams). Check each one's dashboard.
10. [ ] Check the snapshot endpoint if available.
11. [ ] Check OS-level signals: descriptor count, memory pressure, swap, disk full.
12. [ ] Document what you've ruled out in the incident channel.
13. [ ] If still stuck at 30 min: page the service owner. No shame.

---

## Apply it

1. Define the user or business outcome that **Debugging — Professional (Staff / Principal) Level** should improve.
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

- Which measurable outcome justifies investing in Debugging — Professional (Staff / Principal) Level?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
