from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from config.settings import settings
from data.storage.schema import CREATE_RUNS_TABLE_SQL


def _connect() -> sqlite3.Connection:
    db_path = Path(settings.db_path)
    return sqlite3.connect(db_path)


def init_db() -> None:
    with _connect() as conn:
        conn.execute(CREATE_RUNS_TABLE_SQL)
        conn.commit()


def save_run(run: dict[str, Any]) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO runs (
                timestamp, topic, horizon, report_mode,
                constraint_score, fragility_score, momentum,
                regime, classification, weights, scenarios,
                triggers, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                run.get("topic", "Untitled"),
                run.get("horizon"),
                run.get("report_mode"),
                run.get("constraint_score"),
                run.get("fragility_score"),
                run.get("momentum"),
                run.get("regime"),
                run.get("classification"),
                json.dumps(run.get("weights", {})),
                json.dumps(run.get("scenarios", [])),
                json.dumps(run.get("triggers", [])),
                json.dumps(run),
            ),
        )
        conn.commit()


def clear_runs() -> int:
    """Delete all saved runs. Returns number of rows deleted."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM runs")
        conn.commit()
        return cursor.rowcount


def load_runs(limit: int = 50) -> list[sqlite3.Row]:
    with _connect() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return rows
