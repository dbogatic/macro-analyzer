"""Read-only PostgreSQL forecast dashboard queries; explicit outcome vintages."""
from __future__ import annotations

import psycopg
from psycopg.rows import dict_row


def _connect(dsn: str):
    return psycopg.connect(dsn, row_factory=dict_row, connect_timeout=10)


def list_targets(dsn: str) -> list[str]:
    with _connect(dsn) as con:
        return [row["target_name"] for row in con.execute(
            "SELECT DISTINCT target_name FROM forecast_records ORDER BY target_name"
        ).fetchall()]


def list_models(dsn: str, target_name: str) -> list[tuple[str, str]]:
    with _connect(dsn) as con:
        return [
            (row["model_name"], row["model_version"])
            for row in con.execute("""
                SELECT DISTINCT model_name, model_version FROM forecast_records
                WHERE target_name = %s ORDER BY model_name, model_version
            """, (target_name,)).fetchall()
        ]


def list_outcome_revisions(
    dsn: str, target_name: str, model_name: str, model_version: str,
) -> list[tuple[str, str]]:
    with _connect(dsn) as con:
        return [
            (row["source_name"], row["source_version"])
            for row in con.execute("""
                SELECT DISTINCT o.source_name, o.source_version
                FROM forecast_outcomes o JOIN forecast_records f
                  ON o.forecast_id = f.forecast_id
                WHERE f.target_name = %s AND f.model_name = %s
                  AND f.model_version = %s
                ORDER BY o.source_name, o.source_version
            """, (target_name, model_name, model_version)).fetchall()
        ]


def list_forecast_history(
    dsn: str, target_name: str, model_name: str, model_version: str,
    *, source_name: str | None = None, source_version: str | None = None,
) -> list[dict]:
    if (source_name is None) != (source_version is None):
        raise ValueError("Outcome source and revision must be selected together")
    if source_name is None:
        query = """
            SELECT f.forecast_id, f.issued_at_utc, f.model_name, f.model_version,
                f.target_name, f.kind, f.prediction, f.lower, f.upper,
                f.window_start, f.window_end,
                NULL AS outcome, NULL AS recorded_at_utc
            FROM forecast_records f
            WHERE f.target_name = %s AND f.model_name = %s
              AND f.model_version = %s
            ORDER BY f.issued_at_utc, f.forecast_id
        """
        params = (target_name, model_name, model_version)
    else:
        query = """
            SELECT f.forecast_id, f.issued_at_utc, f.model_name, f.model_version,
                f.target_name, f.kind, f.prediction, f.lower, f.upper,
                f.window_start, f.window_end, o.outcome, o.recorded_at_utc
            FROM forecast_records f
            LEFT JOIN forecast_outcomes o ON o.forecast_id = f.forecast_id
                AND o.source_name = %s AND o.source_version = %s
            WHERE f.target_name = %s AND f.model_name = %s
                AND f.model_version = %s
            ORDER BY f.issued_at_utc, f.forecast_id
        """
        params = (source_name, source_version, target_name, model_name, model_version)
    with _connect(dsn) as con:
        return con.execute(query, params).fetchall()
