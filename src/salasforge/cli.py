"""Minimal command-line interface; intentionally not tied to a cloud account."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from salasforge.generator import build_dataset, write_dataset


def main() -> None:
    parser = argparse.ArgumentParser(prog="salasforge")
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser("generate", help="Generate consistent synthetic ERP CSVs")
    generate.add_argument("--seed", type=int, default=42)
    generate.add_argument("--orders", type=int, default=100)
    generate.add_argument("--suppliers", type=int, default=12)
    generate.add_argument("--materials", type=int, default=40)
    generate.add_argument("--output", type=Path, default=Path("data/generated"))
    load = commands.add_parser("load", help="Upsert generated CSVs into PostgreSQL")
    load.add_argument("--input", type=Path, default=Path("data/generated"))
    load.add_argument("--dsn", default=None, help="Overrides DATABASE_URL")
    args = parser.parse_args()
    if args.command == "generate":
        dataset = build_dataset(
            seed=args.seed, orders=args.orders,
            suppliers=args.suppliers, materials=args.materials
        )
        result = write_dataset(dataset, args.output, args.seed)
    else:
        from salasforge.loader import load_csvs

        dsn = args.dsn or os.environ.get("DATABASE_URL")
        if not dsn:
            parser.error("Provide --dsn or DATABASE_URL (see .env.example)")
        result = load_csvs(args.input, dsn)
    print(json.dumps(result, indent=2, sort_keys=True))
