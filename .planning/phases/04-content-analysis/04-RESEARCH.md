# Phase 4: Content Analysis - Research

**Researched:** 2026-05-03
**Domain:** NLP-based web page content quality analysis (readability, named entities, heading structure, Q&A density)
**Confidence:** HIGH

## Summary

Phase 4 analyzes the textual content of a fetched web page across five sub-signals: readability (Flesch Reading Ease + Gunning Fog Index via textstat), content-to-HTML ratio, named entity extraction (spaCy en_core_web_sm), heading structure analysis, and Q&A density scoring. All sub-signals produce individual 0.0-1.0 scores that combine into a single content quality score.

The phase introduces two new dependencies to the project: textstat (0.7.13, already declared in pyproject.toml) and spaCy (3.8.14, already declared). The spaCy model `en_core_web_sm` must be downloaded separately as a post-install step (not pip-installable). The content analyzer follows the Phase 3 schema_analyzer pattern: a single public entry point `analyze_content(fetch_result) -> ContentAnalysis`, with internal helper functions for each sub-signal.

A key architectural insight: the content analyzer should NOT use `FetchResult.soup` for text extraction. Using `soup.get_text(separator=" ")` is the standard approach, but because `.soup` is already a pre-parsed BeautifulSoup tree (lxml parser), the analyzer can either use it or fall back to parsing `.html` if `.soup` is unavailable. Using `.soup` directly is preferred to avoid double-parsing.

**Primary recommendation:** Use `soup.get_text(separator=" ", strip=True)` for plain text extraction and process it through textstat and spaCy. Build scoring functions per sub-signal with clearly documented normalization thresholds. Lazy-load spaCy model at function-call time (not import time) to keep the module import fast.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTML-to-text extraction | API / Backend | — | BeautifulSoup text extraction from pre-parsed HTML tree |
| Readability scoring (Flesch, Fog) | API / Backend | — | Pure computation on extracted plain text |
| Content-to-HTML ratio | API / Backend | — | Simple string length computation; no external service |
| Named entity recognition | API / Backend | — | spaCy runs entirely in-process; no network calls |
| Heading structure analysis | API / Backend | — | HTML DOM traversal on pre-parsed tree |
| Q&A density scoring | API / Backend | — | Sentence-level NLP on extracted text |
| Combined content score | API / Backend | — | Weighted aggregation of sub-signal scores |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| textstat | 0.7.13 | Readability metrics (Flesch Reading Ease, Gunning Fog Index, sentence/word/character counts) | Most popular Python readability library; 1.8k GitHub stars; MIT license; actively maintained |
| spaCy | 3.8.14 | Industrial-strength NLP pipeline (sentence segmentation, NER) | Gold standard for Python NLP; 30k+ GitHub stars; MIT license; en_core_web_sm is the standard lightweight English model |
| en_core_web_sm | Latest (download) | spaCy English pipeline: tok2vec, tagger, parser, senter, ner | Smallest English model (13-15 MB); covers all required entity types (ORG, PRODUCT, GPE, PERSON); fast load time |
| BeautifulSoup4 | 4.14.3 | HTML parsing and text extraction | Already in project (Phase 1); `soup.get_text()` is the standard API for extracting visible text |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | — | Regex for question detection (sentence-ending `?` and question words) | CONT-05 Q&A density; no external dependency needed |
| html (stdlib) | — | HTML entity decoding (unescape `&amp;` etc. in heading text) | CONT-04 heading descriptiveness check |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| textstat | nltk + custom formulas | NLTK is heavier; textstat is purpose-built for readability and simpler |
| spaCy en_core_web_sm | en_core_web_trf (transformer) | Trf model is 400+ MB and 10x slower; overkill for entity counting on single pages |
| spaCy | Stanza (Stanford NLP) | Stanza requires Java/PyTorch; heavier dependency; spaCy is lighter and more Pythonic |

**Installation:**
```bash
pip install "textstat>=0.7,<1.0" "spacy>=3.7,<4.0"
python -m spacy download en_core_web_sm
```

