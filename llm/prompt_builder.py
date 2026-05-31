from __future__ import annotations

import json

from config.prompts import LONG_PROMPT, SHORT_PROMPT


def build_prompt(payload: dict, mode: str = "short", headlines: list[dict] | None = None) -> str:
    template = SHORT_PROMPT if mode == "short" else LONG_PROMPT
    if headlines:
        news_context = "\n".join(
            f"- [{h['source']}] {h['title']} ({h['published']})"
            for h in headlines
        )
    else:
        news_context = "No current news context available."
    return template.format(
        payload=json.dumps(payload, indent=2, default=str),
        news_context=news_context,
    )
