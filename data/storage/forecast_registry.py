"""Append-only SQLite forecast registry, independent of the legacy runs DB.

All predictions are immutable. Realized outcomes are appended with explicit
source revisions; a correction creates a new outcome row, never a rewrite.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
from typing import Any
from uuid import uuid4


def _utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamps must include a timezone")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds")


def _number(value: float) -> float:
    if isinstance(value, bool):
        raise ValueError("Expected a finite number")
    try:
        val = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError("Expected a finite number") from exc
    if not math.isfinite(val):
        raise ValueError("Expected a finite number")
    return val


def _metadata(value: dict[str, Any]) -> str:
    if not isinstance(value, dict):
        raise ValueError("Metadata must be a dictionary")
    return json.dumps(value, sort_keys=True, allow_nan=False)


@dataclass(frozen=True)
class Forecast:
    forecast_id: str
    issued_at: datetime
    model_name: str
    model_version: str
    target_name: str
    target_definition: str
    window_start: date
    window_end: date
    kind: str
    prediction: float
    features: dict[str, Any]
    source_manifest: dict[str, Any]
    lower: float | None = None
    upper: float | None = None


class ForecastRegistry:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self._connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS forecast_records (
                    forecast_id TEXT PRIMARY KEY,
                    issued_at_utc TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    target_definition TEXT NOT NULL,
                    window_start TEXT NOT NULL,
                    window_end TEXT NOT NULL,
                    kind TEXT NOT NULL CHECK(kind IN ('binary', 'continuous')),
                    prediction REAL NOT NULL,
                    lower REAL,
                    upper REAL,
                    features_json TEXT NOT NULL,
                    source_manifest_json TEXT NOT NULL,
                    CHECK(window_start <= window_end),
                    CHECK(kind != 'binary' OR prediction BETWEEN 0 AND 1),
                    CHECK((lower IS NULL AND upper IS NULL) OR
                          (lower IS NOT NULL AND upper IS NOT NULL AND lower <= upper))
                );
                CREATE TABLE IF NOT EXISTS forecast_outcomes (
                    outcome_id TEXT PRIMARY KEY,
                    forecast_id TEXT NOT NULL REFERENCES forecast_records(forecast_id),
                    recorded_at_utc TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    source_version TEXT NOT NULL,
                    outcome REAL NOT NULL,
                    UNIQUE(forecast_id, source_name, source_version)
                );
                CREATE TRIGGER IF NOT EXISTS block_forecast_update
                BEFORE UPDATE ON forecast_records BEGIN
                    SELECT RAISE(ABORT, 'forecasts are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS block_forecast_delete
                BEFORE DELETE ON forecast_records BEGIN
                    SELECT RAISE(ABORT, 'forecasts are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS block_outcome_update
                BEFORE UPDATE ON forecast_outcomes BEGIN
                    SELECT RAISE(ABORT, 'outcomes are immutable');
                END;
                CREATE TRIGGER IF NOT EXISTS block_outcome_delete
                BEFORE DELETE ON forecast_outcomes BEGIN
                    SELECT RAISE(ABORT, 'outcomes are immutable');
                END;
                CREATE INDEX IF NOT EXISTS ix_forecast_target
                    ON forecast_records(target_name, window_end);
                CREATE INDEX IF NOT EXISTS ix_outcome_forecast
                    ON forecast_outcomes(forecast_id);
            """)

    def record_forecast(self, forecast: Forecast) -> None:
        if not forecast.forecast_id.strip():
            raise ValueError("Forecast ID is required")
        if not all(value.strip() for value in (
            forecast.model_name, forecast.model_version,
            forecast.target_name, forecast.target_definition,
        )):
            raise ValueError("Model identification and target definition required")
        issued = _utc(forecast.issued_at)
        if not isinstance(forecast.window_start, date) or not isinstance(forecast.window_end, date):
            raise TypeError("Target window must contain dates")
        if forecast.window_start > forecast.window_end:
            raise ValueError("Target window is reversed")
        if forecast.issued_at.astimezone(timezone.utc).date() > forecast.window_start:
            raise ValueError("Forecast issued after target window began")
        if forecast.kind not in ("binary", "continuous"):
            raise ValueError("Unsupported forecast kind")
        prediction = _number(forecast.prediction)
        if forecast.kind == "binary" and not 0 <= prediction <= 1:
            raise ValueError("Binary probability must be between 0 and 1")
        if (forecast.lower is None) != (forecast.upper is None):
            raise ValueError("Both interval bounds are required")
        lower = None if forecast.lower is None else _number(forecast.lower)
        upper = None if forecast.upper is None else _number(forecast.upper)
        if lower is not None and not lower <= prediction <= upper:
            raise ValueError("Prediction must lie within bounds")
        if forecast.kind == "binary" and lower is not None and not 0 <= lower <= upper <= 1:
            raise ValueError("Probability bounds must lie within [0, 1]")
        with self._connect() as con:
            con.execute("""
                INSERT INTO forecast_records (
                    forecast_id, issued_at_utc, model_name, model_version,
                    target_name, target_definition, window_start, window_end,
                    kind, prediction, lower, upper, features_json, source_manifest_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                forecast.forecast_id, issued, forecast.model_name,
                forecast.model_version, forecast.target_name,
                forecast.target_definition, forecast.window_start.isoformat(),
                forecast.window_end.isoformat(), forecast.kind, prediction,
                lower, upper, _metadata(forecast.features),
                _metadata(forecast.source_manifest),
            ))

    def record_outcome(
        self, forecast_id: str, outcome: float, *, recorded_at: datetime,
        source_name: str, source_version: str, outcome_id: str | None = None,
    ) -> str:
        recorded = _utc(recorded_at)
        value = _number(outcome)
        if not source_name.strip() or not source_version.strip():
            raise ValueError("Outcome source and version are required")
        with self._connect() as con:
            forecast = con.execute(
                "SELECT * FROM forecast_records WHERE forecast_id = ?", (forecast_id,)
            ).fetchone()
            if forecast is None:
                raise LookupError("Unknown forecast ID")
            if recorded_at.astimezone(timezone.utc).date() <= date.fromisoformat(forecast["window_end"]):
                raise ValueError("Target window has not ended")
            if forecast["kind"] == "binary" and value not in (0.0, 1.0):
                raise ValueError("Binary outcome must be 0 or 1")
            oid = outcome_id or str(uuid4())
            con.execute("""
                INSERT INTO forecast_outcomes (
                    outcome_id, forecast_id, recorded_at_utc, source_name,
                    source_version, outcome
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (oid, forecast_id, recorded, source_name, source_version, value))
        return oid

    def scored_rows(
        self, *, target_name: str, source_name: str, source_version: str,
    ) -> list[sqlite3.Row]:
        """Require an explicitly chosen outcome vintage to avoid revision mixing."""
        with self._connect() as con:
            return con.execute("""
                SELECT f.forecast_id, f.model_name, f.model_version, f.kind,
                       f.issued_at_utc, f.window_end, f.prediction, f.lower,
                       f.upper, o.outcome, o.source_name, o.source_version
                FROM forecast_records f
                JOIN forecast_outcomes o ON o.forecast_id = f.forecast_id
                WHERE f.target_name = ? AND o.source_name = ? AND o.source_version = ?
                ORDER BY f.issued_at_utc, f.forecast_id
            """, (target_name, source_name, source_version)).fetchall()

    def target_counts(self, target_name: str) -> dict[str, int]:
        with self._connect() as con:
            row = con.execute("""
                SELECT COUNT(*) AS total,
                    SUM(CASE WHEN EXISTS (
                        SELECT 1 FROM forecast_outcomes o
                        WHERE o.forecast_id = f.forecast_id
                    ) THEN 1 ELSE 0 END) AS completed
                FROM forecast_records f WHERE f.target_name = ?
            """, (target_name,)).fetchone()
        return {
            "total_forecasts": int(row["total"] or 0),
            "with_any_outcome": int(row["completed"] or 0),
        }
