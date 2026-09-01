# OLTP vs OLAP — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Given a query, can you tell whether it belongs on an OLTP system or an
> OLAP system?

---

## Two very different jobs

| | OLTP (Online Transaction Processing) | OLAP (Online Analytical Processing) |
|---|---|---|
| **Typical query** | "Get order #4521." "Update this customer's address." | "Total revenue by region, last 12 months." |
| **Rows touched per query** | A handful | Millions to billions |
| **Query volume** | Thousands to millions per second | A handful to a few hundred per second |
| **Read/write mix** | Roughly balanced, lots of writes | Almost entirely reads |
| **Example systems** | Postgres, MySQL, the app's production database | Snowflake, BigQuery, Redshift, ClickHouse |
| **Who runs the queries** | The application, on behalf of users | Analysts, dashboards, ML training jobs |

```mermaid
flowchart LR
    App[User clicks "buy"] --> OLTP["OLTP query:\nUPDATE inventory WHERE sku=X"]
    Analyst[Analyst opens dashboard] --> OLAP["OLAP query:\nSUM(revenue) GROUP BY region, month"]
```

## Why you can't just use one system for both

An OLTP system is tuned for **many small, fast, concurrent transactions** —
indexes on primary keys, row-level locking, small working sets that fit in
memory. Point it at "sum this column across a billion rows" and it will scan
far more data than it's built to scan quickly, competing for the same
resources (buffer cache, I/O, locks) that live application traffic depends
on.

An OLAP system is tuned for **scanning huge amounts of data efficiently** —
but it's often not optimized for "find and update exactly this one row
transactionally, right now, with sub-millisecond latency and strict
consistency," which is what a checkout flow needs.

> 🎓 **Takeaway:** OLTP and OLAP aren't "the same database, one just has more
> data." They're built with different physical layouts and trade-offs for
> fundamentally different query shapes. The rest of this topic is about *why*
> that's true and what to do about it.

## Test yourself

1. Classify each: "insert a new order," "average order value by month,"
   "check if a coupon code is valid," "top 10 products by revenue this
   quarter."
2. Why would running the "top 10 products by revenue this quarter" query
   directly against the production checkout database worry a senior engineer?
3. Name one system you interact with daily where you can tell, from how it
   behaves, that you're looking at an OLAP-backed view versus an OLTP-backed
   one.

Continue to [`middle.md`](middle.md).
