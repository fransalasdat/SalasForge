# Architecture

## Implemented: M0 — reproducible transactional source

~~~mermaid
flowchart LR
  A[Deterministic Python ERP simulator] --> B[CSV and manifest]
  B --> C[Transactional PostgreSQL loader]
  C --> D[(PostgreSQL source)]
~~~

Implemented: synthetic procurement events; deterministic CSV export; business-integrity validation; transactional upserts into normalized PostgreSQL; Docker Compose and Python CI.

## Target (not implemented)

~~~mermaid
flowchart LR
  S[(PostgreSQL ERP)] --> I[Batch ingestion or CDC]
  I --> R[Raw object storage]
  R --> W[Warehouse staging]
  W --> M[dbt analytical marts]
  M --> C[BI consumers]
  O[Dagster] -.-> I
  O -.-> W
  Q[Quality and observability] -.-> M
~~~

Local-first, cloud optional. See ADR-0001 and roadmap. No cloud infrastructure is provisioned by the current version.
