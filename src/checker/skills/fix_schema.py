"""fix-schema — Generates missing JSON-LD structured data blocks."""

SKILL_NAME = "fix-schema"
SKILL_DESCRIPTION = "Generates missing JSON-LD structured data blocks for schema types flagged as absent in the report."


def execute(html: str, report: dict) -> dict:
    schema_info = report.get("modules", {}).get("schema", {})
    missing = schema_info.get("types_missing", [])
    changes = []

    blocks = _generate_missing_blocks(missing)

    if not blocks:
        return {
            "changes": [],
            "modified_html": html,
            "target": "head",
        }

    insert_str = "\n".join(blocks)
    head_close = "</head>"
    modified = html.replace(head_close, f"\n{insert_str}\n{head_close}", 1)
    changes = [f"Added {t} JSON-LD block" for t in missing if t in _SCHEMA_TEMPLATES]

    return {
        "changes": changes,
        "modified_html": modified,
        "target": "head",
    }


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
