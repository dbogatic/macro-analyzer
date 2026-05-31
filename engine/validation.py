from __future__ import annotations


def validate_required_keys(data: dict, keys: list[str]) -> list[str]:
    missing = [key for key in keys if key not in data]
    return [f"Missing required key: {key}" for key in missing]
