"""Persistent PostgreSQL forecast registry for Streamlit Community Cloud.

Mirrors the SQLite ForecastRegistry contract. Records are append-only;
outcome corrections require a new source_version. Connection credentials
are supplied by a secret, never checked into Git.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from data.storage.forecast_registry import Forecast, _metadata, _number, _utc


SCHEMA = """
CREATE TABLE IF NOT EXISTS forecast_records (
    forecast_id TEXT PRIMARY KEY,
    issued_at_utc TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    target_name TEXT NOT NULL,
    target_definition TEXT NOT NULL,
    window_start DATE NOT NULL,
    window_end DATE NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('binary', 'continuous')),
    prediction DOUBLE PRECISION NOT NULL,
    lower DOUBLE PRECISION,
    upper DOUBLE PRECISION,
    features_json TEXT NOT NULL,
    source_manifest_json TEXT NOT NULL,
    CHECK(window_start <= window_end),
    CHECK(kind <> 'binary' OR prediction BETWEEN 0 AND 1),
    CHECK (
        (lower IS NULL AND upper IS NULL) OR
        (lower IS NOT NULL AND upper IS NOT NULL AND lower <= upper)
    )
);
CREATE TABLE IF NOT EXISTS forecast_outcomes (
    outcome_id TEXT PRIMARY KEY,
    forecast_id TEXT NOT NULL REFERENCES forecast_records(forecast_id),
    recorded_at_utc TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_version TEXT NOT NULL,
    outcome DOUBLE PRECISION NOT NULL,
    UNIQUE(forecast_id, source_name, source_version)
);
CREATE INDEX IF NOT EXISTS ix_forecast_target
    ON forecast_records(target_name, window_end);
CREATE INDEX IF NOT EXISTS ix_outcome_forecast
    ON forecast_outcomes(forecast_id);
CREATE OR REPLACE FUNCTION block_forecast_mutation()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'forecast audit records are immutable';
END;
$$;
DROP TRIGGER IF EXISTS block_forecast_update ON forecast_records;
CREATE TRIGGER block_forecast_update
    BEFORE UPDATE OR DELETE ON forecast_records
    FOR EACH ROW EXECUTE FUNCTION block_forecast_mutation();
DROP TRIGGER IF EXISTS block_outcome_update ON forecast_outcomes;
CREATE TRIGGER block_outcome_update
    BEFORE UPDATE OR DELETE ON forecast_outcomes
    FOR EACH ROW EXECUTE FUNCTION block_forecast_mutation();
"""


class PostgresForecastRegistry:
    def __init__(self, dsn: str):
        if not dsn.startswith(("postgresql://", "postgres://")):
            raise ValueError("Expected a PostgreSQL connection URL")
        self.dsn = dsn
        self.initialize()

    def _connect(self):
        return psycopg.connect(
            self.dsn, row_factory=dict_row, connect_timeout=10,
        )

    def initialize(self) -> None:
        """Idempotent DDL; never deletes stored forecasts or outcomes."""
        with self._connect() as con:
            con.execute(SCHEMA)

    def record_forecast(self, forecast: Forecast) -> None:
        if not forecast.forecast_id.strip():
            raise ValueError("Forecast ID is required")
        if not all(item.strip() for item in (
            forecast.model_name, forecast.model_version,
            forecast.target_name, forecast.target_definition,
        )):
            raise ValueError("Model and target definition are required")
        issued = _utc(forecast.issued_at)
        if not isinstance(forecast.window_start, date) or not isinstance(forecast.window_end, date):
            raise TypeError("Forecast target window must use dates")
        if forecast.window_start > forecast.window_end:
            raise ValueError("Forecast target window is reversed")
        if forecast.issued_at.astimezone(timezone.utc).date() > forecast.window_start:
            raise ValueError("Forecast issued after target window began")
        if forecast.kind not in ("binary", "continuous"):
            raise ValueError("Unsupported forecast kind")
        prediction = _number(forecast.prediction)
        if forecast.kind == "binary" and not 0 <= prediction <= 1:
            raise ValueError("Binary probability must be between 0 and 1")
        if (forecast.lower is None) != (forecast.upper is None):
            raise ValueError("Both interval bounds are required")
        lo = None if forecast.lower is None else _number(forecast.lower)
        hi = None if forecast.upper is None else _number(forecast.upper)
        if lo is not None and not lo <= prediction <= hi:
            raise ValueError("Prediction must lie within bounds")
        if forecast.kind == "binary" and lo is not None and not 0 <= lo <= hi <= 1:
            raise ValueError("Binary probability bounds must lie within [0, 1]")
        with self._connect() as con:
            con.execute("""
                INSERT INTO forecast_records (
                    forecast_id, issued_at_utc, model_name, model_version,
                    target_name, target_definition, window_start, window_end,
                    kind, prediction, lower, upper, features_json,
                    source_manifest_json
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, (
                forecast.forecast_id, issued, forecast.model_name,
                forecast.model_version, forecast.target_name,
                forecast.target_definition, forecast.window_start,
                forecast.window_end, forecast.kind, prediction, lo, hi,
                _metadata(forecast.features), _metadata(forecast.source_manifest),
            ))

    def record_outcome(
        self, forecast_id: str, outcome: float, *, recorded_at: datetime,
        source_name: str, source_version: str, outcome_id: str | None = None,
    ) -> str:
        timestamp = _utc(recorded_at)
        value = _number(outcome)
        if not source_name.strip() or not source_version.strip():
            raise ValueError("Outcome source and version are required")
        with self._connect() as con:
            row = con.execute(
                "SELECT kind, window_end FROM forecast_records WHERE forecast_id = %s",
                (forecast_id,),
            ).fetchone()
            if row is None:
                raise LookupError("Unknown forecast ID")
            if recorded_at.astimezone(timezone.utc).date() <= row["window_end"]:
                raise ValueError("Target window has not ended")
            if row["kind"] == "binary" and value not in (0.0, 1.0):
                raise ValueError("Binary outcome must be 0 or 1")
            oid = outcome_id or str(uuid4())
            con.execute("""
                INSERT INTO forecast_outcomes (
                    outcome_id, forecast_id, recorded_at_utc,
                    source_name, source_version, outcome
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (oid, forecast_id, timestamp, source_name, source_version, value))
        return oid

    def target_counts(self, target_name: str) -> dict[str, int]:
        with self._connect() as con:
            row = con.execute("""
                SELECT COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE EXISTS (
                        SELECT 1 FROM forecast_outcomes o
                        WHERE o.forecast_id = f.forecast_id
                    )) AS completed
                FROM forecast_records f WHERE target_name = %s
            """, (target_name,)).fetchone()
        return {
            "total_forecasts": int(row["total"]),
            "with_any_outcome": int(row["completed"]),
        }

    def scored_rows(
        self, *, target_name: str, source_name: str, source_version: str,
    ) -> list[dict]:
        with self._connect() as con:
            return con.execute("""
                SELECT f.forecast_id, f.model_name, f.model_version, f.kind,
                    f.issued_at_utc, f.window_end, f.prediction, f.lower, f.upper,
                    o.outcome, o.source_name, o.source_version
                FROM forecast_records f
                JOIN forecast_outcomes o ON f.forecast_id = o.forecast_id
                WHERE f.target_name = %s AND o.source_name = %s
                    AND o.source_version = %s
                ORDER BY f.issued_at_utc, f.forecast_id
            """, (target_name, source_name, source_version)).fetchall()
