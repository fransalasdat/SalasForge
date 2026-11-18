"""Core deterministic generation and business invariants."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

from salasforge.generator import build_dataset, validate_dataset, write_dataset


def test_deterministic_generation() -> None:
    first = build_dataset(seed=42, orders=25)
    second = build_dataset(seed=42, orders=25)
    assert first == second
    assert first != build_dataset(seed=43, orders=25)


def test_referential_integrity_and_business_rules() -> None:
    dataset = build_dataset(seed=100, orders=400)
    validate_dataset(dataset)
    assert len(dataset["purchase_orders"]) == 400
    assert len(dataset["goods_receipts"]) == len(dataset["inventory_movements"])
    assert {row["status"] for row in dataset["purchase_orders"]} <= {
        "OPEN", "PARTIAL", "CLOSED"
    }


@pytest.mark.parametrize("kwargs", [
    {"orders": 0}, {"suppliers": -1}, {"materials": 0}
])
def test_invalid_counts(kwargs: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        build_dataset(**kwargs)


def test_export_is_reproducible(tmp_path: Path) -> None:
    dataset = build_dataset(seed=8, orders=12)
    left, right = tmp_path / "left", tmp_path / "right"
    write_dataset(dataset, left, seed=8)
    write_dataset(dataset, right, seed=8)
    assert sorted(path.name for path in left.iterdir()) == sorted(
        path.name for path in right.iterdir()
    )
    for path in left.iterdir():
        assert path.read_bytes() == (right / path.name).read_bytes()
    manifest = json.loads((left / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["record_counts"]["purchase_orders"] == 12


@pytest.mark.parametrize(("table", "key", "field", "target"), [
    ("purchase_orders", "order_id", "supplier_id", "suppliers"),
    ("purchase_order_items", "order_item_id", "order_id", "purchase_orders"),
    ("purchase_order_items", "order_item_id", "material_id", "materials"),
    ("goods_receipts", "receipt_id", "order_item_id", "purchase_order_items"),
    ("goods_receipts", "receipt_id", "warehouse_id", "warehouses"),
    ("inventory_movements", "movement_id", "receipt_id", "goods_receipts"),
])
def test_validation_rejects_missing_references(
    table: str, key: str, field: str, target: str
) -> None:
    dataset = build_dataset(seed=42, orders=25)
    row = dataset[table][0]
    row[field] = -1

    with pytest.raises(ValueError) as exc_info:
        validate_dataset(dataset)

    message = str(exc_info.value)
    assert f"{table}: {key}={row[key]}" in message
    assert f"{field}=-1 does not exist in {target}" in message


@pytest.mark.parametrize("invalid_total", ["negative", "over_received"])
def test_validation_rejects_invalid_receipt_totals(invalid_total: str) -> None:
    dataset = build_dataset(seed=42, orders=25)
    receipt = dataset["goods_receipts"][0]
    item = next(
        row for row in dataset["purchase_order_items"]
        if row["order_item_id"] == receipt["order_item_id"]
    )
    item_receipts = [
        row for row in dataset["goods_receipts"]
        if row["order_item_id"] == item["order_item_id"]
    ]
    other_total = sum(row["received_qty"] for row in item_receipts if row is not receipt)
    expected_total = -1 if invalid_total == "negative" else item["ordered_qty"] + 1
    receipt["received_qty"] = expected_total - other_total

    with pytest.raises(ValueError) as exc_info:
        validate_dataset(dataset)

    message = str(exc_info.value)
    assert f"purchase_order_items: order_item_id={item['order_item_id']}" in message
    assert f"received_qty_total={expected_total}" in message
    assert f"expected between 0 and ordered_qty={item['ordered_qty']}" in message


@pytest.mark.parametrize("expected_status", ["OPEN", "PARTIAL", "CLOSED"])
def test_validation_rejects_inconsistent_order_status(expected_status: str) -> None:
    dataset = build_dataset(seed=100, orders=400)
    order = next(row for row in dataset["purchase_orders"] if row["status"] == expected_status)
    order["status"] = "CLOSED" if expected_status == "OPEN" else "OPEN"

    with pytest.raises(ValueError) as exc_info:
        validate_dataset(dataset)

    message = str(exc_info.value)
    assert f"purchase_orders: order_id={order['order_id']}, status={order['status']}" in message
    assert f"expected={expected_status}" in message


@pytest.mark.parametrize("count_change", [-1, 1])
def test_validation_rejects_incorrect_movement_count(count_change: int) -> None:
    dataset = build_dataset(seed=42, orders=25)
    movements = dataset["inventory_movements"]
    if count_change == -1:
        movements.pop()
    else:
        movements.append(movements[0].copy())

    with pytest.raises(ValueError) as exc_info:
        validate_dataset(dataset)

    message = str(exc_info.value)
    assert f"inventory_movements: count={len(movements)}" in message
    assert f"expected one movement per receipt, count={len(dataset['goods_receipts'])}" in message


def test_validation_rejects_duplicate_movement_receipt() -> None:
    dataset = build_dataset(seed=42, orders=25)
    first, second = dataset["inventory_movements"][:2]
    second["receipt_id"] = first["receipt_id"]

    with pytest.raises(ValueError) as exc_info:
        validate_dataset(dataset)

    message = str(exc_info.value)
    assert f"inventory_movements: movement_id={second['movement_id']}" in message
    assert f"receipt_id={first['receipt_id']}" in message
    assert "duplicate receipt reference" in message


@pytest.mark.parametrize(("field", "invalid_value"), [
    ("material_id", -1),
    ("warehouse_id", -1),
    ("quantity_delta", -1),
    ("movement_date", "1900-01-01"),
])
def test_validation_rejects_inconsistent_movement(field: str, invalid_value: int | str) -> None:
    dataset = build_dataset(seed=42, orders=25)
    movement = dataset["inventory_movements"][0]
    expected_value = movement[field]
    movement[field] = invalid_value

    with pytest.raises(ValueError) as exc_info:
        validate_dataset(dataset)

    message = str(exc_info.value)
    assert f"inventory_movements: movement_id={movement['movement_id']}" in message
    assert f"receipt_id={movement['receipt_id']}" in message
    assert f"{field}={invalid_value}; expected={expected_value}" in message


def test_validation_remains_active_with_optimized_python() -> None:
    script = dedent("""\
        from salasforge.generator import build_dataset, validate_dataset

        dataset = build_dataset(seed=42, orders=25)
        order = dataset["purchase_orders"][0]
        expected = order["status"]
        order["status"] = "CLOSED" if expected == "OPEN" else "OPEN"
        try:
            validate_dataset(dataset)
        except ValueError as exc:
            message = str(exc)
            if (
                "purchase_orders: order_id=1" not in message
                or f"expected={expected}" not in message
            ):
                raise SystemExit(f"Unexpected validation message: {message}")
        else:
            raise SystemExit("Invalid dataset was accepted with optimized Python")
    """)
    result = subprocess.run(
        [sys.executable, "-O", "-c", script], capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stdout + result.stderr
