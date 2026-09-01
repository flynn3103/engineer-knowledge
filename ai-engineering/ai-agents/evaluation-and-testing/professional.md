# Evaluation and Testing - Professional

An evaluation platform is a measurement system. Its datasets, graders,
sampling, statistics, and lineage require the same controls as experimental
infrastructure; otherwise it produces precise-looking misinformation.

## Real-system mechanics

**Ragas** implements reference-free and reference-based RAG metrics using
model and embedding components. Scores depend on segmentation, judge model,
prompt, and evidence supplied, so version the complete metric configuration.

**DeepEval** provides test-case abstractions and LLM-based metrics, including
multi-turn and tool-use evaluations. Treat metric thresholds as application
policy and calibrate them against human labels rather than accepting defaults.

**LangSmith** stores traces, datasets, experiments, and feedback. Its trace
linkage helps move from a failed final answer to the responsible retrieval,
model, or tool step; retention and redaction still require product policy.

**OpenTelemetry** supplies vendor-neutral trace context and span semantics.
Using run/case IDs as span attributes enables joining evaluation results to
runtime stages without making raw prompt content a metric label.

## Statistical design

For binary pass rates, report confidence intervals such as Wilson intervals,
not only point estimates. Predeclare a non-inferiority margin and minimum
sample size. For paired outcomes, analyze per-case differences or use tests
appropriate to paired binary data. Correct or control interpretation when
examining many slices.

Repeatedly checking a canary and stopping when it looks good inflates false
positives. Use a fixed horizon or a valid sequential-testing design. Separate
statistical significance from practical importance and safety constraints.

## Scale and operations

At 10x, model judges often dominate evaluation cost; cache only when all
inputs and grader versions match. At 100x, prioritize deterministic checks,
stratified samples, and disagreement review. Apply concurrency limits so eval
traffic cannot starve production provider quotas.

Dashboard dataset coverage/age, case and grader versions, pass rates with
intervals, slice regressions, flaky-case rate, judge-human agreement, review
backlog, cost, and end-to-end latency. Runbooks distinguish candidate defects
from fixture, judge, provider, and pipeline failures.

## Design and operations checklist

- [ ] Every score is reproducible from dataset, runner, model, and grader versions.
- [ ] Critical invariants use deterministic checks where possible.
- [ ] Judge metrics are calibrated and monitored against blinded human labels.
- [ ] Release comparisons use predeclared margins, slices, and sample plans.
- [ ] Evaluation traffic has independent quotas and privacy controls.
- [ ] Production failures feed a reviewed dataset process, not an unchecked dump.

## Cheat sheet

```text
unit test      = deterministic software property
behavioral eval= sampled quality property
grader         = measurement instrument requiring calibration
slice          = subgroup where aggregate quality may hide failure
release gate   = predeclared decision rule, not post-hoc interpretation
```

## Test yourself

1. Why is a 92% pass rate incomplete without sample size and interval?
2. Design a calibration study for a groundedness judge.
3. How would you scale nightly evaluations without consuming production quotas?

## Further reading

- Ragas, DeepEval, and LangSmith documentation and source repositories
- OpenTelemetry tracing specification
- Wilson, "Probable Inference, the Law of Succession, and Statistical Inference"
- Demsar, "Statistical Comparisons of Classifiers over Multiple Data Sets"
- NIST, "AI Risk Management Framework"
