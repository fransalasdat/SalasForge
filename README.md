# SalasForge

**An End-to-End Enterprise Data Engineering Platform**

SalasForge is a portfolio-grade, local-first data engineering platform focused on a simulated enterprise supply chain: procurement, suppliers, partial goods receipts, warehouses and inventory events.

> **Status: M0 — Foundation.** This release provides a deterministic ERP data generator, relational PostgreSQL schema, transactional bootstrap loader, unit tests, local Docker configuration and CI. Streaming, dbt, Dagster, object storage, BigQuery and observability are planned, **not yet implemented**.

## Quick start

Requirements: Python 3.12+, and optionally Docker Compose for PostgreSQL.

~~~bash
python -m pip install -e '.[dev,postgres]'
python -m salasforge generate --seed 42 --orders 100 --output data/generated
pytest -q
ruff check .
~~~

Start PostgreSQL locally:

~~~bash
docker compose up -d postgres
python -m salasforge load --input data/generated --dsn postgresql://salasforge:salasforge_local_only@localhost:5433/salasforge
~~~

Alternatively use **uv**:

~~~bash
uv sync --extra dev --extra postgres
uv run salasforge generate --orders 100
uv run pytest -q
~~~

The generator writes seven CSV files and a schema-versioned manifest. The same seed and arguments yield byte-for-byte identical output. The loader uses transactional upserts: replaying an identical dataset does not duplicate rows.

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

Business invariants: referenced entities exist; total receipts never exceed ordered quantities; purchase-order status reflects receipt totals; each receipt is reconciled to an inventory movement. The current scope covers receipts only, not transfers or consumption.

## Documentation

- [Architecture](docs/architecture.md)
- [Roadmap](docs/roadmap.md)
- [ADR 0001: Local-first architecture](docs/adr/0001-local-first.md)

## Development

GitHub Actions checks Python 3.12/3.13 on pull requests and pushes. No CI job provisions or deploys cloud infrastructure.

**Costs and security:** Local operation needs no paid cloud account. The sample credentials are intentionally loopback-only development defaults; never expose PostgreSQL publicly or commit credentials. Optional cloud integration is planned for future milestones.

## License

MIT. See [LICENSE](LICENSE).