**Version verification:**
- textstat 0.7.13 [VERIFIED: PyPI registry] — published 2025-08-09
- spaCy 3.8.14 [VERIFIED: PyPI registry] — published 2025-04-15
- en_core_web_sm 3.8.0 [CITED: spaCy models — version corresponds to spaCy 3.8.x]
- BeautifulSoup4 4.14.3 [VERIFIED: pip list on local machine]

## Architecture Patterns

### System Architecture Diagram

```
FetchResult (from Phase 1)
    |
    |-- .soup (BeautifulSoup) -- or -- .html (raw string) --[parse]-->
    |
    v
+--------------------------------------------------+
|              Content Analyzer                     |
|                                                   |
|  Public entry: analyze_content(fetch_result)      |
|                                                   |
|  1. Extract plain text from HTML                  |
|     soup.get_text(separator=" ", strip=True)      |
|     |                                             |
|     +---> CONT-02: content-to-HTML ratio          |
|     |     ratio = len(plain_text) / len(html)     |
|     |     score_text_to_html(ratio) -> 0.0-1.0    |
|     |                                             |
|     +---> CONT-01: readability scoring            |
|     |     textstat.flesch_reading_ease(text)      |
|     |     textstat.gunning_fog(text)              |
|     |     score_readability(flesch, fog) -> 0-1   |
|     |                                             |
|     +---> CONT-03: named entity extraction        |
|     |     nlp = load_spacy_model()  [lazy]        |
|     |     doc = nlp(plain_text)                   |
|     |     entities = {ent.label_: ent.text        |
|     |                  for ent in doc.ents}       |
|     |     filter: ORG, PRODUCT, GPE, PERSON       |
|     |     score_entities(entities) -> 0.0-1.0     |
|     |                                             |
|     +---> CONT-05: Q&A density (uses doc.sents)   |
|     |     questions = detect_questions(sentences) |
|     |     answers = count_following_sentences()   |
|     |     score_qa_density(q, a, total) -> 0-1    |
|     |                                             |
|  2. Heading analysis (direct DOM)  CONT-04        |
|     soup.find_all(['h1', 'h2', 'h3'])             |
|     h1_uniqueness, hierarchy, descriptiveness      |
|     score_headings(...) -> 0.0-1.0                |
|                                                   |
|  3. Combined score  CONT-06                       |
|     weighted average of all 5 sub-scores          |
|     -> ContentAnalysis dataclass                  |
+--------------------------------------------------+
    |
    v
ContentAnalysis (output contract)
    .readability_score, .text_ratio, .entity_score
    .heading_score, .qa_density_score
    .combined_score (0.0-1.0)
    .raw metrics (flesch, fog, entities, etc.)
```

### Recommended Project Structure

```
src/checker/
├── content_analyzer.py    # NEW: analyze_content() + 5 sub-scoring functions
├── contracts.py           # MODIFY: add ContentAnalysis dataclass
└── __init__.py            # MODIFY: export ContentAnalysis + analyze_content

tests/
├── conftest.py            # MODIFY: add CONTENT_HTML_* fixtures
└── test_content.py        # NEW: CONT-01 through CONT-06 test coverage
```

### Pattern 1: Lazy spaCy Model Loading

**What:** spaCy models are loaded at first use, not at import time. This keeps the module cheap to import (important for CLI startup) while paying the ~1s load cost only when analysis actually runs.

**When to use:** Any module that imports spaCy. The model load is the expensive part (~1-2 seconds for en_core_web_sm), not the import.

**Example:**
```python
# Source: spaCy best practices, project pattern from Phase 3 extruct usage
import spacy

_nlp = None  # Module-level cache

def _get_nlp():
    """Lazy-load the spaCy English model. Thread-safe through GIL."""
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp
```

### Pattern 2: Plain Text Extraction from BeautifulSoup

**What:** Extract visible text from pre-parsed HTML using `soup.get_text()` with separator for word boundary preservation. This is the standard and most reliable way to get human-readable content from HTML.

**When to use:** Whenever you need the text content of a page without markup.

**Example:**
```python
# Source: BeautifulSoup4 official docs — get_text() method
# soup is FetchResult.soup (pre-parsed lxml tree from Phase 1)
plain_text = soup.get_text(separator=" ", strip=True)
# separator=" " prevents word concatenation (e.g., "HeadingParagraph" -> "Heading Paragraph")
# strip=True removes leading/trailing whitespace from each text node
```

