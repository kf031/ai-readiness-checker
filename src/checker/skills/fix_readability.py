"""fix-readability — Rewrites dense paragraphs for better readability.

When an LLM backend is provided (v3), uses the LLM to rewrite long
paragraphs into clearer, shorter sentences. Otherwise falls back to
sentence-length detection with recommendations only (v2).
"""

import re

SKILL_NAME = "fix-readability"
SKILL_DESCRIPTION = "Rewrites dense paragraphs for lower reading grade level by breaking long sentences."

_SENTENCE_PATTERN = re.compile(r"([.!?])\s+")


def execute(html: str, report: dict, backend=None) -> dict:
    readability_info = report.get("modules", {}).get("content", {}).get("readability", {})
    if readability_info.get("score", 1.0) >= 0.5:
        return {"changes": [], "modified_html": html, "target": "body"}

    if backend is not None:
        return _fix_with_llm(html, readability_info, backend)

    # v2 fallback: detection only
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


def _fix_with_llm(html: str, readability_info: dict, backend) -> dict:
    """Use LLM to rewrite dense paragraphs for better readability."""
    from bs4 import BeautifulSoup

    score = readability_info.get("score", 0.0)
    flesch = readability_info.get("flesch_reading_ease", "N/A")

    soup = BeautifulSoup(html, "lxml")
    paragraphs = soup.find_all("p")
    if not paragraphs:
        return {"changes": [], "modified_html": html, "target": "body"}

    # Collect paragraph texts (limit to 10 for context window)
    para_texts = []
    for p in paragraphs[:10]:
        text = p.get_text(strip=True)
        if len(text) > 50:
            para_texts.append(text[:500])

    if not para_texts:
        return {"changes": [], "modified_html": html, "target": "body"}

    joined = "\n\n---\n\n".join(para_texts)
    prompt = f"""Rewrite the following webpage paragraphs to improve readability.
Current Flesch Reading Ease: {flesch} (higher = easier to read, 60+ is good).

Rules:
- Break sentences longer than 25 words into 2-3 shorter sentences
- Use simpler words where possible without losing meaning
- Keep all facts and product information intact
- Preserve any pricing, dates, or technical specifications exactly
- Target a 7th-9th grade reading level

Paragraphs to rewrite:
{joined}

Return the rewritten paragraphs in the same order, separated by "---NEW_PARA---" on its own line.
Output ONLY the rewritten text, no explanations."""

    system = (
        "You are a professional editor. Rewrite text to be clearer and more readable. "
        "Preserve all factual information. Output only the requested format."
    )

    try:
        response = backend.generate(prompt, system=system)
        rewritten = [r.strip() for r in response.split("---NEW_PARA---")]

        para_count = 0
        for i, p in enumerate(paragraphs):
            if i < len(rewritten) and rewritten[i]:
                old_text = p.get_text(strip=True)
                if old_text and rewritten[i] != old_text:
                    # Replace paragraph content with rewritten text
                    for child in list(p.children):
                        child.decompose()
                    p.append(soup.new_string(rewritten[i]))
                    para_count += 1

        if para_count > 0:
            return {
                "changes": [
                    f"Rewrote {para_count} paragraph(s) for better readability "
                    f"(original Flesch score: {flesch})"
                ],
                "modified_html": str(soup),
                "target": "body",
            }
    except Exception:
        pass

    return {"changes": [], "modified_html": html, "target": "body"}
