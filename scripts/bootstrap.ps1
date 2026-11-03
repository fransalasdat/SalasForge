# Execute from repository root in Windows PowerShell.
$ErrorActionPreference = 'Stop'

uv sync --locked --all-extras --python 3.12
uv run --no-sync salasforge generate --seed 42 --orders 100 --output data/generated
uv run --no-sync pytest -q -m 'not integration'
uv run --no-sync ruff check .

docker compose up -d postgres
Write-Host 'PostgreSQL startup requested. Check health before loading:'
docker compose ps
Write-Host 'Then run:'
Write-Host 'uv run --no-sync salasforge load --input data/generated --dsn postgresql://salasforge:salasforge_local_only@localhost:5433/salasforge'