### Pattern 3: Scoring Function Decomposition

**What:** Each sub-signal gets its own pure scoring function: input data in, 0.0-1.0 float out. The top-level `analyze_content()` orchestrates extraction and delegates to these functions.

**When to use:** Following the Phase 3 pattern (`extract_structured_data`, `collect_schema_types`, `compute_schema_score`). Makes each sub-signal independently testable.

**Example:**
```python
# Source: Phase 3 schema_analyzer.py pattern
def score_readability(flesch: float, fog: float) -> float:
    """Normalize Flesch (0-100) and Fog (inverted grade) to 0.0-1.0."""
    ...

def score_text_ratio(plain_text_len: int, html_len: int) -> float:
    """Content-to-HTML ratio normalized to 0.0-1.0."""
    ...

def score_entities(entities: dict[str, list[str]]) -> float:
    """Entity diversity score 0.0-1.0."""
    ...

def analyze_content(fetch_result: FetchResult) -> ContentAnalysis:
    """Single public entry point. Orchestrates extraction + scoring."""
    ...
```

### Anti-Patterns to Avoid

- **Eager spaCy model load at import time:** Slows down `import checker` by 1-2 seconds even when content analysis is not used. Lazy-load instead.
- **Double-parsing HTML:** Do not call `BeautifulSoup(fetch_result.html, "lxml")` again. The `FetchResult.soup` field already has the parsed tree.
- **Using soup.get_text() without separator:** Default behavior joins text nodes with no space, producing concatenated words like "HeadingThis iscontent". Always use `separator=" "`.
- **Assuming spaCy model is always installed:** Wrap the `_get_nlp()` call with a clear error message if the model is not found. Users need to run `python -m spacy download en_core_web_sm`.
- **Hardcoding scoring thresholds without documentation:** Every normalization threshold (e.g., "Flesch score of 60 maps to 0.7") must be documented with the rationale in code comments.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Readability scores (Flesch, Fog) | Custom syllable counting, word/sentence tokenization | `textstat.flesch_reading_ease()`, `textstat.gunning_fog()` | Textstat handles 12+ readability formulas with language-specific syllable dictionaries (Pyphen, cmudict). Writing syllable counting from scratch for English alone requires handling silent 'e', vowel teams, diphthongs, etc. |
| Named entity recognition | Regex-based entity extraction, keyword matching | spaCy `en_core_web_sm` NER pipeline | Regex cannot distinguish "Apple" (ORG) from "apple" (fruit). spaCy uses a trained statistical model with contextual disambiguation. |
| Sentence segmentation | Splitting on `.`, `!`, `?` with regex | `doc.sents` from spaCy | Periods in abbreviations ("Dr.", "U.S.", "etc."), decimal numbers, and initials break naive splitting. spaCy's sentencizer is trained on web text. |

**Key insight:** NLP is deceptively complex. Seemingly simple tasks (sentence splitting, word counting, syllable counting) have hundreds of edge cases that libraries like textstat and spaCy have solved over years of development.

## Runtime State Inventory

> Skipped — this is a greenfield content analysis module. No rename/refactor/migration involved.

## Common Pitfalls

### Pitfall 1: spaCy Model Not Downloaded

**What goes wrong:** `spacy.load("en_core_web_sm")` raises `OSError: [E050] Can't find model 'en_core_web_sm'`.

**Why it happens:** spaCy models are separate downloads, not pip packages. `pip install spacy` does not install any models.

**How to avoid:** Lazy-load with a try/except that catches the OSError and prints a clear message: "spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm". Return a ContentAnalysis with entity score of 0.0 and a warning note.

**Warning signs:** The first call to `analyze_content()` crashes. The module imports fine but fails at runtime.

### Pitfall 2: Flesch Reading Ease Can Be Negative

**What goes wrong:** Textstat's `flesch_reading_ease()` can return negative values for very difficult text (long sentences, many polysyllabic words). Normalizing with `score / 100` produces negative scores.

**Why it happens:** The Flesch formula has no lower bound. Academic papers with 40+ word sentences and heavy jargon can score below 0.

**How to avoid:** Clamp the Flesch score with `max(flesch, 0)` before normalizing to 0.0-1.0. Document the clamping boundary.

