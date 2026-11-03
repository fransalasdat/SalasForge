# Execute from repository root in Windows PowerShell.
$ErrorActionPreference = 'Stop'
python -m pip install -e '.[dev,postgres]'
python -m salasforge generate --seed 42 --orders 100 --output data/generated
pytest -q
docker compose up -d postgres
Write-Host 'Database startup requested. Check health before loading:'
Write-Host 'docker compose ps'
Write-Host 'python -m salasforge load --dsn postgresql://salasforge:salasforge_local_only@localhost:5433/salasforge'
