# Roadmap

- [x] **M0 — Foundation:** data model, deterministic simulator, CSV manifest, normalized PostgreSQL schema, bootstrap loader, tests, initial CI, architecture ADR.
- [ ] **M1 — Batch ingestion:** raw immutable Parquet, watermarks, audit tables, retries, resumable idempotent incremental extracts, reconciliation tests.
- [ ] **M2 — Analytics warehouse:** dbt staging/marts, dimensions and facts, incremental models, SCD Type 2, quality contracts, optional BigQuery.
- [ ] **M3 — Orchestration:** Dagster assets, schedules, partitioned backfills, run metadata, OpenTelemetry metrics, alerts and recovery runbooks.
- [ ] **M4 — CDC and resilience:** Debezium/Kafka, schema evolution, event order, duplicate handling, failure injection, benchmarks, Terraform and CI/CD.

These milestones describe a plan, not implemented features.