**Warning signs:** Negative readability scores on dense academic or legal content pages.

### Pitfall 3: get_text() Without separator Joins Words

**What goes wrong:** `soup.get_text()` (default) produces "HeadingParagraph textMore text" — words from adjacent elements concatenate without spaces.

**Why it happens:** BeautifulSoup's default separator is `""`. Text nodes from sibling elements run together.

**How to avoid:** Always use `soup.get_text(separator=" ", strip=True)`. The `separator=" "` inserts a space between text nodes. The `strip=True` removes leading/trailing whitespace from individual text pieces.

**Warning signs:** Word count from textstat is much lower than expected. Readability scores are abnormally poor. Text appears to have run-on words.

### Pitfall 4: Empty Pages Cause Division by Zero

**What goes wrong:** Pages with no visible text (SPAs, image-only pages, empty bodies) produce a plain text length of 0, leading to division by zero in readability formulas and zero-sentence errors in textstat.

**Why it happens:** Some pages are purely JavaScript shells with no server-rendered text content. The crawler fetches the initial HTML, not the JS-rendered DOM.

**How to avoid:** Guard clause at the top of `analyze_content()`: if `len(plain_text.strip()) == 0`, return a ContentAnalysis with all scores at 0.0 and a note that the page has no extractable text content.

**Warning signs:** `ZeroDivisionError`, `textstat` raising errors about 0 sentences, spaCy producing an empty doc.

### Pitfall 5: Gunning Fog Gets Worse with More Readable Text

**What goes wrong:** Gunning Fog returns a grade level — higher = harder to read. If you normalize it the same way as Flesch, you get inverted scoring.

**Why it happens:** Flesch is a "higher is better" score. Fog is a "lower is better" grade level. They need opposite normalization.

**How to avoid:** Normalize Fog as `1.0 - min(fog / 20.0, 1.0)` (invert it). A Fog score of 6 (easy) becomes ~0.70; a Fog score of 17 (very hard) becomes ~0.15. Document the 20.0 ceiling threshold (represents "post-graduate" level).

**Warning signs:** Highly readable pages score lower on Fog component than dense pages. Combined readability score doesn't track with intuition.

## Code Examples

Verified patterns from official sources:

### Readability Scoring (CONT-01)
```python
# Source: textstat PyPI page — flesch_reading_ease and gunning_fog signatures
# Source: textstat README — scoring functions API
import textstat

def score_readability(text: str) -> tuple[float, float, float]:
    """Compute readability sub-scores and combined score.
    
    Returns (flesch_raw, fog_raw, combined_0_to_1).
    """
    if not text.strip():
        return (0.0, 0.0, 0.0)
    
    flesch = textstat.flesch_reading_ease(text)
    fog = textstat.gunning_fog(text)
    
    # Normalize Flesch: 0-100 scale (clamp negatives), higher = better
    # 60+ is "Standard" readability; 90+ is "Very Easy"
    flesch_norm = max(flesch, 0.0) / 100.0
    flesch_norm = min(flesch_norm, 1.0)
    
    # Normalize Fog: grade level, invert so higher = better
    # Fog 6 = easy, Fog 12 = hard, Fog 17+ = very hard
    fog_norm = 1.0 - min(fog / 20.0, 1.0)
    
    combined = (flesch_norm + fog_norm) / 2.0
    return (flesch, fog, combined)
```

### Content-to-HTML Ratio (CONT-02)
```python
# Source: BeautifulSoup4 official docs — get_text() with separator
def score_text_ratio(plain_text: str, html: str) -> tuple[float, float]:
    """Compute content-to-HTML ratio and normalized score.
    
    Returns (raw_ratio, score_0_to_1).
    """
    if not html:
        return (0.0, 0.0)
    
    ratio = len(plain_text) / len(html)
    
    # Typical web pages: 0.05 (thin) to 0.30 (text-heavy)
    # Score: linear from 0 to 0.25 (capped)
    score = min(ratio / 0.25, 1.0)
    return (ratio, score)
```

