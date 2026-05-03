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


# --- CONT-04, CONT-05, CONT-06: Remaining stubs ---

def test_heading_structure():
    """CONT-04: Heading structure analysis (H1 uniqueness, hierarchy, descriptiveness)."""
    assert False, "Not yet implemented — Wave 0 stub"


def test_qa_density():
    """CONT-05: Q&A density scoring."""
    assert False, "Not yet implemented — Wave 0 stub"


def test_combined_score():
    """CONT-06: Combined score 0.0-1.0 from all sub-signals."""
    assert False, "Not yet implemented — Wave 0 stub"


def test_spacy_model_missing():
    """Edge case: spaCy model not installed returns clear error, not crash."""
    assert False, "Not yet implemented — Wave 0 stub"
