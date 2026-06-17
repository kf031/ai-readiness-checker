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

import textstat
from bs4 import BeautifulSoup

from checker.contracts import ContentAnalysis, FetchResult

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
        except Exception:
            logger.warning(
                "spaCy model 'en_core_web_sm' could not be loaded. "
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


# ---------------------------------------------------------------------------
# CONT-04: Heading structure analysis
# ---------------------------------------------------------------------------

def analyze_headings(soup: BeautifulSoup) -> dict:
    """Analyze heading structure from parsed HTML.

    Returns dict with:
        h1_count, h2_count, h3_count: int counts
        h1_unique: True if exactly 1 H1
        hierarchy_violations: count of H3s present when no H2s exist
        descriptive_count: number of headings with >3 words
        total_headings: sum of all h1/h2/h3 elements
        heading_texts: list of (tag_name, text) tuples for debug/display
    """
    import html as html_mod

    headings = soup.find_all(["h1", "h2", "h3"])

    h1s = [h for h in headings if h.name == "h1"]
    h2s = [h for h in headings if h.name == "h2"]
    h3s = [h for h in headings if h.name == "h3"]

    # H1 uniqueness: exactly 1 is ideal
    h1_unique = len(h1s) == 1

    # Hierarchy: H3 should not appear without H2 in the document
    hierarchy_violations = 0
    if h3s and not h2s:
        hierarchy_violations = len(h3s)

    # Descriptiveness: heading text > 3 words
    descriptive_count = 0
    heading_texts = []
    for h in headings:
        text = html_mod.unescape(h.get_text(strip=True))
        heading_texts.append((h.name, text))
        word_count = len(text.split())
        if word_count > 3:
            descriptive_count += 1

    return {
        "h1_count": len(h1s),
        "h2_count": len(h2s),
        "h3_count": len(h3s),
        "h1_unique": h1_unique,
        "hierarchy_violations": hierarchy_violations,
        "descriptive_count": descriptive_count,
        "total_headings": len(headings),
        "heading_texts": heading_texts,
    }


def score_headings(analysis: dict) -> float:
    """Score heading structure 0.0-1.0 from analysis dict.

    Components (equally weighted):
        - H1 uniqueness: 1.0 for exactly 1, 0.5 for 0, 0.0 for >1
        - Hierarchy: 1.0 if no violations, 0.0 if any H3-without-H2 violations
        - Descriptiveness: proportion of headings with >3 words

    Returns 0.0 if total_headings is 0.
    """
    total = analysis["total_headings"]
    if total == 0:
        return 0.0

    # H1 score
    if analysis["h1_unique"]:
        h1_score = 1.0
    elif analysis["h1_count"] == 0:
        h1_score = 0.5
    else:
        h1_score = 0.0

    # Hierarchy score
    hier_score = 0.0 if analysis["hierarchy_violations"] > 0 else 1.0

    # Descriptive score
    desc_score = analysis["descriptive_count"] / total

    return (h1_score + hier_score + desc_score) / 3.0


# ---------------------------------------------------------------------------
# CONT-05: Q&A density
# ---------------------------------------------------------------------------

QUESTION_WORDS = {
    "who", "what", "when", "where", "why", "how",
    "which", "whose", "whom", "can", "could", "would",
    "should", "is", "are", "was", "were", "do", "does",
    "did", "has", "have", "had", "will", "shall", "may",
}


def _is_question(sentence_text: str) -> bool:
    """Detect if a sentence is a question.

    Uses simple string operations (not regex) to avoid ReDoS risk
    per threat model T-4-05. Checks:
        1. Sentence ends with '?'
        2. Sentence starts with a question word and is long enough
           to not be a false positive (e.g., "Can" alone).
    """
    text = sentence_text.strip()
    if not text:
        return False
    if text.endswith("?"):
        return True
    # Check for question-word start, but only for meaningful-length text
    # to avoid "Is." or "Do." false positives
    first_word = text.split()[0].lower().rstrip(",;:")
    if first_word in QUESTION_WORDS and len(text) > 10:
        return True
    return False


def analyze_qa_density(text: str, soup: BeautifulSoup | None = None) -> dict:
    """Analyze Q&A density from plain text and optional heading structure.

    Detects question sentences via _is_question() and counts the
    immediately following sentence as an answer for each question.

    When soup is provided, also runs _is_question() on heading text.
    Heading questions contribute to the question count with 0.5 weight
    per planner discretion (avoiding double-counting bias against
    sentence-level questions).

    Args:
        text: Plain text string to analyze.
        soup: Optional BeautifulSoup tree for heading question detection.

    Returns dict with:
        question_count, answer_count, total_sentences,
        heading_question_count, score.
    """
    if not text.strip():
        return {
            "question_count": 0,
            "answer_count": 0,
            "total_sentences": 0,
            "heading_question_count": 0,
            "score": 0.0,
        }

    nlp = _get_nlp()
    if nlp is not None:
        doc = nlp(text)
        sentences = [s.text.strip() for s in doc.sents if s.text.strip()]
    else:
        # Fallback: simple sentence splitting without spaCy
        import re
        raw = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in raw if s.strip()]

    # Detect sentence-level questions
    question_indices = []
    for i, sent in enumerate(sentences):
        if _is_question(sent):
            question_indices.append(i)

    # Count sentences that directly follow a question as "answers"
    answer_count = 0
    for qi in question_indices:
        if qi + 1 < len(sentences):
            answer_count += 1

    # Detect heading-level questions (weighted at 0.5)
    heading_question_count = 0
    if soup is not None:
        headings = soup.find_all(["h1", "h2", "h3"])
        for h in headings:
            heading_text = h.get_text(strip=True)
            if _is_question(heading_text):
                heading_question_count += 1

    return {
        "question_count": len(question_indices),
        "answer_count": answer_count,
        "total_sentences": len(sentences),
        "heading_question_count": heading_question_count,
    }


