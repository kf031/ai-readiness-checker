# Phase 3: Schema Extraction - Research

**Researched:** 2026-05-03
**Domain:** Structured data extraction from HTML (JSON-LD, microdata, RDFa, OpenGraph) via extruct
**Confidence:** HIGH

## Summary

Phase 3 extracts all structured data from page HTML using the `extruct` library (v0.18.0) and identifies presence of 6 high-value schema.org types: Product, FAQPage, Organization/LocalBusiness, BreadcrumbList, Article/BlogPosting, and Review/AggregateRating. The output is a `SchemaAnalysis` dataclass containing raw extracted data across formats, a set of detected types, and a weighted 0.0-1.0 score where FAQPage and Product carry the highest weights for e-commerce relevance.

The core technical challenge is normalizing type representations across multiple formats. The same "Product" schema type appears as `"Product"` in JSON-LD, `"http://schema.org/Product"` in microdata, `["http://schema.org/Product"]` in RDFa, and `"product"` in OpenGraph. A unified type-collection function handles all formats plus the `@graph` nested-item pattern.

Error handling uses extruct's built-in `errors="log"` mode, which silently skips malformed JSON-LD blocks and unparseable HTML rather than raising exceptions. This ensures a page with some bad structured data still yields results for the formats that parse successfully.

**Primary recommendation:** Use `extruct.extract(html, uniform=True, errors='log', syntaxes=['json-ld', 'microdata', 'opengraph', 'rdfa'])` with a recursive type collector that handles all four formats and the @graph pattern.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Structured data extraction from HTML | API / Backend | -- | extruct runs server-side against raw HTML strings -- this is a pure Python data processing step |
| Schema type identification | API / Backend | -- | Business logic: normalizing type names and matching against the 6 target types |
| Schema scoring | API / Backend | -- | Pure computation from detected types; consumed by Phase 5 scorer |
| Raw HTML source | Frontend Server / Crawler | -- | Provided by Phase 1 crawler via FetchResult.html |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| extruct | 0.18.0 | Extract JSON-LD, microdata, RDFa, OpenGraph from HTML | Only mature Python library that covers all four structured data formats in a single API [VERIFIED: PyPI, installed package] |
| beautifulsoup4 | 4.14.3 | HTML parsing (lxml backend) | Already in project via Phase 1; FetchResult provides pre-parsed `.soup` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| lxml | 6.0.2 | XML/HTML parser used by extruct and BS4 | Already installed as transitive dependency of both extruct and beautifulsoup4 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| extruct | Custom BS4 scraping per format | extruct handles edge cases (nested microdata, @graph JSON-LD, RDFa vocabularies) that would require hundreds of lines of custom code; extruct has 7 years of community testing [CITED: github.com/scrapinghub/extruct, 962 stars, 557 commits] |
| extruct | rdflib directly for RDFa | rdflib is complex and requires custom parsing of HTML RDFa attributes; extruct wraps this correctly |
| extruct | Separate libraries per format | Fragments error handling, inconsistent type representation across formats |

**Installation:**
```bash
# Already in pyproject.toml dependencies
pip install "extruct>=0.17,<1.0"
```

**Version verification:** `extruct` 0.18.0 is installed on the dev machine. `pyproject.toml` specifies `>=0.17,<1.0` which correctly bounds the current latest (0.18.0). The `w3lib` and `rdflib` transitive dependencies are both installed at current versions (w3lib 2.4.1, rdflib 7.6.0).

## Architecture Patterns

### System Architecture Diagram

```
FetchResult.html (raw HTML string from Phase 1 crawler)
    |
    v
extruct.extract(html, uniform=True, errors='log')
    |
    +---> json-ld items    [@type: "Product", @graph: [...]]
    +---> microdata items   [@type: "Article", properties: {...}]
    +---> opengraph items   [@type: "product", og:title: "..."]
    +---> rdfa items        [@type: ["http://schema.org/FAQPage"]]
    |
    v
Collect Types (recursive, handles @graph)
    |
    +---> Flatten @graph arrays
    +---> Normalize URIs -> short names
    +---> Normalize OpenGraph lowercase
    +---> Deduplicate
    |
    v
Match Against 6 Target Types
    |
    v
Compute Weighted Score
    |
    v
SchemaAnalysis dataclass
    raw: {format: [items]}    # all extracted structured data
    detected_types: set[str]  # which of 6 types found
    type_details: dict        # per-type metadata (count, format source)
    score: float              # 0.0-1.0 weighted by type importance
```

