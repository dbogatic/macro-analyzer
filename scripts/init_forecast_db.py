"""Initialize the separate Macro Analyzer 2.0 SQLite forecast database.

Usage (from repository root):
    python scripts/init_forecast_db.py
    python scripts/init_forecast_db.py --db /persistent/path/macro_forecasts.db

Safe to repeat; creates tables if absent and never deletes historical rows.
This does not modify macro_runs.db or create example predictions.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.storage.forecast_registry import ForecastRegistry


def initialize(db_path: Path) -> dict[str, int]:
    destination = db_path.expanduser().resolve()
    if not destination.parent.is_dir():
        raise FileNotFoundError(f"Missing database directory: {destination.parent}")
    ForecastRegistry(destination)
    with sqlite3.connect(destination) as connection:
        tables = {row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )}
        expected = {"forecast_records", "forecast_outcomes"}
        if not expected.issubset(tables):
            raise RuntimeError("Forecast database schema not initialized")
        if connection.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Forecast database foreign-key integrity failure")
        return {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in sorted(expected)
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=ROOT / "macro_forecasts.db")
    args = parser.parse_args()
    counts = initialize(args.db)
    print(f"SQLite forecast database: {args.db.expanduser().resolve()}")
    for name, count in counts.items():
        print(f"{name}: {count} records")


if __name__ == "__main__":
    main()
