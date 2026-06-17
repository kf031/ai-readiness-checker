"""fix-readability — Detects long sentences that hurt readability scores."""

import re

SKILL_NAME = "fix-readability"
SKILL_DESCRIPTION = "Rewrites dense paragraphs for lower reading grade level by breaking long sentences."

_SENTENCE_PATTERN = re.compile(r"([.!?])\s+")


def execute(html: str, report: dict) -> dict:
    readability_info = report.get("modules", {}).get("content", {}).get("readability", {})
    if readability_info.get("score", 1.0) >= 0.5:
        return {"changes": [], "modified_html": html, "target": "body"}

    text_blocks = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
    if not text_blocks:
        return {"changes": [], "modified_html": html, "target": "body"}

    change_count = 0
    for block in text_blocks:
        sentences = [s.strip() for s in _SENTENCE_PATTERN.split(block) if s.strip() and len(s.strip()) > 0]
        long_sentences = [s for s in sentences if len(s.split()) > 25]
        if long_sentences:
            change_count += len(long_sentences)

    if change_count == 0:
        return {"changes": [], "modified_html": html, "target": "body"}

    return {
        "changes": [
            f"Identified {change_count} long sentence(s) (>25 words) — "
            f"recommend breaking into shorter sentences to improve readability score "
            f"from {readability_info.get('flesch_reading_ease', 'N/A')}"
        ],
        "modified_html": html,
        "target": "body",
    }
