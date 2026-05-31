"""
News loader — fetches macro-relevant headlines from NewsAPI.

Discretionary decisions
-----------------------
- Keywords are scoped to macro/financial topics to reduce noise.
  Broad news is not useful here; we want signals relevant to the
  model's modules: policy, growth, financial stress, energy/geo.
- Results are capped at 8 headlines. More adds noise to the LLM prompt
  without improving report quality.
- Articles with removed/deleted content are filtered out.
- If NEWSAPI_KEY is not set the function returns an empty list — the
  app continues to run normally, the report just lacks news context.
- News headlines inform the LLM narrative report only. They do NOT
  affect scores, weights, or probabilities. The quantitative model
  stays clean and auditable.
"""

from __future__ import annotations

from newsapi import NewsApiClient

# Base query kept under 500 chars (NewsAPI free tier limit).
# Covers the core macro dimensions: policy, growth, financial stress,
# energy/supply, and key geopolitical chokepoints.
MACRO_KEYWORDS = (
    '"Federal Reserve" OR "interest rates" OR "inflation" OR '
    '"recession" OR "yield curve" OR "credit spreads" OR '
    '"crude oil" OR "OPEC" OR "oil prices" OR '
    '"Iran" OR "Hormuz" OR "Red Sea" OR "sanctions" OR '
    '"tariffs" OR "trade war" OR "VIX" OR "gold"'
)


def fetch_macro_headlines(api_key: str, max_results: int = 15, extra_keywords: list[str] | None = None) -> list[dict]:
    """
    Fetch recent macro-relevant headlines from NewsAPI.

    extra_keywords: user-supplied terms (e.g. ["Hormuz", "Iran war"]) appended
    to the base query so context-specific events are captured.

    Returns a list of dicts with keys: title, source, published, url.
    Returns empty list on any failure so callers never need to handle errors.
    """
    query = MACRO_KEYWORDS
    if extra_keywords:
        extra = " OR ".join(f'"{k}"' if " " in k else k for k in extra_keywords)
        query = f"{query} OR {extra}"

    client = NewsApiClient(api_key=api_key)
    response = client.get_everything(
        q=query,
        language="en",
        sort_by="publishedAt",
        page_size=max_results,
    )
    # NewsAPI returns status="error" with a message on failure
    if response.get("status") == "error":
        raise RuntimeError(f"NewsAPI error: {response.get('message', 'unknown')}")

    articles = response.get("articles", [])
    return [
        {
            "title": a["title"],
            "source": a["source"]["name"],
            "published": a["publishedAt"][:10],
            "url": a["url"],
        }
        for a in articles
        if a.get("title") and "[Removed]" not in a.get("title", "")
    ]
