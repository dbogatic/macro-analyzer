from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
DB_PATH = ROOT_DIR / "macro_runs.db"
APP_TITLE = "Macro Analyzer"
DEFAULT_REPORT_MODE = "short"

@dataclass(frozen=True)
class Settings:
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    fred_api_key: str | None = os.getenv("FRED_API_KEY")
    newsapi_key: str | None = os.getenv("NEWSAPI_KEY")
    db_path: str = str(DB_PATH)

settings = Settings()
