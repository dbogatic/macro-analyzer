CREATE_RUNS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    topic TEXT NOT NULL,
    horizon TEXT,
    report_mode TEXT,
    constraint_score REAL,
    fragility_score REAL,
    momentum TEXT,
    regime TEXT,
    classification TEXT,
    weights TEXT NOT NULL,
    scenarios TEXT NOT NULL,
    triggers TEXT NOT NULL,
    raw_payload TEXT NOT NULL
)
"""