### Named Entity Extraction (CONT-03)
```python
# Source: spaCy EntityRecognizer API docs — doc.ents, ent.label_
# Source: spaCy linguistic features docs — ORG, GPE, PERSON entity types
import spacy

_nlp = None

def _get_nlp():
    """Lazy-load spaCy model. Thread-safe through GIL."""
    global _nlp
    if _nlp is None:
        try:
            _nlp = spacy.load("en_core_web_sm")
        except OSError:
            raise OSError(
                "spaCy model 'en_core_web_sm' not found. "
                "Install with: python -m spacy download en_core_web_sm"
            )
    return _nlp

TARGET_ENTITIES = {"ORG", "PRODUCT", "GPE", "PERSON"}

def extract_entities(text: str) -> dict[str, list[str]]:
    """Extract named entities of target types.
    
    Returns dict like {"ORG": ["Apple", "Google"], "PERSON": ["Tim Cook"]}.
    """
    if not text.strip():
        return {}
    
    nlp = _get_nlp()
    doc = nlp(text)
    
    entities: dict[str, list[str]] = {}
    for ent in doc.ents:
        if ent.label_ in TARGET_ENTITIES:
            entities.setdefault(ent.label_, []).append(ent.text)
    
    return entities

def score_entities(entities: dict[str, list[str]]) -> float:
    """Score entity presence/diversity 0.0-1.0.
    
    Each of the 4 target types that has at least one entity adds 0.25.
    """
    if not entities:
        return 0.0
    types_found = sum(1 for t in TARGET_ENTITIES if t in entities)
    return types_found / 4.0
```

### Heading Structure Analysis (CONT-04)
```python
# Source: BeautifulSoup4 find_all() standard API
from bs4 import BeautifulSoup
import html as html_mod

def analyze_headings(soup: BeautifulSoup) -> dict:
    """Analyze heading structure from parsed HTML.
    
    Returns dict with h1_count, h2_count, h3_count, h1_unique (bool),
    hierarchy_violations (int), descriptive_count (int), total_headings (int).
    """
    headings = soup.find_all(['h1', 'h2', 'h3'])
    
    h1s = [h for h in headings if h.name == 'h1']
    h2s = [h for h in headings if h.name == 'h2']
    h3s = [h for h in headings if h.name == 'h3']
    
    # H1 uniqueness: exactly 1 is ideal
    h1_unique = len(h1s) == 1
    
    # Hierarchy: H3 should not appear without a preceding H2 in the same section
    # Simplified: check if H3 exists when H2 doesn't
    hierarchy_violations = 0
    if h3s and not h2s:
        hierarchy_violations = len(h3s)
    
    # Descriptiveness: heading text should be > 3 words
    descriptive_count = 0
    for h in headings:
        text = html_mod.unescape(h.get_text(strip=True))
        if len(text.split()) > 3:
            descriptive_count += 1
    
    return {
        "h1_count": len(h1s),
        "h2_count": len(h2s),
        "h3_count": len(h3s),
        "h1_unique": h1_unique,
        "hierarchy_violations": hierarchy_violations,
        "descriptive_count": descriptive_count,
        "total_headings": len(headings),
    }

def score_headings(analysis: dict) -> float:
    """Score heading structure 0.0-1.0 from analysis dict.
    
    Components:
    - H1 uniqueness: 1.0 if exactly 1, 0.5 if 0, 0.0 if >1
    - Hierarchy: 1.0 if no violations, 0.0 if violations
    - Descriptiveness: proportion of headings that are descriptive (>3 words)
    """
    total = analysis["total_headings"]
    
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
    desc_score = (
        analysis["descriptive_count"] / total if total > 0 else 0.0
    )
    
    return (h1_score + hier_score + desc_score) / 3.0
```