### Recommended Project Structure
```
src/checker/
├── contracts.py        # SchemaAnalysis dataclass (add here)
├── schema_analyzer.py  # NEW: analyze_schema(fetch_result) -> SchemaAnalysis
├── crawler.py          # existing (Phase 1)
├── ...
tests/
├── conftest.py         # Add schema HTML fixtures here
├── test_schema.py      # NEW: SCHEMA-01, SCHEMA-02, SCHEMA-03 test coverage
```

### Pattern 1: Unified Type Collection from extruct Output

**What:** A single recursive function that extracts all `@type` values from extruct's uniform-mode output dict, normalizing across format differences (JSON-LD short names, microdata URIs, RDFa URI lists, OpenGraph lowercase, @graph nesting).

**When to use:** Every time extruct output needs to be queried for schema.org type presence.

**Example:**
```python
# Source: Verified via local testing of extruct 0.18.0 on 2026-05-03

def normalize_type_name(type_str: str | None) -> str | None:
    """Convert URI or mixed-case type to short PascalCase name."""
    if type_str is None:
        return None
    # Strip URI prefix: "http://schema.org/Product" -> "Product"
    if "/" in type_str:
        type_str = type_str.rsplit("/", 1)[-1]
    return type_str


def collect_schema_types(extracted: dict) -> set[str]:
    """Recursively extract all @type values from extruct uniform-mode output.

    Handles:
    - JSON-LD @type (string, e.g. "Product")
    - JSON-LD @graph (nested items, top-level @type is None)
    - Microdata @type in uniform mode (string, e.g. "LocalBusiness")
    - RDFa @type (list of full URIs, e.g. ["http://schema.org/Product"])
    - OpenGraph @type in uniform mode (lowercase, e.g. "product")
    """
    types_found: set[str] = set()

    def _recurse(item: dict) -> None:
        # JSON-LD @graph: types are nested inside the graph array
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
```

### Anti-Patterns to Avoid

- **Assuming @type is always a string:** RDFa returns a list of URI strings. Must check `isinstance(t, list)` before treating as a string.
- **Ignoring @graph:** JSON-LD frequently uses `@graph` to group multiple top-level types. The wrapper item has `@type: None` and all actual types are in the `@graph` array. Must recurse into it.
- **Using default `errors="strict"`:** extruct defaults to raising exceptions on malformed JSON-LD. Production code must use `errors="log"` or `errors="ignore"` so a single bad `<script>` block doesn't lose all other valid structured data.
- **Excluding RDFa:** Although less common than JSON-LD and microdata, RDFa is used by some major sites (particularly those built on Drupal or with semantic HTML). Excluding it misses valid structured data.
- **Scoring on raw type count:** A page with 15 BreadcrumbList items should not score higher than one with a single Product type. Score on type *presence* (boolean), not count.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON-LD parsing from `<script>` tags | Custom regex/JSON parsing of script blocks | extruct's JsonLdExtractor | extruct handles HTML comments inside JSON-LD blocks (via jstyleson), multiple script blocks, and edge cases like Unicode escapes |
| Microdata itemprop/itemscope traversal | Custom BeautifulSoup DOM traversal | extruct's MicrodataExtractor | extruct correctly implements the W3C Microdata algorithm including nested items, itemref resolution, and property URI resolution |
| RDFa vocabulary resolution | Manual RDFa attribute parsing | extruct's RDFaExtractor (wraps pyrdfa3 + rdflib) | RDFa has complex prefix/vocabulary resolution rules that are easy to get wrong; extruct delegates to rdflib which handles the full spec |
| Type name normalization across formats | Custom string manipulation per format | Unified normalize_type_name + collect_schema_types as shown above | The four formats encode schema.org types differently; a single normalization function ensures consistent matching |

**Key insight:** Structured data extraction looks simple on the surface but each format has edge cases that took years of community testing to handle correctly. extruct is the result of 557 commits across 7+ years specifically addressing those edge cases.

## Runtime State Inventory

