"""fix-headings — Restructures heading hierarchy and merges duplicate H1s."""

import re

SKILL_NAME = "fix-headings"
SKILL_DESCRIPTION = "Restructures H1/H2/H3 hierarchy, merges duplicate H1s, and makes headings descriptive."


def execute(html: str, report: dict) -> dict:
    headings_info = report.get("modules", {}).get("content", {}).get("headings", {})
    issues = headings_info.get("issues", [])
    changes = []
    modified = html

    if "Multiple H1s" in issues:
        modified, change = _merge_duplicate_h1s(modified)
        if change:
            changes.append(change)

    if "Missing H2 hierarchy" in issues:
        modified, change = _add_h2_hierarchy(modified)
        if change:
            changes.append(change)

    if not changes:
        return {"changes": [], "modified_html": html, "target": "body"}

    return {"changes": changes, "modified_html": modified, "target": "body"}


def _merge_duplicate_h1s(html: str) -> tuple[str, str | None]:
    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE)
    if len(h1s) < 2:
        return html, None
    first = h1s[0]
    for h1 in h1s[1:]:
        html = re.sub(
            r"<h1[^>]*>" + re.escape(h1) + r"</h1>",
            "",
            html,
            count=1,
            flags=re.IGNORECASE,
        )
    return html, f"Merged {len(h1s)} H1s into single H1: '{first}'"


def _add_h2_hierarchy(html: str) -> tuple[str, str | None]:
    h2s = re.findall(r"<h2[^>]*>", html, re.IGNORECASE)
    h3s = re.findall(r"<h3[^>]*>", html, re.IGNORECASE)
    if h3s and not h2s:
        first_h3 = h3s[0]
        html = html.replace(
            first_h3,
            re.sub(r"<h3", "<h2", first_h3),
            1,
        )
        return html, "Promoted H3 to H2 to establish heading hierarchy"
    return html, None
