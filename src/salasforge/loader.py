"""Transactional, idempotent PostgreSQL bootstrap for generated CSV datasets."""

from __future__ import annotations

import csv
from pathlib import Path

from salasforge.generator import COLUMNS


def load_csvs(directory: Path, dsn: str) -> dict[str, int]:
    """Upsert all files in FK order in one transaction; reruns do not duplicate rows.

    This bootstrap loader is not CDC. Incremental ingest is planned for M1.
    """
    try:
        import psycopg
        from psycopg import sql
    except ImportError as exc:
        raise RuntimeError("Install PostgreSQL support: pip install -e '.[postgres]'") from exc

    counts: dict[str, int] = {}
    with psycopg.connect(dsn) as conn, conn.transaction():
        with conn.cursor() as cur:
            for table, columns in COLUMNS.items():
                with (directory / f"{table}.csv").open(newline="", encoding="utf-8") as file:
                    reader = csv.DictReader(file)
                    if tuple(reader.fieldnames or ()) != columns:
                        raise ValueError(f"Unexpected CSV schema for {table}")
                    rows = [tuple(row[column] for column in columns) for row in reader]
                quoted_columns = sql.SQL(", ").join(map(sql.Identifier, columns))
                placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
                assignments = sql.SQL(", ").join(
                    sql.SQL("{} = EXCLUDED.{}").format(sql.Identifier(c), sql.Identifier(c))
                    for c in columns[1:]
                )
                statement = sql.SQL(
                    "INSERT INTO {} ({}) VALUES ({}) ON CONFLICT ({}) DO UPDATE SET {}"
                ).format(
                    sql.Identifier(table), quoted_columns, placeholders,
                    sql.Identifier(columns[0]), assignments,
                )
                cur.executemany(statement, rows)
                counts[table] = len(rows)
    return counts
