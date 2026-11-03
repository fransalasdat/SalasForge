"""PostgreSQL integration contract: schema, replay safety, and atomic rollback.

Runs only with SALASFORGE_TEST_DSN pointing to an isolated *_test database.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from salasforge.generator import COLUMNS, build_dataset, write_dataset
from salasforge.loader import load_csvs

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def test_dsn() -> str:
    dsn = os.getenv("SALASFORGE_TEST_DSN")
    if not dsn:
        pytest.skip("Set SALASFORGE_TEST_DSN to a disposable PostgreSQL *_test database")
    psycopg = pytest.importorskip("psycopg")
    schema_path = Path(__file__).resolve().parents[1] / "infra/postgres/001_init.sql"
    with psycopg.connect(dsn) as connection:
        if not connection.info.dbname.endswith("_test"):
            pytest.fail("Integration tests refuse to modify a database without a *_test name")
        # This fixture is allowed to reset only a dedicated test database.
        connection.execute(
            "DROP TABLE IF EXISTS inventory_movements, goods_receipts, "
            "purchase_order_items, purchase_orders, warehouses, materials, "
            "suppliers CASCADE"
        )
        connection.execute(schema_path.read_text(encoding="utf-8"))
    return dsn


def test_bootstrap_replay_and_transactional_rollback(
    test_dsn: str, tmp_path: Path
) -> None:
    import psycopg

    dataset = build_dataset(seed=42, orders=30)
    write_dataset(dataset, tmp_path, seed=42)

    counts = load_csvs(tmp_path, test_dsn)
    assert counts == {name: len(rows) for name, rows in dataset.items()}

    with psycopg.connect(test_dsn) as connection:
        for table, expected in counts.items():
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT count(*) FROM {table}")  # known static table names
                assert cursor.fetchone()[0] == expected

    # Replaying the same input must not create additional rows.
    assert load_csvs(tmp_path, test_dsn) == counts

    with psycopg.connect(test_dsn) as connection:
        for table, expected in counts.items():
            with connection.cursor() as cursor:
                cursor.execute(f"SELECT count(*) FROM {table}")
                assert cursor.fetchone()[0] == expected

    # Force an earlier UPSERT followed by a later invalid CSV header.
    supplier_path = tmp_path / "suppliers.csv"
    supplier_path.write_text(
        supplier_path.read_text(encoding="utf-8").replace(
            "Supplier 001", "SHOULD_NOT_COMMIT"
        ),
        encoding="utf-8",
    )
    items_path = tmp_path / "purchase_order_items.csv"
    items_path.write_text(
        items_path.read_text(encoding="utf-8").replace(
            "order_item_id", "invalid_column", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Unexpected CSV schema"):
        load_csvs(tmp_path, test_dsn)

    with psycopg.connect(test_dsn) as connection:
        row = connection.execute(
            "SELECT name FROM suppliers WHERE supplier_id = 1"
        ).fetchone()
        assert row is not None and row[0] == "Supplier 001"
