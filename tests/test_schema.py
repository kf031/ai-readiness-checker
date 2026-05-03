"""Tests for schema_analyzer.py -- covers SCHEMA-01, SCHEMA-02, SCHEMA-03."""

import pytest
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from src.checker.contracts import SchemaAnalysis, FetchResult
from tests.conftest import (
    SCHEMA_JSONLD_PRODUCT,
    SCHEMA_MICRODATA_FAQ,
    SCHEMA_GRAPH_MULTI_TYPE,
    SCHEMA_RDFA_BREADCRUMB,
    SCHEMA_OG_PRODUCT,
    SCHEMA_MULTI_FORMAT,
    SCHEMA_MALFORMED_JSONLD,
    SCHEMA_EMPTY_HTML,
)


# SCHEMA-01 tests -- structured data extraction from all formats


def test_extract_all_formats():
    """SCHEMA-01: All 4 formats extracted (json-ld, microdata, opengraph, rdfa)."""
    from src.checker.schema_analyzer import extract_structured_data

    result = extract_structured_data(SCHEMA_MULTI_FORMAT)
    assert "json-ld" in result, "Missing json-ld key"
    assert "microdata" in result, "Missing microdata key"
    assert "opengraph" in result, "Missing opengraph key"
    assert "rdfa" in result, "Missing rdfa key"
    assert len(result["json-ld"]) > 0, "json-ld list empty"
    assert len(result["microdata"]) > 0, "microdata list empty"
    assert len(result["opengraph"]) > 0, "opengraph list empty"


def test_malformed_jsonld_handled():
    """SCHEMA-01: Malformed JSON-LD does not crash extraction (errors='log')."""
    from src.checker.schema_analyzer import extract_structured_data

    result = extract_structured_data(SCHEMA_MALFORMED_JSONLD)
    assert "microdata" in result, "microdata key missing"
    # json-ld key should be present (the valid second block)
    assert "json-ld" in result, "json-ld key missing"


def test_graph_pattern():
    """SCHEMA-01: JSON-LD @graph pattern is correctly traversed for nested types."""
    from src.checker.schema_analyzer import extract_structured_data, collect_schema_types

    result = extract_structured_data(SCHEMA_GRAPH_MULTI_TYPE)
    types_found = collect_schema_types(result)
    assert "Product" in types_found, f"Product missing from @graph: {types_found}"
    assert "Organization" in types_found, f"Organization missing from @graph: {types_found}"


# SCHEMA-02 tests -- schema type identification across 6 categories


def test_detect_product_jsonld():
    """SCHEMA-02: Product type detected from JSON-LD."""
    from src.checker.schema_analyzer import extract_structured_data, collect_schema_types

    result = extract_structured_data(SCHEMA_JSONLD_PRODUCT)
    types_found = collect_schema_types(result)
    assert "Product" in types_found, f"Product missing from {types_found}"


def test_detect_faqpage_microdata():
    """SCHEMA-02: FAQPage type detected from microdata."""
    from src.checker.schema_analyzer import extract_structured_data, collect_schema_types

    result = extract_structured_data(SCHEMA_MICRODATA_FAQ)
    types_found = collect_schema_types(result)
    assert "FAQPage" in types_found, f"FAQPage missing from {types_found}"


def test_organization_or_localbusiness():
    """SCHEMA-02: Organization and LocalBusiness map to same category."""
    from src.checker.schema_analyzer import TYPE_CATEGORY

    assert TYPE_CATEGORY.get("Organization") == TYPE_CATEGORY.get("LocalBusiness")
    assert TYPE_CATEGORY.get("Organization") == "Organization/LocalBusiness"


def test_article_or_blogposting():
    """SCHEMA-02: Article and BlogPosting map to same category."""
    from src.checker.schema_analyzer import TYPE_CATEGORY

    assert TYPE_CATEGORY.get("Article") == TYPE_CATEGORY.get("BlogPosting")
    assert TYPE_CATEGORY.get("Article") == "Article/BlogPosting"


def test_review_or_aggregaterating():
    """SCHEMA-02: Review and AggregateRating map to same category (treated independently)."""
    from src.checker.schema_analyzer import TYPE_CATEGORY

    assert TYPE_CATEGORY.get("Review") == TYPE_CATEGORY.get("AggregateRating")
    assert TYPE_CATEGORY.get("Review") == "Review/AggregateRating"