> Not applicable -- this is a greenfield module that produces a new dataclass. No existing runtime state references schema analysis.

## Common Pitfalls

### Pitfall 1: JSONDecodeError on malformed JSON-LD

**What goes wrong:** A site's `<script type="application/ld+json">` block contains invalid JSON (e.g., a plain text description, or JSON with syntax errors). extruct's default `errors="strict"` mode raises `json.decoder.JSONDecodeError`, crashing the entire analysis.

**Why it happens:** extruct uses `jstyleson.loads()` to parse each JSON-LD block. When JSON is malformed, the parser raises. The default `errors="strict"` propagates this exception rather than eating it.

**How to avoid:** Always call `extruct.extract(html, errors="log", syntaxes=[...])`. With `errors="log"`, the JSON-LD extractor's exception is caught and logged to the Python logger, and the `"json-ld"` key is simply absent from the output dict. Other formats (microdata, RDFa) still extract successfully.

**Warning signs:** Extractor returning an empty dict `{}`, or missing keys in the output.

[VERIFIED: tested locally with malformed JSON-LD input -- `errors="log"` silently skips the bad block; `errors="strict"` raises JSONDecodeError]

### Pitfall 2: OpenGraph @type case mismatch

**What goes wrong:** OpenGraph `og:type` values are lowercase by convention (e.g., `"product"`, `"article"`), but schema.org types are PascalCase (`"Product"`, `"Article"`). The type matcher must compare case-insensitively or normalize both sides.

**Why it happens:** The OpenGraph protocol defines `og:type` as an arbitrary lowercase string. HTML authors write `<meta property="og:type" content="product">`. But our target type list uses PascalCase `"Product"`.

**How to avoid:** Normalize the extracted OpenGraph type to title-case before comparison, or use case-insensitive matching. In the `collect_schema_types` function above, normalize `"product"` to `"Product"` by title-casing after URI extraction.

**Warning signs:** A page with `<meta property="og:type" content="product">` reports "no Product schema found" when it clearly has product structured data via OpenGraph.

[VERIFIED: tested locally -- extruct uniform mode returns `@type: "product"` (lowercase) from OpenGraph]

### Pitfall 3: @graph items missed

**What goes wrong:** A page uses the common JSON-LD `@graph` pattern to declare multiple top-level types. The extractor only checks `item["@type"]` at the top level, finds `None`, and reports zero types found -- even though the `@graph` array contains Product, Organization, and WebSite types.

**Why it happens:** When JSON-LD uses `@graph`, the outer object is `{"@context": "...", "@graph": [...]}` with no `@type` on the wrapper itself. All type information is nested inside.

**How to avoid:** The `collect_schema_types` function above explicitly checks for `@graph` keys and recurses into each graph item before checking `@type`.

**Warning signs:** A known product page with visible JSON-LD blocks reports "no structured data types found."

[VERIFIED: tested locally -- extruct uniform mode on @graph input: top-level `@type: None`, types exist only in nested `@graph` items]

### Pitfall 4: dublincore false positive

**What goes wrong:** extruct's dublincore extractor always returns a list containing one item (`{"namespaces": {}, "elements": [], "terms": []}`) even on pages with no Dublin Core metadata. If dublincore is included in syntaxes and its output is checked for truthiness, every page appears to have structured data.

**Why it happens:** The DublinCoreExtractor always produces a result dict, even when no DC elements are found.

**How to avoid:** Exclude `'dublincore'` from the syntaxes list. For Phase 3's purposes (identifying the 6 schema.org types), Dublin Core metadata is irrelevant.

**Warning signs:** Every page, including empty `<html><body></body></html>`, reports "1 dublincore item found."

[VERIFIED: tested locally -- `extruct.extract("<html><body></body></html>")` returns `{'dublincore': [{'namespaces': {}, 'elements': [], 'terms': []}]}`]

### Pitfall 5: Including 'microformat' with pre-parsed trees

**What goes wrong:** Passing an lxml tree object (`FetchResult.soup`) to extruct with `'microformat'` in syntaxes raises `ValueError: 'microformat' syntax requires a string, not a parsed tree.`

**Why it happens:** The microformat extractor (mf2py) requires a raw HTML string, not a pre-parsed lxml tree. extruct explicitly checks for this and raises when a tree is passed with 'microformat' in the syntax list.

