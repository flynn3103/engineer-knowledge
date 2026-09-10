# Storage System

> Covers File Format, File System, KV Store, Object Storage, Query Engine, Spark, and Table Format.

## Topics

| Topic | What it covers |
|---|---|
| [File Format](file-format/) | How bytes are physically laid out inside a file — row-major vs. column-major, schema embedding, compression — determines whether reading… |
| [File System](file-system/) | The layer between "bytes I want to store" and "physical blocks on a disk" — a distributed file system (HDFS) extends this abstraction… |
| [KV Store](kv-store/) | The simplest possible data model — get/put/delete by key — is also the foundation almost every other storage system in this tree is built… |
| [Object Storage](object-storage/) | Flat, key-value storage for arbitrarily large blobs — no directories, no in-place edits, no POSIX semantics. S3 (and its many equivalents)… |
| [Query Engine](query-engine/) | A distributed SQL engine (Trino, Presto, Dremio) that queries data directly where it lives — Parquet files on object storage, table formats… |
| [Spark](spark/) | A distributed compute engine built around one core abstraction — transformations on partitioned data, lazily planned and executed as a DAG… |
| [Table Format](table-format/) | Covers Delta Lake, Hudi, and Iceberge. |