def score_qa_density(analysis: dict) -> float:
    """Score Q&A density 0.0-1.0.

    Uses the ratio of QA pairs to total sentences with a 0.10 ceiling.
    Heading questions (weighted at 0.5) are merged into the question
    count for the final ratio.

    A page where 10%+ of sentence pairs are QA scores the maximum 1.0.
    """
    total = analysis["total_sentences"]
    if total == 0:
        return 0.0

    # Sentence-level QA pairs
    pair_count = analysis["answer_count"]
    # Heading questions weighted at 0.5
    heading_qa = analysis.get("heading_question_count", 0) * 0.5

    effective_pairs = pair_count + heading_qa
    ratio = effective_pairs / total
    return min(ratio / 0.10, 1.0)


# ---------------------------------------------------------------------------
# CONT-06: Combined content score
# ---------------------------------------------------------------------------

# Equal weighting for all 5 sub-signals per planner discretion.
# No requirements specify per-signal weights (unlike SCORE-01).
# Simplest defensible default — makes each sub-signal equally important.
SUB_SIGNAL_WEIGHTS = {
    "readability": 0.20,
    "text_ratio": 0.20,
    "entities": 0.20,
    "headings": 0.20,
    "qa_density": 0.20,
}


def compute_combined_score(
    readability: float,
    text_ratio: float,
    entities: float,
    headings: float,
    qa_density: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Compute weighted combined content quality score 0.0-1.0.

    Default weights are equal (0.2 each). All sub-scores must already
    be in 0.0-1.0 range. Result is clamped to [0.0, 1.0] per T-4-06.
    """
    w = weights if weights is not None else SUB_SIGNAL_WEIGHTS

    combined = (
        readability * w["readability"]
        + text_ratio * w["text_ratio"]
        + entities * w["entities"]
        + headings * w["headings"]
        + qa_density * w["qa_density"]
    )

    return min(max(combined, 0.0), 1.0)


# ---------------------------------------------------------------------------
# Public API: single entry point for Phase 4
# ---------------------------------------------------------------------------

def analyze_content(fetch_result: FetchResult) -> ContentAnalysis:
    """Analyze content quality from a fetched page and return scored result.

    This is the single public entry point for Phase 4.
    Consumed by Phase 5 scorer for the content component (35% weight).

    Pipeline:
        1. Extract plain text from pre-parsed HTML (FetchResult.soup)
        2. Score readability via textstat (CONT-01)
        3. Score content-to-HTML ratio (CONT-02)
        4. Extract and score named entities via spaCy (CONT-03)
        5. Analyze and score heading structure (CONT-04)
        6. Analyze and score Q&A density (CONT-05)
        7. Compute weighted combined score (CONT-06)

    Args:
        fetch_result: FetchResult from Phase 1 crawler.
            Reads .url, .html, and .soup.

    Returns:
        ContentAnalysis with all sub-scores, raw metrics, and combined score.

    Edge cases handled:
        - Empty page text: all scores 0.0, no crash
        - spaCy model missing: entity and QA scores 0.0 with log warning
        - No headings: heading score 0.0 (not a crash)
        - Very long text: truncated to 1MB before NLP processing
    """
    url = fetch_result.url
    html = fetch_result.html
    soup = fetch_result.soup

    # Step 1: Extract text
    plain_text = _extract_plain_text(soup)

    # Guard: empty page returns all zeros
    if not plain_text.strip():
        return ContentAnalysis(
            url=url,
            readability_score=0.0,
            text_ratio=0.0,
            entity_score=0.0,
            heading_score=0.0,
            qa_density_score=0.0,
            flesch_raw=0.0,
            fog_raw=0.0,
            raw_text_ratio=0.0,
            entities={},
            heading_analysis={},
            qa_analysis={"question_count": 0, "answer_count": 0,
                         "total_sentences": 0, "heading_question_count": 0,
                         "score": 0.0},
            combined_score=0.0,
        )

    # CONT-01: Readability
    flesch_raw, fog_raw, readability_score = score_readability(plain_text)

    # CONT-02: Text ratio
    raw_text_ratio, text_ratio_score = score_text_ratio(plain_text, html)

    # CONT-03: Entities
    entities = extract_entities(plain_text)
    entity_score = score_entities(entities)

    # CONT-04: Headings
    heading_analysis = analyze_headings(soup)
    heading_score = score_headings(heading_analysis)

    # CONT-05: QA density
    qa_analysis = analyze_qa_density(plain_text, soup)
    qa_density_score = score_qa_density(qa_analysis)
    qa_analysis["score"] = qa_density_score

    # CONT-06: Combined score
    combined_score = compute_combined_score(
        readability_score,
        text_ratio_score,
        entity_score,
        heading_score,
        qa_density_score,
    )

    return ContentAnalysis(
        url=url,
        readability_score=readability_score,
        text_ratio=text_ratio_score,
        entity_score=entity_score,
        heading_score=heading_score,
        qa_density_score=qa_density_score,
        flesch_raw=flesch_raw,
        fog_raw=fog_raw,
        raw_text_ratio=raw_text_ratio,
        entities=entities,
        heading_analysis=heading_analysis,
        qa_analysis=qa_analysis,
        combined_score=combined_score,
    )
