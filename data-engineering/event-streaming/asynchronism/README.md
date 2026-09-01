# Asynchronism

> Covers Back Pressure, Dead Letter Queues, Delivery Guarantees, Kafka, Message Queues, NATS, Rabbitmq, and Task Queues.

## Topics

| Topic | What it covers |
|---|---|
| [Back Pressure](back-pressure/) | When a consumer can't keep up with a producer, something has to give — back-pressure is the umbrella term for mechanisms that explicitly… |
| [Dead Letter Queues](dead-letter-queues/) | A dedicated holding area for messages that repeatedly fail processing — instead of blocking the main queue forever or silently dropping… |
| [Delivery Guarantees](delivery-guarantees/) | Every messaging system makes a specific promise about what happens to a message under failure: at-most-once, at-least-once, or the… |
| [Kafka](kafka/) | A distributed, append-only, partitioned commit log — not a traditional message queue at all. Consumers track their own read position… |
| [Message Queues](message-queues/) | Decouple a producer from a consumer with a durable buffer in between — the producer doesn't wait for the consumer to be ready, and the… |
| [NATS](nats/) | A famously simple, lightweight, high-performance messaging system — Core NATS is fire-and-forget pub/sub with no persistence at all;… |
| [Rabbitmq](rabbitmq/) | A mature, general-purpose AMQP message broker with flexible routing (exchanges and bindings) — the go-to choice when you need sophisticated… |
| [Task Queues](task-queues/) | A message queue specialized for one purpose: distributing units of executable work (not just data) across a pool of workers — with built-in… |
