"""Read-only dashboard queries for immutable forecast records.

A model/version, target and explicit outcome source/version are required for
accuracy metrics. Unmatched forecasts remain visible in coverage statistics.
"""
from __future__ import annotations

from contextlib import contextmanager
import sqlite3
from pathlib import Path
from typing import Iterator


@contextmanager
def _connect(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(str(db_path))
    try:
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA query_only = ON")
        yield con
    finally:
        con.close()


def list_targets(db_path: str | Path) -> list[str]:
    with _connect(db_path) as con:
        return [
            row["target_name"] for row in con.execute(
                "SELECT DISTINCT target_name FROM forecast_records ORDER BY target_name"
            )
        ]


def list_models(db_path: str | Path, target_name: str) -> list[tuple[str, str]]:
    with _connect(db_path) as con:
        return [
            (row["model_name"], row["model_version"])
            for row in con.execute(
                """SELECT DISTINCT model_name, model_version
                   FROM forecast_records WHERE target_name = ?
                   ORDER BY model_name, model_version""",
                (target_name,),
            )
        ]


def list_outcome_revisions(
    db_path: str | Path, target_name: str,
    model_name: str, model_version: str,
) -> list[tuple[str, str]]:
    with _connect(db_path) as con:
        return [
            (row["source_name"], row["source_version"])
            for row in con.execute(
                """SELECT DISTINCT o.source_name, o.source_version
                   FROM forecast_outcomes o
                   JOIN forecast_records f ON f.forecast_id = o.forecast_id
                   WHERE f.target_name = ? AND f.model_name = ? AND f.model_version = ?
                   ORDER BY o.source_name, o.source_version""",
                (target_name, model_name, model_version),
            )
        ]


def list_forecast_history(
    db_path: str | Path, target_name: str, model_name: str,
    model_version: str, *, source_name: str | None = None,
    source_version: str | None = None,
) -> list[dict]:
    """One row per issued forecast; unmatched outcomes remain NULL.

    A partial source/revision selection is forbidden to avoid ambiguous
    versions. No forecast rows are dropped in this coverage view.
    """
    if (source_name is None) != (source_version is None):
        raise ValueError("Outcome source and revision must be selected together")
    with _connect(db_path) as con:
        if source_name is None:
            sql = """SELECT f.forecast_id, f.issued_at_utc, f.model_name,
                       f.model_version, f.target_name, f.kind, f.prediction,
                       f.lower, f.upper, f.window_start, f.window_end,
                       NULL AS outcome, NULL AS recorded_at_utc
                     FROM forecast_records f
                     WHERE f.target_name = ? AND f.model_name = ?
                       AND f.model_version = ?
                     ORDER BY f.issued_at_utc, f.forecast_id"""
            parameters = (target_name, model_name, model_version)
        else:
            sql = """SELECT f.forecast_id, f.issued_at_utc, f.model_name,
                       f.model_version, f.target_name, f.kind, f.prediction,
                       f.lower, f.upper, f.window_start, f.window_end,
                       o.outcome, o.recorded_at_utc
                     FROM forecast_records f
                     LEFT JOIN forecast_outcomes o ON o.forecast_id = f.forecast_id
                       AND o.source_name = ? AND o.source_version = ?
                     WHERE f.target_name = ? AND f.model_name = ?
                       AND f.model_version = ?
                     ORDER BY f.issued_at_utc, f.forecast_id"""
            parameters = (source_name, source_version, target_name, model_name, model_version)
        return [dict(row) for row in con.execute(sql, parameters)]
