"""Core deterministic generation and business invariants."""

from __future__ import annotations

import json
from pathlib import Path

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
