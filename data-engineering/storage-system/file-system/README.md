# File System

> The layer between "bytes I want to store" and "physical blocks on a
> disk" — a distributed file system (HDFS) extends this abstraction across
> many machines, and understanding its block/replica model explains both
> why Hadoop-era big data tooling works the way it does and why object
> storage eventually displaced it for most new systems.

```mermaid
flowchart LR
    Junior["Junior: files, blocks, and why big files get split"] --> Middle["Middle: HDFS's NameNode/DataNode architecture"]
    Middle --> Senior["Senior: the small-files problem and NameNode memory pressure"]
    Senior --> Professional["Professional: why object storage displaced HDFS for most new systems"]
```

```mermaid
flowchart LR
    File["A 1GB file"] --> Block1["Block 1 (128MB)"]
    File --> Block2["Block 2 (128MB)"]
    File --> BlockN["... Block N"]
    Block1 --> Replica1["Replica on\nDataNode A"]
    Block1 --> Replica2["Replica on\nDataNode B"]
    Block1 --> Replica3["Replica on\nDataNode C"]
```

## Choose a level

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Files, blocks, and splitting](junior.md) | You can explain why a distributed file system splits large files into fixed-size blocks. |
| Middle | [NameNode/DataNode architecture](middle.md) | You can trace a file read through HDFS's metadata and data planes. |
| Senior | [The small-files problem](senior.md) | You can explain why millions of tiny files degrade a NameNode's performance. |
| Professional | [Why object storage displaced HDFS](professional.md) | You can articulate the architectural trade-offs that led most new systems toward S3-style object storage. |

## Practice rule

Before writing a pipeline that produces many small output files, ask:
"how many files will this generate per day, and does whatever's storing
them (HDFS NameNode, or an object store) handle that volume well?" Small-
file proliferation is one of the most common, avoidable big-data
performance problems.

## Related

- [Object Storage](../object-storage/README.md)
- [B+Tree — professional](../../databases/performance/indexing/b+tree/professional.md)
