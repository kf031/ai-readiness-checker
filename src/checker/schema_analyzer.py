"""
Schema extraction and scoring for AI readiness analysis.

Extracts structured data from HTML across 4 formats (JSON-LD, microdata,
OpenGraph, RDFa) using extruct, identifies presence of 6 high-value
schema.org types, and computes a weighted 0.0-1.0 score where FAQPage
and Product carry the highest weights for e-commerce relevance.

Covers: SCHEMA-01 (extraction), SCHEMA-02 (type identification),
SCHEMA-03 (weighted scoring).

Dependencies:
    - extruct 0.18.0: HTML structured data extraction
    - extruct configured with uniform=True, errors='log' for production safety

Open Questions Resolved (per planner discretion):
    1. OpenGraph og:type is INCLUDED in type detection. Lowercase OG types
       are normalized to PascalCase via normalize_type_name().title().
       They carry the same weight as other formats since scoring is
       presence-based (boolean), not confidence-weighted.
    2. AggregateRating without Review COUNTS toward the Review/AggregateRating
       category. Both subtypes are treated independently -- finding either
       one makes the category present.
"""

import logging
from datetime import datetime, timezone

import extruct

from checker.contracts import FetchResult, SchemaAnalysis

logger = logging.getLogger(__name__)

# Weights for the 9 concrete schema.org types that map to
# the 6 high-value categories. FAQPage and Product weighted
# highest (0.25 each) for e-commerce relevance.
# Total across all 9 types = 1.0
TARGET_TYPES: dict[str, float] = {
    "Product": 0.25,
    "FAQPage": 0.25,
    "Organization": 0.08,       # half of Organization/LocalBusiness weight (0.15)
    "LocalBusiness": 0.07,       # half of Organization/LocalBusiness weight (0.15)
    "BreadcrumbList": 0.10,
    "Article": 0.05,             # half of Article/BlogPosting weight (0.10)
    "BlogPosting": 0.05,         # half of Article/BlogPosting weight (0.10)
    "Review": 0.075,             # half of Review/AggregateRating weight (0.15)
    "AggregateRating": 0.075,    # half of Review/AggregateRating weight (0.15)
}

# Maps each concrete schema.org type to its 6-category group.
# Used by compute_schema_score to aggregate types into categories.
TYPE_CATEGORY: dict[str, str] = {
    "Product": "Product",
    "FAQPage": "FAQPage",
    "Organization": "Organization/LocalBusiness",
    "LocalBusiness": "Organization/LocalBusiness",
    "BreadcrumbList": "BreadcrumbList",
    "Article": "Article/BlogPosting",
    "BlogPosting": "Article/BlogPosting",
    "Review": "Review/AggregateRating",
    "AggregateRating": "Review/AggregateRating",
}


def extract_structured_data(html: str) -> dict:
    """Extract all structured data formats from HTML using extruct.

    Configures extruct with:
        - uniform=True: normalizes all format outputs to consistent
          {'@context': ..., '@type': ..., ...} dict structures
        - errors='log': malformed JSON-LD blocks are caught, logged,
          and skipped without crashing the entire extraction
        - syntaxes: json-ld, microdata, opengraph, rdfa only
          (excludes dublincore -- always returns a false-positive empty item;
           excludes microformat -- requires raw HTML string, not parsed tree)

    Args:
        html: Raw HTML string from FetchResult.html

    Returns:
        Dict with keys 'json-ld', 'microdata', 'opengraph', 'rdfa'.
        Each value is a list of extracted items (may be empty).
        On catastrophic failure, returns empty dict with logged error.
    """
    try:
        result = extruct.extract(
            html,
            uniform=True,
            errors="log",
            syntaxes=["json-ld", "microdata", "opengraph", "rdfa"],
        )
    except Exception:
        logger.exception("extruct.extract raised unexpected exception")
        result = {}

    # Normalize: ensure all 4 expected keys are present even when
    # extruct omits them (e.g., when all JSON-LD blocks are malformed
    # and errors="log" causes the entire json-ld key to be absent).
    for key in ("json-ld", "microdata", "opengraph", "rdfa"):
        result.setdefault(key, [])

    return result


def normalize_type_name(type_str: str | None) -> str | None:
    """Convert URI or mixed-case type string to PascalCase short name.

    Handles:
        - Full URIs: "http://schema.org/Product" -> "Product"
        - PascalCase: "Product" -> "Product" (pass-through)
        - Lowercase (OpenGraph): "product" -> "Product" (via .title())

    Returns None if type_str is None or empty after stripping.
    """
    if type_str is None:
        return None
    # Strip URI prefix: "http://schema.org/Product" -> "Product"
    if "/" in type_str:
        type_str = type_str.rsplit("/", 1)[-1]
    # Normalize case for OpenGraph lowercase types (e.g., "product" -> "Product")
    # Using .title() handles single-word types correctly
    type_str = type_str.strip()
    if not type_str:
        return None
    # Title-case only lowercase strings (OpenGraph convention).
    # Already-PascalCase strings (e.g., "FAQPage", "BreadcrumbList")
    # must pass through unmodified -- .title() would corrupt them.
    if type_str.islower():
        return type_str.title()
    return type_str


