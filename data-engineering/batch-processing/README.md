# Schedule Jobs

> Covers Airflow, Durable Execution Temporal, Retries and Idempotency, Returning Results, and Schedule Driven.

## Topics

| Topic | What it covers |
|---|---|
| [Airflow](airflow/) | A Python-based workflow orchestrator: define pipelines as directed acyclic graphs (DAGs) of tasks, and let a scheduler, executor, and… |
| [Durable Execution Temporal](durable-execution-temporal/) | Write a long-running, multi-step workflow as plain code — loops, conditionals, sleeps spanning days — and have the platform guarantee it… |
| [Retries and Idempotency](retries-and-idempotency/) | A failed job usually deserves another try — but retrying blindly can turn one failure into a cascading pile-on, and re-running a job that… |
| [Returning Results](returning-results/) | A background job, by definition, doesn't return a value the way a normal function call does — the caller has already moved on. Getting the… |
| [Schedule Driven](schedule-driven/) | Run work at a fixed point in time or interval, regardless of whether anything "happened" to trigger it. Cron jobs, nightly batch pipelines,… |
