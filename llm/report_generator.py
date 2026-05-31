from __future__ import annotations

from openai import OpenAI

from config.settings import settings
from llm.prompt_builder import build_prompt


def generate_report(payload: dict, mode: str = "short", headlines: list[dict] | None = None) -> str:
    if not settings.openai_api_key:
        return (
            "OpenAI report generation is disabled because OPENAI_API_KEY is not set.\n\n"
            "The analysis pipeline still ran. Add your API key to the .env file to enable short/long narrative reports."
        )

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model="gpt-4o-mini",
        input=build_prompt(payload, mode=mode, headlines=headlines),
    )
    return response.output_text
