# Indexing

> Covers B+Tree, Bloom Filter, LSM Tree, and Skip List.

## Topics

| Topic | What it covers |
|---|---|
| [B+Tree](b+tree/) | The default index structure behind almost every relational database. A balanced tree tuned for disk: shallow (few levels), wide nodes (fits… |
| [Bloom Filter](bloom-filter/) | A probabilistic structure that answers "have I possibly seen this before?" using a fraction of the memory a real set would need — trading a… |
| [LSM Tree](lsm-tree/) | Never modify data in place — always append. Writes become sequential and fast; reads pay the cost of checking multiple sorted files,… |
| [Skip List](skip-list/) | A sorted linked list with extra "express lane" pointers layered on top, giving O(log n) search without the rebalancing complexity of a… |
