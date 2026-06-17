"""fix-qa — Adds Q&A sections when Q&A density score is low."""

import re

SKILL_NAME = "fix-qa"
SKILL_DESCRIPTION = "Adds Q&A sections derived from existing content where Q&A density is low."


def execute(html: str, report: dict) -> dict:
    qa_info = report.get("modules", {}).get("content", {}).get("qa_density", {})
    if qa_info.get("score", 1.0) >= 0.5:
        return {"changes": [], "modified_html": html, "target": "body"}

    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE)
    h2s = re.findall(r"<h2[^>]*>(.*?)</h2>", html, re.IGNORECASE)
    p_texts = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)

    title = h1s[0] if h1s else "This Page"
    topics = [t.strip() for t in h2s[:3]] if h2s else ["the content"]
    if not topics and p_texts:
        topics = [p_texts[0][:60] + "..."]
    if not topics:
        return {"changes": [], "modified_html": html, "target": "body"}

    qa_html_parts = []
    for topic in topics:
        qa_html_parts.append(
            f'<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">\n'
            f'  <h3 itemprop="name">What should I know about {topic}?</h3>\n'
            f'  <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">\n'
            f'    <p itemprop="text">[Expand based on existing content about {topic}]</p>\n'
            f'  </div>\n'
            f'</div>'
        )

    qa_section = (
        f'\n<section>\n<h2>Frequently Asked Questions about {title}</h2>\n'
        + "\n".join(qa_html_parts)
        + "\n</section>\n"
    )

    body_close = "</body>"
    modified = html.replace(body_close, f"\n{qa_section}\n{body_close}", 1)

    return {
        "changes": [f"Added Q&A section with {len(topics)} question(s) based on page topics: {', '.join(topics)}"],
        "modified_html": modified,
        "target": "body",
    }
