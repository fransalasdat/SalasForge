# Local development

## 1. Verify prerequisites

Run in PowerShell from the SalasForge repository root:

~~~powershell
uv --version
docker compose version
~~~

Docker is only needed for PostgreSQL. The generator and Python unit tests work without Docker.

## 2. Python environment with uv

~~~powershell
uv python install 3.12
uv sync --locked --all-extras --python 3.12
uv run --no-sync python -c "import sys; print(sys.executable)"
~~~

- `pyproject.toml` declares project metadata, build requirements, runtime and optional dependencies.
- `uv.lock` records exact resolved dependencies; commit this file.
- `.venv/` is created locally; it contains the isolated Python environment and is **not committed**.
- `--locked` refuses to update an out-of-date lockfile; this ensures CI and developer environments resolve consistently.
- `--all-extras` includes the PostgreSQL and development dependencies.

Use VS Code **Python: Select Interpreter** to select `.venv/Scripts/python.exe`.

## 3. Generate deterministic data

~~~powershell
uv run --no-sync salasforge generate --seed 42 --orders 100 --output data/generated
Get-Content data/generated/manifest.json
Import-Csv data/generated/purchase_orders.csv | Group-Object status
~~~

The command dispatches to `salasforge.cli:main` (configured under `[project.scripts]`), which invokes `build_dataset()`, `validate_dataset()`, and `write_dataset()`. Seven CSV files plus `manifest.json` are generated. These are synthetic procurement data, not company or personal records.

## 4. Start PostgreSQL with Docker Compose

~~~powershell
docker compose up -d postgres
docker compose ps
~~~

Compose binds PostgreSQL only to `127.0.0.1:5433` on your computer and persists data in the named Docker volume `postgres_data`. On a new volume, PostgreSQL executes `infra/postgres/001_init.sql` automatically to create the tables.

**Important:** PostgreSQL initialization scripts run only when the data directory is first created. If you change the SQL schema after a volume already exists, the script does not rerun automatically. Do not delete a volume containing data you want to preserve.

## 5. Load, inspect and replay

~~~powershell
uv run --no-sync salasforge load --input data/generated --dsn postgresql://salasforge:salasforge_local_only@localhost:5433/salasforge

docker compose exec postgres psql -U salasforge -d salasforge -c "SELECT status, COUNT(*) FROM purchase_orders GROUP BY status ORDER BY status;"
docker compose exec postgres psql -U salasforge -d salasforge -c "SELECT COUNT(*) AS receipts FROM goods_receipts;"
~~~

Repeat the `salasforge load` command using the same CSV files. Counts should remain unchanged because the loader uses primary-key upserts in a transaction. This is an initial bootstrap demonstration, **not** an incremental extraction engine.

## 6. Unit tests and CI

~~~powershell
uv run --no-sync pytest -q -m "not integration"
uv run --no-sync ruff check .
~~~

GitHub Actions additionally runs the database integration suite against an ephemeral PostgreSQL 16 service using `SALASFORGE_TEST_DSN`. That suite verifies load consistency, exact replay, and rollback after invalid input. The fixture resets tables, so **never point `SALASFORGE_TEST_DSN` at a normal development or production database.** It refuses database names not ending in `_test`.

## 7. Common issues

| Symptom | Check |
|---|---|
| `uv` not recognized | Reopen PowerShell after installing uv |
| Python environment missing | Run `uv sync --locked --all-extras --python 3.12` |
| Connection refused | Run `docker compose ps`; check PostgreSQL health and port 5433 |
| Missing tables | Check whether the named Docker volume was created before SQL initialization was added |
| `psycopg` missing | Ensure `--all-extras` was included during sync |
| Lock mismatch | Review dependency changes to `pyproject.toml`; run `uv lock` intentionally and commit the diff |

## Next milestone

Implement incremental batch ingestion from PostgreSQL into a raw storage layer, with watermarks, ingestion metadata, replay safety, and reconciliation.
