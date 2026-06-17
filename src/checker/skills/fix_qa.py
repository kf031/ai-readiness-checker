"""fix-qa — Adds Q&A sections when Q&A density score is low.

When an LLM backend is provided (v3), uses the LLM to generate real Q&A
content from the page's actual text. Otherwise falls back to template-based
placeholder Q&A sections (v2).
"""

import re

SKILL_NAME = "fix-qa"
SKILL_DESCRIPTION = "Adds Q&A sections derived from existing content where Q&A density is low."


def execute(html: str, report: dict, backend=None) -> dict:
    qa_info = report.get("modules", {}).get("content", {}).get("qa_density", {})
    if qa_info.get("score", 1.0) >= 0.5:
        return {"changes": [], "modified_html": html, "target": "body"}

    if backend is not None:
        return _fix_with_llm(html, qa_info, backend)

    # v2 fallback: template-based Q&A
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


def _fix_with_llm(html: str, qa_info: dict, backend) -> dict:
    """Use LLM to generate real Q&A content from the page's actual content."""
    from bs4 import BeautifulSoup

    # Extract page context
    soup = BeautifulSoup(html, "lxml")

    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else ""

    h1_tag = soup.find("h1")
    h1_text = h1_tag.get_text(strip=True) if h1_tag else ""

    # Get body text for context (limit to 3000 chars)
    body = soup.find("body")
    body_text = body.get_text(separator=" ", strip=True)[:3000] if body else ""

    prompt = f"""Based on this webpage content, generate 3-5 FAQ Q&A pairs that real users would ask.

Page title: {page_title}
Page heading: {h1_text}

Page content:
{body_text}

Rules:
- Questions should be things real customers/users would actually ask
- Answers should use facts from the page content (not made up)
- Answers should be 1-3 sentences each
- Include questions about: what the product/service is, pricing/cost, how to get started, common concerns

Return the Q&A pairs as HTML with schema.org markup. Use this exact format for each Q&A:

<div itemscope itemprop="mainEntity" itemtype="https://schema.org/Question">
  <h3 itemprop="name">[question text here]</h3>
  <div itemscope itemprop="acceptedAnswer" itemtype="https://schema.org/Answer">
    <p itemprop="text">[answer text here]</p>
  </div>
</div>

Output ONLY the Q&A HTML blocks, nothing else."""

    system = (
        "You are a content strategist who writes helpful FAQ sections. "
        "Use only facts from the provided content. Generate real, useful questions. "
        "Output only the requested HTML format, no explanations."
    )

    try:
        response = backend.generate(prompt, system=system)
        # Extract just the Q&A div blocks
        qa_blocks = re.findall(
            r'<div itemscope[^>]*>.*?</div>\s*</div>',
            response, re.DOTALL | re.IGNORECASE
        )
        if not qa_blocks:
            # Try looser match — grab everything that looks like Q&A HTML
            qa_html = response.strip()
            if '<div itemscope' in qa_html:
                qa_blocks = [qa_html]

        if qa_blocks:
            qa_section = (
                '\n<section>\n<h2>Frequently Asked Questions</h2>\n'
                + "\n".join(qa_blocks)
                + "\n</section>\n"
            )

            modified = html.replace("</body>", f"\n{qa_section}\n</body>", 1)

            itemprop_pattern = 'itemprop="name"'
            qa_count = len(re.findall(itemprop_pattern, qa_section))

            return {
                "changes": [
                    f"Added AI-generated Q&A section with "
                    f"{qa_count} "
                    f"questions based on page content"
                ],
                "modified_html": modified,
                "target": "body",
            }
    except Exception:
        pass

    return {"changes": [], "modified_html": html, "target": "body"}
