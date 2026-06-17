"""fix-headings — Restructures heading hierarchy and makes headings descriptive.

When an LLM backend is provided (v3), uses the LLM to rewrite headings
contextually based on page content. Otherwise falls back to regex-based
H1 merge and H3→H2 promotion (v2).
"""

import re

SKILL_NAME = "fix-headings"
SKILL_DESCRIPTION = "Restructures H1/H2/H3 hierarchy, eliminates duplicate H1s, and makes headings descriptive."


def execute(html: str, report: dict, backend=None) -> dict:
    headings_info = report.get("modules", {}).get("content", {}).get("headings", {})
    issues = headings_info.get("issues", [])
    if not issues:
        return {"changes": [], "modified_html": html, "target": "body"}

    if backend is not None:
        return _fix_with_llm(html, issues, backend)

    # v2 fallback: regex-based fixes
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


def _fix_with_llm(html: str, issues: list[str], backend) -> dict:
    """Use an LLM to rewrite headings intelligently."""
    issues_str = ", ".join(issues)

    # Extract headings for context
    headings = re.findall(r"<(h[1-3])[^>]*>(.*?)</\1>", html, re.IGNORECASE | re.DOTALL)
    heading_summary = "\n".join(f"  <{tag}>{text.strip()}</{tag}>" for tag, text in headings)

    prompt = f"""Fix the heading structure of this HTML page. Issues found: {issues_str}.

Current headings:
{heading_summary}

Rules:
- Exactly ONE <h1> — it should be the single most important title for the page
- If there are multiple H1s, merge their ideas into ONE clear descriptive H1
- H2s should come before H3s — never skip levels (no H3 without an H2 first)
- Every heading should be descriptive (>3 meaningful words, no generic labels)
- Use the actual page content/topic for heading text, not placeholders

Return the COMPLETE HTML with corrected headings. Change ONLY the heading elements — do not modify anything else (preserve all <p>, <div>, <a>, etc exactly as-is).

Output the full corrected HTML between <FIXED> and </FIXED> tags."""

    system = (
        "You are an SEO and content structure expert. "
        "Fix heading hierarchy issues in HTML. "
        "Output ONLY the corrected HTML between <FIXED></FIXED> tags. "
        "Preserve all non-heading elements exactly."
    )

    try:
        response = backend.generate(prompt, system=system)
        fixed = _extract_fixed_html(response, html)
        if fixed != html:
            return {
                "changes": [f"Rewrote headings using AI to fix: {issues_str}"],
                "modified_html": fixed,
                "target": "body",
            }
    except Exception:
        pass

    return {"changes": [], "modified_html": html, "target": "body"}


def _extract_fixed_html(response: str, fallback: str) -> str:
    """Extract HTML between <FIXED> tags from LLM response."""
    m = re.search(r"<FIXED>(.*?)</FIXED>", response, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return fallback


# ---- v2 fallback implementations ----

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