def test_detect_breadcrumblist_rdfa():
    """SCHEMA-02: BreadcrumbList type detected from RDFa."""
    from src.checker.schema_analyzer import extract_structured_data, collect_schema_types

    result = extract_structured_data(SCHEMA_RDFA_BREADCRUMB)
    types_found = collect_schema_types(result)
    assert "BreadcrumbList" in types_found, f"BreadcrumbList missing from {types_found}"


def test_no_types_found():
    """SCHEMA-02: Empty set returned when no schema types present."""
    from src.checker.schema_analyzer import extract_structured_data, collect_schema_types

    result = extract_structured_data(SCHEMA_EMPTY_HTML)
    types_found = collect_schema_types(result)
    assert types_found == set(), f"Expected empty set for empty HTML, got {types_found}"


def test_empty_html():
    """SCHEMA-02: Empty HTML does not crash extraction."""
    from src.checker.schema_analyzer import extract_structured_data

    result = extract_structured_data(SCHEMA_EMPTY_HTML)
    for key in ("json-ld", "microdata", "opengraph", "rdfa"):
        assert key in result, f"Missing key: {key}"
        assert len(result[key]) == 0, f"{key} list not empty: {result[key]}"


def test_og_type_detection():
    """SCHEMA-02: OpenGraph og:type contributes to type detection."""
    from src.checker.schema_analyzer import extract_structured_data, collect_schema_types

    result = extract_structured_data(SCHEMA_OG_PRODUCT)
    types_found = collect_schema_types(result)
    assert "Product" in types_found, f"OG product not detected: {types_found}"


# SCHEMA-03 tests -- weighted scoring


def test_score_all_categories():
    """SCHEMA-03: Score = 0.805 when all 6 categories present (one type each)."""
    from src.checker.schema_analyzer import compute_schema_score

    score = compute_schema_score(
        {"Product", "FAQPage", "Organization", "BreadcrumbList", "Article", "AggregateRating"}
    )
    # Floating-point precision: 0.25+0.25+0.08+0.10+0.05+0.075 may not be exactly 0.805
    assert score == pytest.approx(0.805), f"Expected ~0.805, got {score}"


def test_score_zero():
    """SCHEMA-03: Score = 0.0 when no types present."""
    from src.checker.schema_analyzer import compute_schema_score

    assert compute_schema_score(set()) == 0.0


def test_score_product_faqpage_weights():
    """SCHEMA-03: Product and FAQPage each contribute 0.25 (highest weights)."""
    from src.checker.schema_analyzer import compute_schema_score

    assert compute_schema_score({"Product"}) == 0.25
    assert compute_schema_score({"FAQPage"}) == 0.25


def test_score_partial():
    """SCHEMA-03: Partial type presence produces proportionate score."""
    from src.checker.schema_analyzer import compute_schema_score

    # FAQPage (0.25) + BreadcrumbList (0.10) = 0.35
    assert compute_schema_score({"FAQPage", "BreadcrumbList"}) == 0.35


# -- TARGET_TYPES integrity checks --


def test_weights_sum_to_one():
    """TARGET_TYPES weights sum exactly to 1.0."""
    from src.checker.schema_analyzer import TARGET_TYPES

    total = sum(TARGET_TYPES.values())
    assert abs(total - 1.0) < 0.001, f"TARGET_TYPES sum = {total}, should be 1.0"


def test_type_category_covers_targets():
    """TYPE_CATEGORY has entries for all TARGET_TYPES keys."""
    from src.checker.schema_analyzer import TARGET_TYPES, TYPE_CATEGORY

    assert set(TARGET_TYPES.keys()) == set(TYPE_CATEGORY.keys()), (
        f"Mismatch: TARGET_TYPES keys {set(TARGET_TYPES.keys())}, "
        f"TYPE_CATEGORY keys {set(TYPE_CATEGORY.keys())}"
    )


# -- analyze_schema integration --


def test_analyze_schema_multi_format():
    """analyze_schema returns SchemaAnalysis with correct detected_types."""
    from src.checker.schema_analyzer import analyze_schema

    fetch_result = FetchResult(
        url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        html=SCHEMA_MULTI_FORMAT,
        soup=BeautifulSoup(SCHEMA_MULTI_FORMAT, "lxml"),
        fetched_at=datetime.now(timezone.utc),
    )
    analysis = analyze_schema(fetch_result)
    assert analysis.detected_types.issuperset(
        {"Product", "Article", "FAQPage", "BreadcrumbList"}
    ), f"detected_types missing expected types: {analysis.detected_types}"
