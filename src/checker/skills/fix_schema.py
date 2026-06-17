"""fix-schema — Generates missing JSON-LD structured data blocks.

When an LLM backend is provided (v3), uses the LLM to generate
context-aware JSON-LD blocks based on actual page content.
Otherwise falls back to template-based generation (v2).
"""

SKILL_NAME = "fix-schema"
SKILL_DESCRIPTION = "Generates missing JSON-LD structured data blocks for schema types flagged as absent in the report."


def execute(html: str, report: dict, backend=None) -> dict:
    schema_info = report.get("modules", {}).get("schema", {})
    missing = schema_info.get("types_missing", [])
    changes = []

    if not missing:
        return {
            "changes": [],
            "modified_html": html,
            "target": "head",
        }

    if backend is not None:
        # v3: Use LLM to generate context-aware JSON-LD
        blocks, changes = _generate_with_llm(html, missing, backend)
    else:
        # v2 fallback: Use templates
        blocks = _generate_missing_blocks(missing)
        changes = [f"Added {t} JSON-LD block (template)" for t in missing if t in _SCHEMA_TEMPLATES]

    if not blocks:
        return {
            "changes": [],
            "modified_html": html,
            "target": "head",
        }

    insert_str = "\n".join(blocks)
    head_close = "</head>"
    modified = html.replace(head_close, f"\n{insert_str}\n{head_close}", 1)

    return {
        "changes": changes,
        "modified_html": modified,
        "target": "head",
    }


def _generate_with_llm(html: str, missing_types: list[str], backend) -> tuple[list[str], list[str]]:
    """Use an LLM backend to generate context-aware JSON-LD blocks."""
    # Extract content snippets to give the LLM context
    import re
    title = ""
    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_m:
        title = title_m.group(1).strip()

    h1 = ""
    h1_m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if h1_m:
        h1 = h1_m.group(1).strip()

    # Get text snippets from body
    body_text = ""
    body_m = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
    if body_m:
        # Strip tags for context
        body_text = re.sub(r"<[^>]+>", " ", body_m.group(1))
        body_text = re.sub(r"\s+", " ", body_text).strip()[:2000]

    types_str = ", ".join(missing_types)
    prompt = f"""Given the following webpage content, generate valid JSON-LD structured data blocks for these schema types: {types_str}.

Page title: {title}
Page heading: {h1}
Page content snippet:
{body_text}

For each schema type, output a complete <script type="application/ld+json"> block with valid schema.org JSON-LD. Use the page's actual content to fill in the fields (not placeholders). Make the data accurate and useful for AI search engines.

Output format — for each schema type, output exactly:
===SCHEMA_TYPE===
<script type="application/ld+json">
...
</script>
===END===

Generate only the JSON-LD blocks, no explanations."""

    try:
        response = backend.generate(prompt, system=(
            "You are an SEO and structured data expert. Generate accurate, "
            "valid JSON-LD blocks based on the actual page content provided. "
            "Use real values from the content, not placeholder text. "
            "Output only the requested format, nothing else."
        ))
    except Exception:
        return [], []

    blocks = []
    types_done = set()

    # Parse the LLM response for blocks
    current_type = None
    current_block = []
    for line in response.split("\n"):
        stripped = line.strip()
        if stripped.startswith("===SCHEMA_TYPE==="):
            if current_type and current_block:
                blocks.append("\n".join(current_block))
                types_done.add(current_type)
            current_type = stripped.replace("===SCHEMA_TYPE===", "").strip()
            current_block = []
        elif stripped == "===END===":
            if current_type and current_block:
                blocks.append("\n".join(current_block))
                types_done.add(current_type)
            current_type = None
            current_block = []
        elif current_type:
            current_block.append(line)

    # Capture last block if no ===END=== marker
    if current_type and current_block:
        blocks.append("\n".join(current_block))
        types_done.add(current_type)

    changes = [f"Added {t} JSON-LD block (LLM-generated)" for t in types_done]
    return blocks, changes


_SCHEMA_TEMPLATES = {
    "FAQPage": (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "FAQPage",\n'
        '  "mainEntity": [{\n'
        '    "@type": "Question",\n'
        '    "name": "[Derive questions from page content]",\n'
        '    "acceptedAnswer": {\n'
        '      "@type": "Answer",\n'
        '      "text": "[Provide answers from page content]"\n'
        '    }\n'
        '  }]\n'
        '}\n'
        '</script>'
    ),
    "BreadcrumbList": (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "BreadcrumbList",\n'
        '  "itemListElement": [{\n'
        '    "@type": "ListItem",\n'
        '    "position": 1,\n'
        '    "name": "[Page title]",\n'
        '    "item": "[Page URL]"\n'
        '  }]\n'
        '}\n'
        '</script>'
    ),
    "Organization": (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "Organization",\n'
        '  "name": "[Organization name]",\n'
        '  "url": "[Site URL]"\n'
        '}\n'
        '</script>'
    ),
    "Article": (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "Article",\n'
        '  "headline": "[Page heading]",\n'
        '  "datePublished": "[Date]"\n'
        '}\n'
        '</script>'
    ),
    "Review": (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "Review",\n'
        '  "reviewBody": "[Review text]",\n'
        '  "reviewRating": {\n'
        '    "@type": "Rating",\n'
        '    "ratingValue": "[Score]"\n'
        '  }\n'
        '}\n'
        '</script>'
    ),
    "AggregateRating": (
        '<script type="application/ld+json">\n'
        '{\n'
        '  "@context": "https://schema.org",\n'
        '  "@type": "AggregateRating",\n'
        '  "ratingValue": "[Score]",\n'
        '  "reviewCount": "[Count]"\n'
        '}\n'
        '</script>'
    ),
}


def _generate_missing_blocks(missing: list[str]) -> list[str]:
    return [
        template
        for schema_type, template in _SCHEMA_TEMPLATES.items()
        if schema_type in missing
    ]