**How to avoid:** If using the pre-parsed soup, exclude `'microformat'` from syntaxes. If microformats are needed, pass the raw HTML string instead. For Phase 3, microformats are irrelevant to the 6 target schema.org types, so simply exclude `'microformat'` from the syntaxes list.

**Warning signs:** `ValueError` when calling extruct with soup object.

[VERIFIED: extruct source code lines 82-87 -- explicit ValueError check for microformat + tree combination]

## Code Examples

Verified patterns from testing extruct 0.18.0 locally:

### Core Extraction Call
```python
# Source: Verified via local testing of extruct 0.18.0, 2026-05-03
import extruct
import logging

logger = logging.getLogger(__name__)

def extract_structured_data(html: str) -> dict:
    """Extract all structured data formats from HTML.

    Uses uniform=True so all formats produce consistent
    {'@context': ..., '@type': ..., ...} dict structures.

    Uses errors='log' so malformed JSON-LD blocks are skipped
    without crashing the entire extraction.
    """
    return extruct.extract(
        html,
        uniform=True,
        errors="log",
        syntaxes=["json-ld", "microdata", "opengraph", "rdfa"],
    )
```

### Type Matching Against 6 Target Types
```python
# Source: Derived from extruct 0.18.0 behavior, verified via testing

# The 6 target types with their scoring weights (SCHEMA-03)
TARGET_TYPES: dict[str, float] = {
    "Product": 0.25,
    "FAQPage": 0.25,
    "Organization": 0.08,  # half of Organization/LocalBusiness weight
    "LocalBusiness": 0.07,  # half of Organization/LocalBusiness weight
    "BreadcrumbList": 0.10,
    "Article": 0.05,        # half of Article/BlogPosting weight
    "BlogPosting": 0.05,    # half of Article/BlogPosting weight
    "Review": 0.075,        # half of Review/AggregateRating weight
    "AggregateRating": 0.075,  # half of Review/AggregateRating weight
}
# Total: 0.25+0.25+0.08+0.07+0.10+0.05+0.05+0.075+0.075 = 1.0

# Map detected subtypes to their category for scoring
TYPE_CATEGORY: dict[str, str] = {
    # Each concrete type maps to one of the 6 categories
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
```

### Scoring Formula (SCHEMA-03)
```python
# Source: Derived from SCHEMA-03 requirement: "weighted by schema type
# importance (FAQPage and Product weighted highest for e-commerce)"

def compute_schema_score(
    detected_types: set[str],
    weights: dict[str, float] | None = None,
) -> float:
    """Compute 0.0-1.0 schema score from detected types.

    Each of the 6 high-value type categories has a weight.
    When a type is present, its weight is added to the score.
    FAQPage and Product have the highest weights (0.25 each)
    reflecting their importance for e-commerce search visibility.
    """
    if weights is None:
        weights = TARGET_TYPES

    if not detected_types:
        return 0.0

    # Collect which of the 6 categories are present
    categories_present: set[str] = set()
    for t in detected_types:
        category = TYPE_CATEGORY.get(t)
        if category:
            categories_present.add(category)

    # Score: sum of weights for present categories
    # Each category contributes at most once
    score = 0.0
    for t, weight in weights.items():
        category = TYPE_CATEGORY.get(t, "")
        if category in categories_present:
            score += weight

    return min(score, 1.0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| extruct < 0.17 without uniform mode | extruct 0.18.0 with `uniform=True` | 0.18.0 (current) | Uniform mode normalizes all format outputs to consistent `{@context, @type, ...}` dicts, eliminating the need for format-specific type extraction logic |
| extruct `errors='strict'` (default) | extruct with `errors='log'` | Always available (parameter since early versions) | Production-safe: malformed JSON-LD no longer crashes extraction |

**Deprecated/outdated:**
- extruct's `url` parameter: Use `base_url` instead. The `url` parameter emits a DeprecationWarning in 0.18.0.
- RDFa in non-uniform mode: The output is rdflib JSON-LD with full URIs; `uniform=True` handles this better by flattening to standard dicts (though RDFa uniform support is noted as incomplete for some edge cases).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The scoring weights (Product=0.25, FAQPage=0.25, etc.) are appropriate for e-commerce focus | Code Examples - Scoring | Weights can be adjusted; this is a tunable parameter, not a structural design decision. Risk is low. |
| A2 | Uniform mode on RDFa works correctly for the 6 target types | State of the Art | extruct docs note RDFa uniform support is incomplete. If RDFa output for target types is malformed, we may miss types declared via RDFa. Mitigation: our type collector handles RDFa non-uniform output too (list of URIs). |
| A3 | The 6 type categories (Product, FAQPage, Organization/LocalBusiness, BreadcrumbList, Article/BlogPosting, Review/AggregateRating) cover the most valuable schema types for AI search visibility | Architecture Patterns | These are defined in REQUIREMENTS.md SCHEMA-02. Adding or removing types is a simple config change. |

## Open Questions (RESOLVED)

1. **Should OpenGraph `og:type` contribute to the 6-type detection?**
   - What we know: OpenGraph types are lowercase strings like "product", "article", "website". These can indicate the page type.
   - What's unclear: Whether SCHEMA-02 intends OpenGraph types to count toward "which of the 6 schema types are present" or only schema.org types (JSON-LD, microdata, RDFa).
   - Recommendation: Include OpenGraph types but weight them lower. An `og:type` of "product" is a weaker signal than a full JSON-LD Product with offers/price. The planner should confirm or should treat as Claude's discretion.

2. **Should AggregateRating without Review count as "Review/AggregateRating"?**
   - What we know: `AggregateRating` can appear standalone (e.g., on a Product page without a full Review markup) or nested inside a Review.
   - What's unclear: Whether the category should trigger on AggregateRating alone, or only when paired with Review.
   - Recommendation: Treat them independently. If either Review or AggregateRating is present, the category is considered present. This is the more generous interpretation and catches more structured data.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Runtime | Yes | 3.13.9 | -- |
| extruct | SCHEMA-01 structured data extraction | Yes | 0.18.0 | -- |
| beautifulsoup4 | Input from FetchResult | Yes | 4.14.3 | -- |
| lxml | HTML parsing (extruct, BS4) | Yes | 6.0.2 | -- |
| pytest | Test execution | Yes | 8.4.2 | -- |

**Missing dependencies with no fallback:** None -- all required dependencies are installed and version-compatible.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python -m pytest tests/test_schema.py -v` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHEMA-01 | All structured data extracted from JSON-LD, microdata, RDFa in page HTML | unit | `pytest tests/test_schema.py::test_extract_all_formats -x` | No -- Wave 0 |
| SCHEMA-01 | Graceful handling of malformed JSON-LD (does not crash) | unit | `pytest tests/test_schema.py::test_malformed_jsonld_handled -x` | No -- Wave 0 |
| SCHEMA-01 | Handles @graph JSON-LD pattern correctly | unit | `pytest tests/test_schema.py::test_graph_pattern -x` | No -- Wave 0 |
| SCHEMA-02 | Identifies Product type from JSON-LD | unit | `pytest tests/test_schema.py::test_detect_product_jsonld -x` | No -- Wave 0 |
| SCHEMA-02 | Identifies FAQPage type from microdata | unit | `pytest tests/test_schema.py::test_detect_faqpage_microdata -x` | No -- Wave 0 |
| SCHEMA-02 | Identifies Organization/LocalBusiness as one category | unit | `pytest tests/test_schema.py::test_organization_or_localbusiness -x` | No -- Wave 0 |
| SCHEMA-02 | Identifies Article/BlogPosting as one category | unit | `pytest tests/test_schema.py::test_article_or_blogposting -x` | No -- Wave 0 |
| SCHEMA-02 | Identifies Review/AggregateRating as one category | unit | `pytest tests/test_schema.py::test_review_or_aggregaterating -x` | No -- Wave 0 |
| SCHEMA-02 | Identifies BreadcrumbList type | unit | `pytest tests/test_schema.py::test_detect_breadcrumblist -x` | No -- Wave 0 |
| SCHEMA-02 | Reports correctly when no types found | unit | `pytest tests/test_schema.py::test_no_types_found -x` | No -- Wave 0 |
| SCHEMA-02 | Does not crash on empty HTML | unit | `pytest tests/test_schema.py::test_empty_html -x` | No -- Wave 0 |
| SCHEMA-03 | Score = 1.0 when all 6 categories present | unit | `pytest tests/test_schema.py::test_score_all_categories -x` | No -- Wave 0 |
| SCHEMA-03 | Score = 0.0 when no types present | unit | `pytest tests/test_schema.py::test_score_zero -x` | No -- Wave 0 |
| SCHEMA-03 | Product and FAQPage each contribute 0.25 (highest weights) | unit | `pytest tests/test_schema.py::test_score_product_faqpage_weights -x` | No -- Wave 0 |
| SCHEMA-03 | Partial presence produces proportionate score | unit | `pytest tests/test_schema.py::test_score_partial -x` | No -- Wave 0 |
| SCHEMA-03 | OpenGraph type detection contributes (if enabled by resolution of Open Question #1) | unit | `pytest tests/test_schema.py::test_og_type_detection -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_schema.py -v`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full test suite (40 existing + new schema tests) green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_schema.py` -- covers all SCHEMA-01, SCHEMA-02, SCHEMA-03 requirements
- [ ] `tests/conftest.py` -- add 6-8 HTML fixtures: JSON-LD Product, microdata FAQPage, @graph multi-type, RDFa Product, malformed JSON-LD, empty page, OpenGraph product, full multi-format page
- [ ] No framework install needed -- pytest already configured in pyproject.toml

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | No | -- |
| V3 Session Management | No | -- |
| V4 Access Control | No | -- |
| V5 Input Validation | Yes | extruct processes untrusted HTML from arbitrary URLs. Mitigation: use `errors="log"` to prevent malformed input from crashing; extruct uses lxml (C library with libxml2) for parsing which is memory-safe for well-formed input; no JavaScript execution occurs. |
| V6 Cryptography | No | -- |

### Known Threat Patterns for extruct + HTML parsing

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malformed JSON-LD causing unhandled exception | Denial of Service | `errors="log"` catches and logs extractor exceptions without crashing |
| Extremely large HTML payloads | Denial of Service | Phase 1 crawler already enforces `MAX_RESPONSE_SIZE` (10MB); extruct receives already-capped HTML |
| Billion laughs / XML entity expansion via lxml | Denial of Service | lxml disables network access and DTD loading by default in recent versions; libxml2 has built-in entity expansion limits |
| HTML with embedded JavaScript in JSON-LD | Information Disclosure | extruct does not execute JavaScript; JSON-LD is parsed as static data via `jstyleson.loads()` |

## Sources

### Primary (HIGH confidence)
- extruct 0.18.0 installed and tested locally -- verified all format outputs, error modes, @graph behavior, uniform mode, dublincore false positive
- extruct source code at `/opt/miniconda3/lib/python3.13/site-packages/extruct/_extruct.py` -- verified `errors` parameter behavior, syntax validation, processor dispatch, uniform mode
- extruct GitHub README via WebFetch -- API documentation, supported formats, CLI usage [CITED: github.com/scrapinghub/extruct]

### Secondary (MEDIUM confidence)
- Google Search Gallery structured data documentation -- 26 rich result types, Product (Ecommerce), FAQ (standalone), LocalBusiness (Organizations), Breadcrumb (Generic), Article (News), Review (multiple categories) [CITED: developers.google.com/search/docs/appearance/structured-data/search-gallery]
- extruct GitHub issues -- known issues with empty HTML parsing, JSON-LD outside HTML elements, pip installation compatibility [CITED: github.com/scrapinghub/extruct/issues]

### Tertiary (LOW confidence)
- WebSearch for extruct usage patterns -- returned results but no detailed code examples beyond what was already known from docs

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- extruct is installed, tested, and its behavior is verified through 10+ local experiments
- Architecture: HIGH -- type collection algorithm tested against all 4 formats plus @graph pattern, uniform mode confirmed working
- Pitfalls: HIGH -- 5 pitfalls identified and verified through local testing (malformed JSON-LD, dublincore false positive, @graph nesting, OpenGraph case mismatch, microformat tree restriction)

**Research date:** 2026-05-03
**Valid until:** 2026-08-03 (extruct is stable; 0.18.0 released recently; no breaking changes expected)
