"""Deterministic, referentially consistent synthetic ERP event generator."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from random import Random
from typing import Any

COLUMNS: dict[str, tuple[str, ...]] = {
    "suppliers": ("supplier_id", "name", "country", "lead_time_days"),
    "materials": ("material_id", "sku", "description", "category", "unit_of_measure"),
    "warehouses": ("warehouse_id", "code", "name"),
    "purchase_orders": (
        "order_id", "supplier_id", "order_date", "promised_date", "status"
    ),
    "purchase_order_items": (
        "order_item_id", "order_id", "material_id", "ordered_qty", "unit_price"
    ),
    "goods_receipts": (
        "receipt_id", "order_item_id", "warehouse_id", "receipt_date", "received_qty"
    ),
    "inventory_movements": (
        "movement_id", "receipt_id", "material_id", "warehouse_id",
        "movement_date", "quantity_delta", "movement_type"
    ),
}


def build_dataset(
    *, seed: int = 42, orders: int = 100, suppliers: int = 12, materials: int = 40
) -> dict[str, list[dict[str, Any]]]:
    """Create repeatable procurement and inventory events with valid business keys."""
    if min(orders, suppliers, materials) <= 0:
        raise ValueError("orders, suppliers, and materials must be positive")

    rng = Random(seed)
    dataset: dict[str, list[dict[str, Any]]] = {name: [] for name in COLUMNS}
    for supplier_id in range(1, suppliers + 1):
        dataset["suppliers"].append({
            "supplier_id": supplier_id,
            "name": f"Supplier {supplier_id:03d}",
            "country": rng.choice(("AR", "BR", "CL", "UY")),
            "lead_time_days": rng.randint(5, 21),
        })
    for material_id in range(1, materials + 1):
        dataset["materials"].append({
            "material_id": material_id,
            "sku": f"MAT-{material_id:05d}",
            "description": f"Material {material_id:05d}",
            "category": rng.choice(("PACKAGING", "INGREDIENT", "SPARE_PART")),
            "unit_of_measure": "EA",
        })
    for warehouse_id, code in enumerate(("CBA", "ROS", "BUE"), start=1):
        dataset["warehouses"].append({
            "warehouse_id": warehouse_id, "code": code, "name": f"Warehouse {code}"
        })

    next_item, next_receipt = 1, 1
    start_date = date(2026, 1, 1)
    for order_id in range(1, orders + 1):
        supplier_id = rng.randint(1, suppliers)
        order_date = start_date + timedelta(days=rng.randint(0, 180))
        lead = int(dataset["suppliers"][supplier_id - 1]["lead_time_days"])
        promised_date = order_date + timedelta(days=lead)
        ordered_total, received_total = 0, 0
        for _ in range(rng.randint(1, 3)):
            item_id = next_item
            next_item += 1
            material_id = rng.randint(1, materials)
            ordered_qty = rng.randint(20, 300)
            ordered_total += ordered_qty
            dataset["purchase_order_items"].append({
                "order_item_id": item_id, "order_id": order_id,
                "material_id": material_id, "ordered_qty": ordered_qty,
                "unit_price": f"{rng.randint(10, 1000)}.{rng.randint(0, 99):02d}",
            })
            fulfillment = rng.choices(("NONE", "PARTIAL", "FULL"), (15, 25, 60))[0]
            received_qty = (
                0 if fulfillment == "NONE" else
                rng.randint(1, ordered_qty - 1) if fulfillment == "PARTIAL" else
                ordered_qty
            )
            received_total += received_qty
            if received_qty == 0:
                continue
            first = received_qty
            second = 0
            if received_qty >= 2 and rng.random() < 0.4:
                first = rng.randint(1, received_qty - 1)
                second = received_qty - first
            for offset, quantity in enumerate((first, second)):
                if quantity == 0:
                    continue
                warehouse_id = rng.randint(1, 3)
                receipt_date = promised_date + timedelta(days=rng.randint(-3, 12) + offset)
                if receipt_date < order_date:
                    receipt_date = order_date
                dataset["goods_receipts"].append({
                    "receipt_id": next_receipt,
                    "order_item_id": item_id,
                    "warehouse_id": warehouse_id,
                    "receipt_date": receipt_date.isoformat(),
                    "received_qty": quantity,
                })
                dataset["inventory_movements"].append({
                    "movement_id": next_receipt,
                    "receipt_id": next_receipt,
                    "material_id": material_id,
                    "warehouse_id": warehouse_id,
                    "movement_date": receipt_date.isoformat(),
                    "quantity_delta": quantity,
                    "movement_type": "RECEIPT",
                })
                next_receipt += 1
        status = (
            "OPEN" if received_total == 0 else
            "CLOSED" if received_total == ordered_total else "PARTIAL"
        )
        dataset["purchase_orders"].append({
            "order_id": order_id, "supplier_id": supplier_id,
            "order_date": order_date.isoformat(),
            "promised_date": promised_date.isoformat(), "status": status,
        })
    validate_dataset(dataset)
    return dataset


def validate_dataset(data: dict[str, list[dict[str, Any]]]) -> None:
    """Fail on missing relationships, over-receipt, or inconsistent order states."""
    suppliers = {row["supplier_id"] for row in data["suppliers"]}
    materials = {row["material_id"] for row in data["materials"]}
    warehouses = {row["warehouse_id"] for row in data["warehouses"]}
    orders = {row["order_id"]: row for row in data["purchase_orders"]}
    items = {row["order_item_id"]: row for row in data["purchase_order_items"]}
    receipts = {row["receipt_id"]: row for row in data["goods_receipts"]}
    assert all(row["supplier_id"] in suppliers for row in orders.values())
    assert all(row["order_id"] in orders for row in items.values())
    assert all(row["material_id"] in materials for row in items.values())
    assert all(row["order_item_id"] in items for row in receipts.values())
    assert all(row["warehouse_id"] in warehouses for row in receipts.values())
    quantities: dict[int, int] = defaultdict(int)
    for receipt in receipts.values():
        quantities[receipt["order_item_id"]] += receipt["received_qty"]
    ordered_per_order: dict[int, int] = defaultdict(int)
    received_per_order: dict[int, int] = defaultdict(int)
    for item in items.values():
        item_id = item["order_item_id"]
        order_id = item["order_id"]
        assert 0 <= quantities[item_id] <= item["ordered_qty"]
        ordered_per_order[order_id] += item["ordered_qty"]
        received_per_order[order_id] += quantities[item_id]
    for order_id, order in orders.items():
        received = received_per_order[order_id]
        expected = (
            "OPEN" if received == 0 else
            "CLOSED" if received == ordered_per_order[order_id] else "PARTIAL"
        )
        assert order["status"] == expected
    movements = data["inventory_movements"]
    assert len(movements) == len(receipts)
    assert len({row["receipt_id"] for row in movements}) == len(receipts)
    for movement in movements:
        receipt = receipts[movement["receipt_id"]]
        item = items[receipt["order_item_id"]]
        assert movement["material_id"] == item["material_id"]
        assert movement["warehouse_id"] == receipt["warehouse_id"]
        assert movement["quantity_delta"] == receipt["received_qty"]
        assert movement["movement_date"] == receipt["receipt_date"]


def write_dataset(
    data: dict[str, list[dict[str, Any]]], output: Path, seed: int
) -> dict[str, Any]:
    """Write stable CSV files plus a manifest with counts and schema version."""
    output.mkdir(parents=True, exist_ok=True)
    for name, columns in COLUMNS.items():
        with (output / f"{name}.csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(data[name])
    manifest = {
        "schema_version": "0.1.0", "seed": seed,
        "record_counts": {name: len(rows) for name, rows in data.items()},
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest
