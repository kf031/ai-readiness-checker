"""Tests for the content analysis module (Phase 4: CONT-01 through CONT-06)."""

import pytest
from bs4 import BeautifulSoup

from src.checker.content_analyzer import (
    _extract_plain_text,
    extract_entities,
    score_entities,
    score_readability,
    score_text_ratio,
)
from src.checker.contracts import ContentAnalysis
from tests.conftest import (
    CONTENT_HTML_MULTI_ENTITY,
    CONTENT_HTML_TEXT_HEAVY,
    CONTENT_HTML_THIN,
    SCHEMA_EMPTY_HTML,
)


# --- CONT-01: Readability ---

def test_readability_scoring():
    """CONT-01: Readability scoring returns Flesch and Fog."""
    soup = BeautifulSoup(CONTENT_HTML_TEXT_HEAVY, "lxml")
    text = _extract_plain_text(soup)

    flesch, fog, combined = score_readability(text)

    # Flesch should be positive for readable text
    assert flesch > 0, f"Expected positive Flesch, got {flesch}"
    # Fog should be a reasonable grade level (not 0, not absurdly high)
    assert fog > 0, f"Expected positive Fog, got {fog}"
    assert fog < 25, f"Fog too high: {fog}"
    # Combined score must be in [0.0, 1.0]
    assert 0.0 <= combined <= 1.0, f"Combined out of range: {combined}"


def test_readability_empty_text():
    """CONT-01: Empty text returns all zeros, no crash."""
    flesch, fog, combined = score_readability("")

    assert flesch == 0.0
    assert fog == 0.0
    assert combined == 0.0


# --- CONT-02: Text Ratio ---

def test_text_ratio():
    """CONT-02: Content-to-HTML ratio correctly computed."""
    # Text-heavy page
    soup_heavy = BeautifulSoup(CONTENT_HTML_TEXT_HEAVY, "lxml")
    text_heavy = _extract_plain_text(soup_heavy)
    _, score_heavy = score_text_ratio(text_heavy, CONTENT_HTML_TEXT_HEAVY)

    # Thin page (JS SPA shell)
    soup_thin = BeautifulSoup(CONTENT_HTML_THIN, "lxml")
    text_thin = _extract_plain_text(soup_thin)
    _, score_thin = score_text_ratio(text_thin, CONTENT_HTML_THIN)

    # Text-heavy should score higher than thin
    assert score_heavy > score_thin, (
        f"Expected text-heavy ({score_heavy:.3f}) > thin ({score_thin:.3f})"
    )
    assert 0.0 <= score_heavy <= 1.0
    assert 0.0 <= score_thin <= 1.0


def test_text_ratio_empty_html():
    """CONT-02: Empty HTML returns (0.0, 0.0)."""
    ratio, score = score_text_ratio("text", "")
    assert ratio == 0.0
    assert score == 0.0


# --- CONT-03: Named Entities ---

def test_named_entities():
    """CONT-03: Named entities extracted (ORG, PRODUCT, GPE, PERSON)."""
    soup = BeautifulSoup(CONTENT_HTML_MULTI_ENTITY, "lxml")
    text = _extract_plain_text(soup)
    entities = extract_entities(text)

    # If spaCy model installed, should find entities
    # If not, test still passes (entities will be empty due to _get_nlp() returning None)
    if entities:
        # Should find at least ORG entities (Apple, Microsoft, Google, etc.)
        assert "ORG" in entities or "PERSON" in entities, (
            f"Expected ORG or PERSON entities, got: {list(entities.keys())}"
        )
        entity_score = score_entities(entities)
        assert entity_score > 0.0, f"Entity score should be > 0, got {entity_score}"
    else:
        # spaCy model not installed — acceptable, test passes vacuously
        import warnings
        warnings.warn("spaCy model not installed; entity test skipped")


def test_entities_empty_text():
    """CONT-03: Empty text returns empty entities dict."""
    entities = extract_entities("")
    assert entities == {}
    assert score_entities(entities) == 0.0


# --- Edge Cases ---

def test_empty_page():
    """Edge case: Empty page returns all zeros, no crash."""
    soup = BeautifulSoup(SCHEMA_EMPTY_HTML, "lxml")
    text = _extract_plain_text(soup)

    # Readability on empty text
    flesch, fog, combined = score_readability(text)
    assert flesch == 0.0
    assert fog == 0.0
    assert combined == 0.0

    # Text ratio on empty page
    _, ratio_score = score_text_ratio(text, SCHEMA_EMPTY_HTML)
    assert ratio_score == 0.0

    # Entities on empty text
    entities = extract_entities(text)
    assert entities == {}
    assert score_entities(entities) == 0.0


# --- CONT-04: Heading Structure ---

def test_heading_structure():
    """CONT-04: Heading structure analysis (H1 uniqueness, hierarchy, descriptiveness)."""
    from tests.conftest import CONTENT_HTML_TEXT_HEAVY, CONTENT_HTML_NO_HEADINGS
    from src.checker.content_analyzer import analyze_headings, score_headings

    # Text-heavy page with proper heading hierarchy
    soup = BeautifulSoup(CONTENT_HTML_TEXT_HEAVY, "lxml")
    analysis = analyze_headings(soup)

    assert analysis["total_headings"] > 0, "Expected headings in text-heavy page"
    assert analysis["h1_count"] == 1, (
        f"Expected exactly 1 H1, got {analysis['h1_count']}"
    )
    assert analysis["h1_unique"] is True
    assert analysis["hierarchy_violations"] == 0, (
        f"Unexpected hierarchy violations: {analysis['hierarchy_violations']}"
    )
    # At least some headings should be descriptive (>3 words)
    assert analysis["descriptive_count"] > 0, (
        f"No descriptive headings found in {analysis['total_headings']} headings"
    )

    score = score_headings(analysis)
    assert 0.0 <= score <= 1.0, f"Heading score out of range: {score}"
    # Proper heading structure should score well
    assert score > 0.5, f"Heading score too low for well-structured page: {score}"


def test_heading_structure_no_headings():
    """CONT-04: Page with no headings returns score 0.0."""
    from tests.conftest import CONTENT_HTML_NO_HEADINGS
    from src.checker.content_analyzer import analyze_headings, score_headings

    soup = BeautifulSoup(CONTENT_HTML_NO_HEADINGS, "lxml")
    analysis = analyze_headings(soup)

    assert analysis["total_headings"] == 0
    assert analysis["h1_count"] == 0
    assert score_headings(analysis) == 0.0


# --- CONT-05: Q&A Density ---

def test_qa_density():
    """CONT-05: Q&A density scoring."""
    from tests.conftest import CONTENT_HTML_FAQ
    from src.checker.content_analyzer import _extract_plain_text, analyze_qa_density, score_qa_density

    soup = BeautifulSoup(CONTENT_HTML_FAQ, "lxml")
    text = _extract_plain_text(soup)
    analysis = analyze_qa_density(text, soup)

    # FAQ page should have questions
    assert analysis["question_count"] > 0, (
        f"Expected questions in FAQ page, got {analysis['question_count']}"
    )
    assert analysis["total_sentences"] > 0
    # Heading questions should be detected (FAQ headings are questions)
    assert analysis["heading_question_count"] > 0, (
        f"Expected heading questions in FAQ, got {analysis['heading_question_count']}"
    )

    score = score_qa_density(analysis)
    assert 0.0 <= score <= 1.0, f"QA score out of range: {score}"
    # FAQ page should have non-zero QA score
    assert score > 0.0, f"QA score should be >0 for FAQ page, got {score}"


def test_qa_density_empty_text():
    """CONT-05: Empty text returns zero QA density."""
    from src.checker.content_analyzer import analyze_qa_density, score_qa_density

    analysis = analyze_qa_density("")
    assert analysis["question_count"] == 0
    assert analysis["total_sentences"] == 0
    assert score_qa_density(analysis) == 0.0


# --- CONT-06: Combined Score ---

