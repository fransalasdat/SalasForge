.PHONY: install test lint generate up down
install:
	python -m pip install -e '.[dev,postgres]'
test:
	pytest -q
lint:
	ruff check .
generate:
	python -m salasforge generate --seed 42 --orders 100 --output data/generated
up:
	docker compose up -d postgres
down:
	docker compose down