### Q&A Density (CONT-05)
```python
# Source: spaCy doc.sents API for sentence boundaries
# Source: Standard regex pattern for question detection
import re

QUESTION_WORDS = {"who", "what", "when", "where", "why", "how",
                  "which", "whose", "whom", "can", "could", "would",
                  "should", "is", "are", "was", "were", "do", "does",
                  "did", "has", "have", "had", "will", "shall", "may"}

def _is_question(sentence_text: str) -> bool:
    """Detect if a sentence is a question."""
    text = sentence_text.strip()
    if not text:
        return False
    # Ends with question mark
    if text.endswith("?"):
        return True
    # Starts with question word and contains no question mark ambiguity
    first_word = text.split()[0].lower().rstrip(",;:")
    if first_word in QUESTION_WORDS and len(text) > 10:
        return True
    return False

def analyze_qa_density(text: str) -> dict:
    """Analyze Q&A density from plain text.
    
    Returns dict with question_count, answer_count, total_sentences, score.
    """
    if not text.strip():
        return {"question_count": 0, "answer_count": 0,
                "total_sentences": 0, "score": 0.0}
    
    nlp = _get_nlp()
    doc = nlp(text)
    sentences = [s.text.strip() for s in doc.sents]
    
    question_indices = []
    for i, sent in enumerate(sentences):
        if _is_question(sent):
            question_indices.append(i)
    
    # Count sentences that directly follow a question as "answers"
    answer_count = 0
    for qi in question_indices:
        if qi + 1 < len(sentences):
            answer_count += 1
    
    return {
        "question_count": len(question_indices),
        "answer_count": answer_count,
        "total_sentences": len(sentences),
    }

def score_qa_density(analysis: dict) -> float:
    """Score Q&A density 0.0-1.0.
    
    Uses the ratio of QA pairs to total sentences, with a ceiling.
    A page where 10%+ of sentences are QA pairs scores 1.0.
    """
    total = analysis["total_sentences"]
    if total == 0:
        return 0.0
    
    pair_count = analysis["answer_count"]
    ratio = pair_count / total
    return min(ratio / 0.10, 1.0)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NLTK for tokenization + custom readability formulas | textstat library (wraps Pyphen/cmudict for syllables) | textstat 0.5+ (2020ish) | Fewer dependencies, more readability formulas, language support |
| Regex-based sentence splitting | spaCy's trained sentencizer | spaCy 2.0+ (2017) | Handles abbreviations, decimals, acronyms correctly |
| Manual entity keyword matching (e.g., "Inc.", "Corp.") | spaCy NER with contextual embeddings | spaCy 2.0+ (2017) | Context-aware: "Apple released..." vs "I ate an apple" |

**Deprecated/outdated:**
- NLTK's `sent_tokenize` for web text: spaCy's sentencizer is trained on more diverse text and handles web-specific patterns better
- Manual syllable counting: textstat uses Pyphen hyphenation dictionaries and cmudict pronunciation data, far more accurate than naive vowel-counting heuristics

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | en_core_web_sm NER labels include exactly PRODUCT, ORG, GPE, PERSON. The full 18-label set from spaCy docs was cited but not verified by loading the model locally. | Standard Stack | Low — these 4 labels are the canonical set from spaCy's OntoNotes 5 training. If PRODUCT is absent, CONT-03 entity types reduce to 3, and score weight per type increases from 0.25 to 0.33. |
| A2 | Flesch Reading Ease normalization ceiling of 100.0 and floor of 0.0 is appropriate for web content. | Code Examples | Medium — some web pages can score above 100 (very short words/sentences like children's content). Score would be artificially capped. Acceptable tradeoff since the goal is to flag poor readability, not precisely rank highly readable content. |
| A3 | Gunning Fog ceiling of 20.0 for normalization is appropriate (scores above 20 are "post-graduate"). | Code Examples | Low — Fog above 20 is rare for web content. If it occurs, the score floor is 0.0 which is semantically correct (extremely difficult text). |
| A4 | Content-to-HTML ratio ceiling of 0.25 maps to score 1.0. | Code Examples | Medium — some minimalist pages (e.g., plain text served as HTML) could exceed 0.25. Score caps at 1.0 regardless, which is acceptable. |
| A5 | Q&A density ceiling of 0.10 (10% of sentences as QA pairs) maps to score 1.0. | Code Examples | Medium — FAQ pages could have higher density. Ceiling means all "good" FAQ pages score the same (1.0), which is acceptable since the goal is detecting absence, not ranking abundance. |
| A6 | Heading hierarchy check (H3 without H2) is sufficient for hierarchy validation. A deeper check (e.g., H3 must appear after its parent H2 in DOM order) is not needed. | Code Examples | Low — standard SEO best practice focuses on the skip-level violation (H3 without H2). DOM-order checking would catch H3 appearing before its first H2, but this is an edge case for malformed pages. |

## Open Questions (RESOLVED)

1. **Combined sub-signal weighting for CONT-06**
   - What we know: CONT-06 requires a combined 0.0-1.0 score from all sub-signals
   - What's unclear: Whether all 5 sub-signals should be equally weighted (0.2 each) or some should carry more weight. The requirements do not specify weights for content sub-signals (unlike SCORE-01 which specifies per-module weights).
   - Recommendation: Use equal weighting (0.2 each for readability, text ratio, entities, headings, QA density) as the simplest defensible default. The planner should surface this for user confirmation. If the user has a preference (e.g., readability matters more than QA density), they can adjust.

2. **Heading question detection for QA density (CONT-05)**
   - What we know: CONT-05 mentions "question-style headings" as part of Q&A density
   - What's unclear: Whether heading questions should count as "questions" in addition to sentence-level questions, potentially double-counting if a heading is also the first sentence
   - Recommendation: Include heading-level question detection as a separate sub-count in the QA analysis, but weight heading questions at 0.5 to avoid dominating the score. Merge heading and sentence questions for the final ratio calculation.

3. **Non-English page handling**
   - What we know: The project uses `en_core_web_sm` (English model). No v1 requirement for multi-language support.
   - What's unclear: What happens when a non-English page is analyzed. spaCy will still process it but entity recognition quality degrades significantly. textstat has multi-language support but defaults to English.
   - Recommendation: Do not gate on language detection in v1. Accept that English is the primary target. Document that non-English pages may produce misleading scores. Add language detection (via `langdetect` or spaCy's `spacy-langdetect`) in v2.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | Runtime | Yes | 3.13.9 | — |
| pip | Package install | Yes | 25.2 | — |
| textstat | CONT-01 readability | No | — | Install via pip (in pyproject.toml) |
| spaCy | CONT-03 NER, CONT-05 sentence segmentation | No | — | Install via pip (in pyproject.toml) |
| en_core_web_sm | CONT-03 NER labels | No | — | Download via `python -m spacy download en_core_web_sm` |
| BeautifulSoup4 | CONT-02 text extraction, CONT-04 headings | Yes | 4.14.3 | — |
| lxml | BeautifulSoup parser | Yes | 6.0.2 | — |

**Missing dependencies with no fallback:**
- **textstat** — Must be installed. Can't do readability scoring without it.
- **spaCy** — Must be installed. Can't do NER or sentence segmentation without it.
- **en_core_web_sm** — Must be downloaded. Without it, CONT-03 and CONT-05 scoring degrades to 0.0 (graceful fallback possible but undesirable).

**Action required before Phase 4 execution:**
```bash
pip install "textstat>=0.7,<1.0" "spacy>=3.7,<4.0"
python -m spacy download en_core_web_sm
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | pyproject.toml (tool.pytest.ini_options) |
| Quick run command | `pytest tests/test_content.py -x` |
| Full suite command | `pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONT-01 | Readability scoring returns Flesch and Fog | unit | `pytest tests/test_content.py::test_readability_scoring -x` | No — Wave 0 |
| CONT-02 | Content-to-HTML ratio correctly computed | unit | `pytest tests/test_content.py::test_text_ratio -x` | No — Wave 0 |
| CONT-03 | Named entities extracted (ORG, PRODUCT, GPE, PERSON) | unit | `pytest tests/test_content.py::test_named_entities -x` | No — Wave 0 |
| CONT-04 | Heading structure analysis (H1 uniqueness, hierarchy, descriptiveness) | unit | `pytest tests/test_content.py::test_heading_structure -x` | No — Wave 0 |
| CONT-05 | Q&A density scoring | unit | `pytest tests/test_content.py::test_qa_density -x` | No — Wave 0 |
| CONT-06 | Combined score 0.0-1.0 from all sub-signals | unit | `pytest tests/test_content.py::test_combined_score -x` | No — Wave 0 |
| (Edge) | Empty page returns all zeros | unit | `pytest tests/test_content.py::test_empty_page -x` | No — Wave 0 |
| (Edge) | spaCy model not installed gracefully handled | unit | `pytest tests/test_content.py::test_spacy_model_missing -x` | No — Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_content.py -x`
- **Per wave merge:** `pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_content.py` — covers all 6 CONT-* requirements
- [ ] `tests/conftest.py` — add CONTENT_HTML_* fixtures (text-heavy HTML, FAQ-style HTML, thin HTML, no-heading HTML, multi-entity HTML)
- [ ] test_content.py test functions for each CONT requirement
- [ ] Framework install: `pip install "textstat>=0.7,<1.0" "spacy>=3.7,<4.0" && python -m spacy download en_core_web_sm`

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — no auth in content analysis |
| V3 Session Management | No | N/A |
| V4 Access Control | No | N/A |
| V5 Input Validation | Yes | Primary input is `FetchResult.html` (already fetched via Phase 1 SSRF protection). Plain text extraction bounds: enforce max text length before NLP processing (~1MB reasonable cap) |
| V6 Cryptography | No | N/A — no crypto in text analysis |

