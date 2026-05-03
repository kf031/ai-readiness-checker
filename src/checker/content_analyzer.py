"""
Content quality analysis for AI readiness scoring.

Analyzes page text across five sub-signals: readability (Flesch Reading Ease
+ Gunning Fog Index via textstat), content-to-HTML ratio, named entity
extraction (spaCy en_core_web_sm), heading structure analysis, and Q&A
density scoring. All sub-signals produce individual 0.0-1.0 scores that
combine into a single content quality score.

Covers: CONT-01 (readability), CONT-02 (text ratio), CONT-03 (entities),
CONT-04 (headings), CONT-05 (QA density), CONT-06 (combined score).

Dependencies:
    - textstat 0.7.13: readability metrics (Flesch, Fog)
    - spaCy 3.8.14 + en_core_web_sm: sentence segmentation, NER
    - BeautifulSoup4 4.14.3: HTML text extraction (via FetchResult.soup)

Planner Decisions (no CONTEXT.md — per Claude's discretion per RESEARCH.md):
    1. Sub-signal weighting for CONT-06: equal weight (0.2 each for 5 signals).
       Simplest defensible default. No requirements specify per-signal weights.
    2. Heading question detection for CONT-05: heading-level questions
       included in QA count with 0.5 weight per heading question, merged
       with sentence-level questions for final ratio calculation.
    3. Non-English pages: not gated. Accept English-only for v1. Document
       that non-English scores may be misleading (spaCy English model).
"""

import logging
from datetime import datetime, timezone

import textstat
from bs4 import BeautifulSoup

from src.checker.contracts import ContentAnalysis, FetchResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy spaCy model loading
# ---------------------------------------------------------------------------

_nlp = None

# Maximum plain text length before NLP processing (1MB cap per RESEARCH.md
# threat model T-4-01: prevents CPU exhaustion on extremely long pages)
MAX_TEXT_LENGTH = 1_000_000

def _get_nlp():
    """Lazy-load the spaCy English model. Thread-safe through GIL.

    Returns the loaded spaCy Language object, or None if the model
    is not installed. Callers must handle the None case gracefully.
    """
    global _nlp
    if _nlp is None:
        try:
            _nlp = __import__("spacy").load("en_core_web_sm")
        except OSError:
            logger.warning(
                "spaCy model 'en_core_web_sm' not found. "
                "Install with: python -m spacy download en_core_web_sm. "
                "Entity extraction and QA density scoring will return 0.0."
            )
            _nlp = None
    return _nlp


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def _extract_plain_text(soup: BeautifulSoup) -> str:
    """Extract visible plain text from pre-parsed BeautifulSoup tree.

    Uses separator=" " to prevent word concatenation between sibling
    text nodes (avoids "HeadingParagraph" -> "Heading Paragraph" bug).
    strip=True removes leading/trailing whitespace from each text node.
    """
    text = soup.get_text(separator=" ", strip=True)
    # Cap at 1MB to prevent CPU exhaustion in NLP processing (T-4-01)
    if len(text) > MAX_TEXT_LENGTH:
        logger.warning(
            "Plain text length %d exceeds %d cap; truncating.",
            len(text), MAX_TEXT_LENGTH,
        )
        text = text[:MAX_TEXT_LENGTH]
    return text


# ---------------------------------------------------------------------------
# CONT-01: Readability scoring
# ---------------------------------------------------------------------------

def score_readability(text: str) -> tuple[float, float, float]:
    """Compute readability sub-scores and combined score.

    Returns (flesch_raw, fog_raw, combined_0_to_1).

    Flesch Reading Ease (0-100+, higher = easier):
        Normalized as max(flesch, 0) / 100, clamped to 1.0.
        Negatives are clamped to 0 (occurs on very dense academic text).

    Gunning Fog Index (grade level, lower = easier):
        Inverted: 1.0 - min(fog / 20.0, 1.0).
        Fog 6 (easy) = ~0.70; Fog 17 (very hard) = ~0.15.

    Combined score is the average of the two normalized scores.
    """
    if not text.strip():
        return (0.0, 0.0, 0.0)

    flesch = textstat.flesch_reading_ease(text)
    fog = textstat.gunning_fog(text)

    # Normalize Flesch: clamp negative, scale to 0-1
    flesch_norm = max(flesch, 0.0) / 100.0
    flesch_norm = min(flesch_norm, 1.0)

    # Normalize Fog: invert so higher = more readable
    fog_norm = 1.0 - min(fog / 20.0, 1.0)

    combined = (flesch_norm + fog_norm) / 2.0
    return (flesch, fog, combined)


# ---------------------------------------------------------------------------
# CONT-02: Content-to-HTML ratio
# ---------------------------------------------------------------------------

def score_text_ratio(plain_text: str, html: str) -> tuple[float, float]:
    """Compute content-to-HTML ratio and normalized score.

    Returns (raw_ratio, score_0_to_1).

    Raw ratio = len(plain_text) / len(html).
    Typical web pages range from 0.05 (thin) to 0.30 (text-heavy).
    Score is linear from 0 to 0.25, capped at 1.0.

    Returns (0.0, 0.0) when html is empty (avoids division by zero).
    """
    if not html:
        return (0.0, 0.0)

    ratio = len(plain_text) / len(html)
    score = min(ratio / 0.25, 1.0)
    return (ratio, score)


# ---------------------------------------------------------------------------
# CONT-03: Named entity extraction
# ---------------------------------------------------------------------------

TARGET_ENTITIES = {"ORG", "PRODUCT", "GPE", "PERSON"}


def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract named entities of target types from plain text.

    Args:
        text: Plain text string to analyze.

    Returns:
        Dict mapping entity type (ORG, PRODUCT, GPE, PERSON) to list
        of entity text values. Returns empty dict if text is empty
        or spaCy model is not installed.
    """
    if not text.strip():
        return {}

    nlp = _get_nlp()
    if nlp is None:
        return {}

    doc = nlp(text)

    entities: dict[str, list[str]] = {}
    for ent in doc.ents:
        if ent.label_ in TARGET_ENTITIES:
            entities.setdefault(ent.label_, []).append(ent.text)

    return entities


def score_entities(entities: dict[str, list[str]]) -> float:
    """Score entity presence/diversity 0.0-1.0.

    Each of the 4 target entity types (ORG, PRODUCT, GPE, PERSON)
    that has at least one entity contributes 0.25 to the score.
    """
    if not entities:
        return 0.0
    types_found = sum(1 for t in TARGET_ENTITIES if t in entities)
    return types_found / 4.0
