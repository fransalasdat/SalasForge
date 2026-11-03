# SalasForge

**An End-to-End Enterprise Data Engineering Platform**

SalasForge is a portfolio-grade, local-first data engineering platform focused on a simulated enterprise supply chain: procurement, suppliers, partial goods receipts, warehouses and inventory events.

> **Status: M0 — Foundation.** Implemented: deterministic ERP generator, normalized PostgreSQL schema, transactional bootstrap loader, versioned uv dependencies, unit/integration tests and GitHub Actions CI. Streaming, dbt, Dagster, object storage, BigQuery and observability remain **planned**, not implemented.

## Quick start (Windows PowerShell or other shell)

Prerequisites: [uv](https://docs.astral.sh/uv/getting-started/installation/), and Docker Compose only if running PostgreSQL locally. The pinned dependencies are tracked in `uv.lock`.

~~~sh
uv sync --locked --all-extras --python 3.12
uv run --no-sync salasforge generate --seed 42 --orders 100 --output data/generated
uv run --no-sync pytest -q -m "not integration"
uv run --no-sync ruff check .
~~~

Start PostgreSQL locally, check readiness, then load CSVs:

~~~sh
docker compose up -d postgres
docker compose ps
uv run --no-sync salasforge load --input data/generated --dsn postgresql://salasforge:salasforge_local_only@localhost:5433/salasforge
~~~

The loader is **idempotent for identical input** and wraps the load in a database transaction. It does not yet handle general incremental/CDC logic.

The generator writes seven CSV files and a schema-versioned manifest, all ignored by Git. The same seed and arguments produce byte-for-byte identical files.

## Data domain

| Source table | Grain |
|---|---|
| suppliers | One record per supplier |
| materials | One record per material |
| warehouses | One record per warehouse |
| purchase_orders | One record per purchase order |
| purchase_order_items | One record per purchase order line |
| goods_receipts | One record per receipt |
| inventory_movements | One receipt-linked inventory movement |

Business invariants: referenced entities exist, total receipts never exceed ordered quantities, purchase-order status reflects receipt totals, and receipts reconcile to inventory movements. Current scope covers receipts only, not transfers or consumption.

## Automated validation

CI has three jobs: Python 3.12 unit/lint/smoke, Python 3.13 unit/lint/smoke, and PostgreSQL 16 integration. The PostgreSQL suite uses a **disposable `salasforge_test` database** to verify initial load, safe identical replay and transaction rollback on invalid input.

Run integration tests yourself only against a disposable database with a name ending in `_test`; the fixture resets application tables. The regular `salasforge` development database is *not* suitable for the test suite.

## Documentation

- [Development and local setup](docs/development.md)
- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [ADR 0001: Local-first architecture](docs/adr/0001-local-first.md)

No CI job provisions or deploys cloud infrastructure. Local operation does not require a paid cloud account. Default PostgreSQL credentials are **loopback-only development defaults**; do not expose the service publicly or use these credentials in a deployed environment.

## License

MIT. See [LICENSE](LICENSE).