### Known Threat Patterns for NLP/Text Processing

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Billion laughs / XML bomb via HTML | Denial of Service | Not applicable — HTML is parsed by lxml in Phase 1. Phase 4 only reads the already-parsed soup tree. |
| Extremely long text DoS | Denial of Service | Cap plain text length at 1MB before passing to textstat/spaCy. Both libraries process O(n) in text length; 1MB mitigates CPU exhaustion. |
| Zip bomb via compressed response | Denial of Service | Handled in Phase 1 (MAX_RESPONSE_SIZE). Phase 4 receives already-bounded HTML. |
| Regex DoS (ReDoS) in question detection | Denial of Service | Question detection uses simple string operations (`endswith`, `split`), not complex regex. No backtracking risk. |

## Sources

### Primary (HIGH confidence)
- [textstat PyPI page](https://pypi.org/project/textstat/) — full API reference: all functions, parameters, return types, language support matrix
- [spaCy EntityRecognizer API](https://spacy.io/api/entityrecognizer) — NER component architecture, `Doc.ents`, `Token.ent_type_`, label access patterns
- [spaCy Doc API](https://spacy.io/api/doc) — sentence iteration via `doc.sents`, token attributes, noun chunks
- [spaCy Linguistic Features](https://spacy.io/usage/linguistic-features) — confirmed ORG, GPE, PERSON, MONEY, DATE, LANGUAGE entity types in examples; noted PRODUCT in entity description
- [BeautifulSoup4 docs — get_text()](https://www.crummy.com/software/BeautifulSoup/bs4/doc/#get-text) — separator parameter behavior (verified pattern, used in Phase 1 crawler)
- [PyPI: textstat 0.7.13](https://pypi.org/project/textstat/0.7.13/) — version verification (published 2025-08-09)
- [PyPI: spacy 3.8.14](https://pypi.org/project/spacy/3.8.14/) — version verification (published 2025-04-15)

### Secondary (MEDIUM confidence)
- [spaCy Models — en](https://spacy.io/models/en) — confirmed en_core_web_sm type (core), genre (web), size (sm); model details failed to load from GitHub but component types are well-known
- [spaCy models releases](https://github.com/explosion/spacy-models/releases) — first page did not contain en_core_web_sm; full label set from training data knowledge
- [textstat README](https://github.com/textstat/textstat/blob/main/README.md) — confirmed char_count, sentence_count, lexicon_count API and parameter defaults
- Phase 3 schema_analyzer.py — project-specific patterns (lazy import, scoring decomposition, single public entry point)

### Tertiary (LOW confidence)
- [textstat/statology article](https://www.statology.org/calculate-and-interpret-readability-metrics-with-textstat/) — readability score interpretation guidelines (not authoritative but useful for threshold decisions)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — both textstat and spaCy APIs verified via official PyPI pages; BeautifulSoup already proven in Phases 1-3
- Architecture: HIGH — follows established Phase 3 pattern; scoring decomposition is a direct analogue to schema_analyzer.py structure
- Pitfalls: MEDIUM — identified from library documentation and known NLP edge cases; some pitfalls (empty page handling thresholds) depend on design decisions
- Scoring thresholds: MEDIUM — normalization ceilings are standard ranges but exact values depend on target content distribution (web pages); flagged as assumptions for planner confirmation

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30 days — textstat and spaCy are stable; scoring thresholds may evolve with user feedback)