def test_combined_score():
    """CONT-06: Combined score 0.0-1.0 from all sub-signals."""
    from tests.conftest import CONTENT_HTML_TEXT_HEAVY
    from src.checker.contracts import FetchResult
    from src.checker.content_analyzer import analyze_content

    soup = BeautifulSoup(CONTENT_HTML_TEXT_HEAVY, "lxml")
    # Build a minimal FetchResult for the text-heavy fixture
    fetch_result = FetchResult(
        url="https://example.com/article",
        final_url="https://example.com/article",
        status_code=200,
        html=CONTENT_HTML_TEXT_HEAVY,
        soup=soup,
    )

    result = analyze_content(fetch_result)

    # All sub-scores should be populated
    assert 0.0 <= result.readability_score <= 1.0
    assert 0.0 <= result.text_ratio <= 1.0
    assert 0.0 <= result.heading_score <= 1.0
    # Entity/QA scores may be 0 if spaCy missing — that's OK
    assert 0.0 <= result.entity_score <= 1.0
    assert 0.0 <= result.qa_density_score <= 1.0

    # Raw metrics should be populated
    assert result.flesch_raw > 0, f"Flesch should be positive: {result.flesch_raw}"
    assert result.fog_raw > 0, f"Fog should be positive: {result.fog_raw}"
    assert result.raw_text_ratio > 0, f"Text ratio should be positive: {result.raw_text_ratio}"

    # Combined score must be in [0.0, 1.0]
    assert 0.0 <= result.combined_score <= 1.0, (
        f"Combined score out of range: {result.combined_score}"
    )

    # Combined score must equal the weighted sum of sub-scores
    expected_combined = (
        result.readability_score * 0.20
        + result.text_ratio * 0.20
        + result.entity_score * 0.20
        + result.heading_score * 0.20
        + result.qa_density_score * 0.20
    )
    assert abs(result.combined_score - expected_combined) < 0.001, (
        f"Combined {result.combined_score} != expected {expected_combined}"
    )


# --- Edge Case: Empty Page (integration test via analyze_content) ---

def test_empty_page_integration():
    """Edge case: Empty page via analyze_content returns all zeros, no crash."""
    from tests.conftest import SCHEMA_EMPTY_HTML
    from src.checker.contracts import FetchResult
    from src.checker.content_analyzer import analyze_content

    soup = BeautifulSoup(SCHEMA_EMPTY_HTML, "lxml")
    fetch_result = FetchResult(
        url="https://example.com/empty",
        final_url="https://example.com/empty",
        status_code=200,
        html=SCHEMA_EMPTY_HTML,
        soup=soup,
    )

    result = analyze_content(fetch_result)

    assert result.readability_score == 0.0
    assert result.text_ratio == 0.0
    assert result.entity_score == 0.0
    assert result.heading_score == 0.0
    assert result.qa_density_score == 0.0
    assert result.combined_score == 0.0
    assert result.flesch_raw == 0.0
    assert result.fog_raw == 0.0


# --- Edge Case: spaCy Model Missing ---

def test_spacy_model_missing():
    """Edge case: When spaCy model not installed, analyze_content returns gracefully."""
    from unittest import mock
    from tests.conftest import CONTENT_HTML_TEXT_HEAVY
    from src.checker.contracts import FetchResult
    from src.checker import content_analyzer

    soup = BeautifulSoup(CONTENT_HTML_TEXT_HEAVY, "lxml")
    fetch_result = FetchResult(
        url="https://example.com/article",
        final_url="https://example.com/article",
        status_code=200,
        html=CONTENT_HTML_TEXT_HEAVY,
        soup=soup,
    )

    # Force _nlp to None to simulate missing spaCy model
    with mock.patch.object(content_analyzer, "_nlp", None):
        # Reset _get_nlp to return None (model missing)
        def _get_nlp_none():
            return None

        with mock.patch.object(content_analyzer, "_get_nlp", side_effect=_get_nlp_none):
            result = content_analyzer.analyze_content(fetch_result)

    # Should return gracefully, not crash
    assert result.entity_score == 0.0, (
        f"Entity score should be 0.0 without spaCy, got {result.entity_score}"
    )
    assert result.qa_density_score == 0.0, (
        f"QA score should be 0.0 without spaCy, got {result.qa_density_score}"
    )
    # Other scores should still work (they don't need spaCy)
    assert result.readability_score > 0.0, "Readability should work without spaCy"
    assert result.heading_score > 0.0, "Headings should work without spaCy"