def collect_schema_types(extracted: dict) -> set[str]:
    """Recursively extract all @type values from extruct uniform-mode output.

    Handles all 4 format-specific representations:
        - JSON-LD @type as string: "Product"
        - JSON-LD @graph: types nested inside the graph array
          (top-level @type is None on the wrapper object)
        - Microdata @type in uniform mode: string like "LocalBusiness"
        - RDFa @type: list of full URIs like ["http://schema.org/Product"]
        - OpenGraph @type in uniform mode: lowercase string like "product"

    Args:
        extracted: Dict from extruct.extract() with format keys.

    Returns:
        Set of normalized PascalCase type names (e.g., {"Product", "FAQPage"}).
    """
    types_found: set[str] = set()

    def _recurse(item: dict) -> None:
        # JSON-LD @graph: types are nested inside the graph array.
        # The wrapper object has @type = None; recurse into each graph item.
        if "@graph" in item and isinstance(item["@graph"], list):
            for graph_item in item["@graph"]:
                _recurse(graph_item)

        t = item.get("@type")
        if t is None:
            return

        if isinstance(t, list):
            # RDFa: @type is a list of full URIs
            for uri in t:
                name = normalize_type_name(uri)
                if name:
                    types_found.add(name)
        elif isinstance(t, str):
            name = normalize_type_name(t)
            if name:
                types_found.add(name)

    for format_name in ("json-ld", "microdata", "opengraph", "rdfa"):
        for item in extracted.get(format_name, []):
            _recurse(item)

    return types_found


def compute_schema_score(
    detected_types: set[str],
    weights: dict[str, float] | None = None,
) -> float:
    """Compute 0.0-1.0 schema score from detected concrete types.

    Each of the 9 concrete schema.org types has a weight. For each
    detected type, its weight is added to the score. This means finding
    both Organization AND LocalBusiness adds 0.08 + 0.07 = 0.15 for
    the Organization/LocalBusiness category.

    FAQPage (0.25) and Product (0.25) have the highest weights,
    reflecting their importance for e-commerce AI search visibility.

    Args:
        detected_types: Set of normalized type names from collect_schema_types()
        weights: Override weight dict (defaults to TARGET_TYPES)

    Returns:
        Float in [0.0, 1.0] representing the weighted schema score.
    """
    if weights is None:
        weights = TARGET_TYPES

    if not detected_types:
        return 0.0

    # Sum weights for each detected type. Types not in the
    # weight dict (non-target types) are silently ignored.
    score = 0.0
    for t in detected_types:
        score += weights.get(t, 0.0)

    return min(score, 1.0)


def analyze_schema(fetch_result: FetchResult) -> SchemaAnalysis:
    """Analyze structured data from a fetched page and return scored result.

    This is the single public entry point for Phase 3.
    Consumed by Phase 5 scorer for the schema component (30% weight).

    Pipeline:
        1. Extract structured data from HTML via extruct (SCHEMA-01)
        2. Collect and normalize all type names across formats (SCHEMA-02)
        3. Compute weighted score from detected types (SCHEMA-03)

    Args:
        fetch_result: FetchResult from Phase 1 crawler -- reads .html and .url

    Returns:
        SchemaAnalysis with raw extraction data, detected types,
        per-type metadata, and weighted score.
    """
    raw = extract_structured_data(fetch_result.html)
    detected_types = collect_schema_types(raw)

    # Build per-type metadata: count occurrences and list source formats
    type_details: dict[str, dict] = {}
    for format_name in ("json-ld", "microdata", "opengraph", "rdfa"):
        for item in raw.get(format_name, []):
            t = item.get("@type")
            if isinstance(t, str):
                name = normalize_type_name(t)
            elif isinstance(t, list):
                # RDFa can have multiple types per item; take first as primary
                name = normalize_type_name(t[0]) if t else None
            else:
                name = None
            if name and name in detected_types:
                if name not in type_details:
                    type_details[name] = {"count": 0, "formats": []}
                type_details[name]["count"] += 1
                if format_name not in type_details[name]["formats"]:
                    type_details[name]["formats"].append(format_name)

    score = compute_schema_score(detected_types)

    return SchemaAnalysis(
        url=fetch_result.url,
        raw=raw,
        detected_types=detected_types,
        type_details=type_details,
        score=score,
    )
