from data.storage.sqlite_store import init_db, save_run

if __name__ == "__main__":
    init_db()
    save_run({
        "topic": "Example run",
        "horizon": "Short",
        "report_mode": "short",
        "constraint_score": 4,
        "fragility_score": 3,
        "momentum": "Stable",
        "regime": "Stress",
        "classification": "Turbulence",
        "weights": {"policy": 0.3, "growth": 0.25, "financial": 0.2, "energy_geo": 0.15, "political": 0.1},
        "scenarios": [],
        "triggers": [],
    })
    print("Example run saved.")
