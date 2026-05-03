# Phase 5: Scorer + Report Generator - Research

**Researched:** 2026-05-03
**Domain:** Scoring composition, recommendation generation, report data contract
**Confidence:** HIGH

## Summary

Phase 5 is a pure composition layer -- no new external dependencies, no network I/O, no new data formats. Its job is to consume the four existing module result types (RobotsResult, LlmsResult, SchemaAnalysis, ContentAnalysis), combine their scores using fixed weights, map to an A-F grade, and generate plain-English recommendations for what the user should fix.

The phase is computationally trivial (weighted average, grade lookup, template-based recommendations) but has significant edge-case complexity around missing/error states from upstream modules. The key architectural decisions are: (1) how to handle robots.txt and llms.txt scores when the scorer must compute them itself (the result types lack a `.score` field -- unlike SchemaAnalysis and ContentAnalysis which carry their own), and (2) how to generate recommendations that are specific, actionable, and correctly prioritized.

**Primary recommendation:** Build as a single `scorer.py` module with three public functions (`compute_overall_score`, `generate_recommendations`, `generate_report`) and a `ScoreReport` dataclass added to `contracts.py`. Import existing scoring functions from `robots_txt` and `llms_txt` modules rather than duplicating logic. Use template-based recommendation generation with priority sorting -- no ML, no external libraries needed.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Score composition (weighted average) | API / Backend | -- | Pure computation on in-memory results; no client logic |
| Grade mapping (A-F) | API / Backend | -- | Simple lookup; no UI dependency (CLI and Streamlit format it differently) |
| Recommendation generation | API / Backend | -- | Business logic: inspects module results for failure patterns |
| Report dict assembly | API / Backend | -- | Data contract production; consumed by Phase 6 (CLI) and Phase 7 (Streamlit) |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python dataclasses | stdlib | ScoreReport data contract | Same pattern as all existing contracts [VERIFIED: codebase] |
| datetime (stdlib) | stdlib | Timestamp on report | Already used in all 5 existing dataclasses [VERIFIED: codebase] |
| src.checker.robots_txt:compute_bot_score | existing | Robots score computation | DRY -- score logic lives in one place [VERIFIED: codebase] |
| src.checker.llms_txt:compute_llms_score | existing | llms.txt score computation | DRY -- score logic lives in one place [VERIFIED: codebase] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.4.2 (existing) | Test the scorer | All test scenarios [VERIFIED: `python3 -m pytest --version`] |
| typing (stdlib) | stdlib | Type hints for ScoreReport | Used in contracts.py already [VERIFIED: codebase] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Re-implement bot/llms scoring in scorer.py | Import compute_bot_score / compute_llms_score from source modules | Re-implementation creates drift risk. Import couples scorer to internal module functions but keeps single source of truth. Import is the better choice for v1. |
| Generator-based recommendation stream | Template-based dict builder | Generator adds complexity for no benefit -- recommendations list is small (<20 items max). Template dicts are simpler to sort and serialize. |

**Installation:** No new packages required. The scorer imports only stdlib and existing checker modules.

## Architecture Patterns

### System Architecture Diagram

```
                        ┌──────────────────────────┐
                        │   generate_report(url,     │
                        │   robots_result,           │
                        │   llms_result,             │
                        │   schema_analysis,         │
                        │   content_analysis)        │
                        └─────────┬────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
          ┌─────────────┐  ┌──────────┐  ┌──────────────────┐
          │ Extract      │  │ Compute  │  │ Generate         │
          │ Module       │  │ Weighted │  │ Recommendations  │
          │ Scores       │  │ Overall  │  │ (per module)     │
          │              │  │ Score    │  │                  │
          │ robots:      │  │          │  │ Inspect:         │
          │  compute_    │  │ 0-100 =  │  │  - blocked bots  │
          │  bot_score() │  │ (S_r *   │  │  - missing llms  │
          │              │  │  0.20 +  │  │  - absent schema │
          │ llms:        │  │  S_l *   │  │  - low sub-scores│
          │  compute_    │  │  0.15 +  │  │                  │
          │  llms_score()│  │  S_s *   │  │ Priority sort:   │
          │              │  │  0.30 +  │  │  HIGH > MED > LOW│
          │ schema:      │  │  S_c *   │  │                  │
          │  .score      │  │  0.35)   │  └────────┬─────────┘
          │              │  │  * 100   │           │
          │ content:     │  └────┬─────┘           │
          │  .combined_  │       │                 │
          │  score       │       ▼                 │
          └──────┬───────┘  ┌──────────┐           │
                 │          │ Grade     │           │
                 │          │ Mapping   │           │
                 │          │           │           │
                 │          │ A: 85-100 │           │
                 │          │ B: 70-84  │           │
                 │          │ C: 55-69  │           │
                 │          │ D: 40-54  │           │
                 │          │ F: 0-39   │           │
                 │          └────┬─────┘           │
                 │               │                 │
                 └───────┬───────┴─────────────────┘
                         │
                         ▼
                ┌──────────────────┐
                │  ScoreReport     │
                │  dataclass       │
                │                  │
                │  url             │
                │  overall_score   │
                │  grade           │
                │  module_breakdown│
                │  recommendations │
                │  timestamp       │
                └──────────────────┘
```

### Recommended Project Structure
```
src/checker/
├── contracts.py          # ADD: ScoreReport dataclass
├── scorer.py             # NEW: all scoring + recommendation logic
├── robots_txt.py         # existing -- import compute_bot_score
├── llms_txt.py           # existing -- import compute_llms_score
├── schema_analyzer.py    # existing -- read .score field
├── content_analyzer.py   # existing -- read .combined_score field
└── __init__.py           # ADD: ScoreReport, generate_report exports

tests/
└── test_scorer.py        # NEW: all scorer tests
```

### Pattern 1: Composition-Over-Inheritance for Score Computation

**What:** Each module score is extracted via a small adapter function. The scorer does not know (and should not know) how each module computes its score internally -- it only needs the final 0.0-1.0 value.

**When to use:** When composing heterogeneous module outputs into a single pipeline.

**Example:**
```python
# Source: derived from existing codebase patterns
# Each _get_*_score function is a thin adapter that extracts
# the 0.0-1.0 score from a module result, handling edge cases.

def _get_robots_score(result: RobotsResult) -> float:
    """Extract robots score from result, handling error states.
    
    When bots list is empty (fetch error), compute_bot_score
    returns 0.5 baseline. This is correct: transient errors
    should not unfairly penalize the overall score.
    """
    if not result.exists and result.fetch_error:
        # Transient error: use baseline 0.5 (neutral)
        return 0.5
    return compute_bot_score(result.bots)

def _get_llms_score(result: LlmsResult) -> float:
    """Extract llms.txt score from result."""
    if result.fetch_error:
        # Transient error: missing = 0.0
        return 0.0
    return compute_llms_score(result.found, result.valid)

def _get_schema_score(analysis: SchemaAnalysis) -> float:
    """Schema score is already computed and stored."""
    return analysis.score

def _get_content_score(analysis: ContentAnalysis) -> float:
    """Content combined score is already computed and stored."""
    return analysis.combined_score
```

### Pattern 2: Template-Based Recommendation Generation

**What:** Rules inspect module results and produce recommendation dicts when conditions are met. Recommendations are tagged with priority and sorted before inclusion in the report.

**When to use:** When recommendations are deterministic (rule-based, not ML-driven) and must be human-readable.

**Example:**
```python
# Source: derived from SCORE-03 requirement
# Each generator function returns list[dict] with keys:
#   priority: "HIGH" | "MEDIUM" | "LOW"
#   module: "robots" | "llms_txt" | "schema" | "content"
#   message: str (plain-English, specific)

def _robot_recommendations(result: RobotsResult) -> list[dict]:
    recs = []
    if not result.exists and result.fetch_error:
        recs.append({
            "priority": "HIGH",
            "module": "robots",
            "message": f"Could not fetch robots.txt ({result.fetch_error}). "
                       f"Check that your site is reachable."
        })
    elif not result.exists:
        recs.append({
            "priority": "HIGH",
            "module": "robots",
            "message": "No robots.txt found. Create one to control AI bot access."
        })
    else:
        for bot in result.bots:
            if bot.status == "blocked":
                recs.append({
                    "priority": "MEDIUM",
                    "module": "robots",
                    "message": f"{bot.bot_name} is blocked in your robots.txt. "
                               f"Unblock it to allow AI search engines to index your content."
                })
    return recs
```

### Anti-Patterns to Avoid

- **God-scorer function:** A single 200-line function that does score extraction, weighting, grading, and recommendations all at once. Instead, decompose into small single-responsibility functions as shown above.
- **Silent score coercion:** If a module returns NaN or out-of-range, do not silently clamp. Log a warning and treat as 0.0 so the behavior is observable.
- **Hardcoded recommendation strings in a single function:** Each module should have its own recommendation generator. This keeps rules close to the data they inspect.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Robots score computation | Re-implement from BotStatus list | `from src.checker.robots_txt import compute_bot_score` | Single source of truth; drift risk if scoring formula changes [VERIFIED: codebase] |
| llms.txt score computation | Re-implement from found/valid booleans | `from src.checker.llms_txt import compute_llms_score` | Single source of truth [VERIFIED: codebase] |
| Grade boundary logic | Custom comparator chains | Simple if/elif on integer thresholds | No library needed; boundaries are fixed per SCORE-02 |
| Recommendation priority sorting | Custom sort algorithm | `sorted(recs, key=lambda r: PRIORITY_ORDER[r["priority"]])` | Python's Timsort is stable and built-in |

**Key insight:** The scorer is glue code. Its job is composition, not computation. Resist the urge to rewrite module internals.

## Runtime State Inventory

> Omitted -- this is a greenfield composition phase, not a rename/refactor/migration.

## Common Pitfalls

### Pitfall 1: Score Range Mismatch (robots 0.01-0.99)

**What goes wrong:** The robots module produces scores in [0.01, 0.99] while schema and content produce [0.0, 1.0]. If the scorer treats all scores uniformly, the robots contribution is slightly compressed (max 19.8 out of a possible 20 in the weighted 0-100 scale).

**Why it happens:** Phase 2 intentionally used a non-zero range to avoid misleading absolute scores -- no site is perfectly AI-visible (1.0) or completely invisible (0.0).

**How to avoid:** Accept this as-is and document the behavior. The difference (0.2 points) is negligible for practical use. Do NOT rescale robots scores to [0,1] -- that would alter the established scoring semantics.

**Warning signs:** Someone asks "why can't I get 100?" -- the answer is documented.

### Pitfall 2: Empty bots List for Error States

**What goes wrong:** When `RobotsResult.exists=False` with `fetch_error` set, `result.bots` is `[]`. Passing an empty list to `compute_bot_score()` returns 0.5 (baseline). This is numerically correct but semantically misleading -- the score should communicate "we couldn't check" rather than "neutral."

**How to avoid:** Check `exists` and `fetch_error` before calling `compute_bot_score`. When `exists=False` with an error, document the score as "unavailable" in the module breakdown and skip robots-specific recommendations (use the error message instead).

**Warning signs:** Report shows a 0.5 robots score on a site that clearly has a robots.txt -- the fetch failed silently.

### Pitfall 3: Grade Boundary Off-by-One

**What goes wrong:** Using `<` vs `<=` at grade boundaries. SCORE-02 specifies: A (85-100), B (70-84), C (55-69), D (40-54), F (0-39). A score of exactly 85.0 should be "A", exactly 70.0 should be "B", etc.

**Why it happens:** Boundary conditions are a classic source of bugs in grading logic.

**How to avoid:** Use integer thresholds with `>=`. Test every boundary value (85, 84, 70, 69, 55, 54, 40, 39) explicitly.

**Warning signs:** Tests pass on random scores but fail on exact boundary values.

### Pitfall 4: Recommendations for "Good Enough" Modules

**What goes wrong:** Generating recommendations for every module score below 1.0 produces noise. A schema score of 0.9 should not generate "missing Product schema" recommendations -- the site has most important types and is doing fine.

**Why it happens:** Recommendations are triggered on simple boolean checks ("is schema score < 1.0?") without considering whether the gap is meaningful.

**How to avoid:** Use thresholds aligned with the scoring semantics:
- Robots: recommend on any blocked bot (regardless of overall score)
- llms.txt: recommend when missing or malformed (regardless of overall score)
- Schema: recommend when important types (Product, FAQPage) are absent; skip if score >= 0.7
- Content: recommend on low sub-scores (<0.3); skip if combined_score >= 0.6

**Warning signs:** Report shows 20+ recommendations where most are trivial.

## Code Examples

Verified patterns from the existing codebase:

### Extracting scores from all four modules
```python
# Source: this research, based on codebase analysis
# Each module produces its score differently. The scorer normalizes.

def _extract_scores(
    robots_result: RobotsResult,
    llms_result: LlmsResult,
    schema_analysis: SchemaAnalysis,
    content_analysis: ContentAnalysis,
) -> dict[str, float]:
    """Extract 0.0-1.0 scores from all four module results.
    
    Returns dict with keys: robots, llms_txt, schema, content.
    All values are float in [0.0, 1.0].
    """
    from src.checker.robots_txt import compute_bot_score
    from src.checker.llms_txt import compute_llms_score
    
    return {
        "robots": compute_bot_score(robots_result.bots)
                  if robots_result.exists else 0.5,
        "llms_txt": compute_llms_score(llms_result.found, llms_result.valid)
                    if llms_result.found else 0.0,
        "schema": schema_analysis.score,
        "content": content_analysis.combined_score,
    }
```

### Weighted overall score computation (SCORE-01)
```python
# Source: SCORE-01 requirement (20%, 15%, 30%, 35% weights)
MODULE_WEIGHTS = {
    "robots": 0.20,
    "llms_txt": 0.15,
    "schema": 0.30,
    "content": 0.35,
}

def compute_overall_score(scores: dict[str, float]) -> float:
    """Compute weighted 0-100 overall score.
    
    Args:
        scores: Dict from _extract_scores with keys matching MODULE_WEIGHTS.
    
    Returns:
        Float rounded to 1 decimal place in [0.0, 100.0].
    """
    weighted = sum(
        scores[key] * MODULE_WEIGHTS[key]
        for key in MODULE_WEIGHTS
    )
    return round(weighted * 100.0, 1)
```

### Grade mapping (SCORE-02)
```python
# Source: SCORE-02 requirement (A: 85-100, B: 70-84, etc.)
GRADE_BOUNDARIES = [
    (85, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
    (0, "F"),
]

def letter_grade(overall_score: float) -> str:
    """Map 0-100 score to A-F letter grade."""
    for threshold, grade in GRADE_BOUNDARIES:
        if overall_score >= threshold:
            return grade
    return "F"  # fallback
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Individual module scoring (phases 2-4) | Composition into weighted report | Phase 5 | First time all signals combine into a single actionable output |
| Raw analysis dataclasses | ScoreReport with recommendations | Phase 5 | Consumers (CLI, Streamlit) now get a single report instead of piecing together 4 results |

**Deprecated/outdated:**
- None -- this is the first phase that composes the four modules. All existing contracts remain unchanged.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Robots score of 0.01-0.99 (not 0.0-1.0) is acceptable for the weighted overall score | Common Pitfalls #1 | Negligible (~0.2 points out of 100). If user demands exactly 0.0-1.0 rescaling, the scorer can be adjusted in < 5 lines. |
| A2 | Empty bots list (fetch error) -> 0.5 baseline is the correct behavior | Common Pitfalls #2 | Low. The alternatives (skip module, penalize) would be more complex with no clear benefit. |
| A3 | Recommendations should be gated by quality thresholds (not all sub-optimal scores get a recommendation) | Common Pitfalls #4 | Medium. If user wants every minor gap flagged, threshold values can be adjusted or made configurable. Current thresholds are defensible defaults. |
| A4 | The scorer receives all four module results pre-computed -- it does not orchestrate the analysis pipeline | Architecture | Low. Phase 6 (Pipeline + CLI) is responsible for orchestration. The scorer is a pure function of its inputs. |
| A5 | SchemaAnalysis.score and ContentAnalysis.combined_score are always valid floats in [0.0, 1.0] | Integration Points | Low. These are set by constructors with default 0.0 and never produce NaN/Inf. Verified by inspection of analyzer code. |

## Open Questions

1. **Should the scorer handle fetch errors differently in the robots/llms.txt modules?**
   - What we know: `compute_bot_score([])` returns 0.5 (neutral baseline). `compute_llms_score(False, None)` returns 0.0.
   - What's unclear: Whether a timeout/connection error should produce a different score than "file not found" (404). Currently both result in `exists=False` with empty bots / not-found llms.
   - Recommendation: Treat them the same for scoring (0.5 baseline for robots, 0.0 for llms), but differentiate in the module breakdown and recommendations. This keeps scoring simple while still communicating "we tried but couldn't check" to the user.

2. **What recommendation threshold values are appropriate for content sub-scores?**
   - What we know: ContentAnalysis has 5 sub-scores (readability, text_ratio, entities, headings, qa_density), each 0.0-1.0.
   - What's unclear: At what threshold should each sub-score trigger a recommendation? 0.3 feels reasonable for most (below 30% of ideal), but heading score at 0.0 (no headings at all) vs 0.3 (suboptimal headings) might warrant different messages.
   - Recommendation: Start with 0.3 as the universal threshold. Adjust per sub-score in response to user feedback during Phase 6 (CLI) testing. Document the threshold as a constant.

3. **Should recommendations include "positive" messages (things the site does well)?**
   - What we know: SCORE-03 says "recommendations based on which checks failed" -- implies failure-only.
   - What's unclear: Whether a "your schema markup looks great" message adds value or noise.
   - Recommendation: Failure-only for v1. Positive reinforcement can be added in v2 if users request it. Keeps the report focused on action items.

## Environment Availability

> All dependencies are internal code modules (no new external tools or services). The phase has no network, database, or external service dependencies.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.10+ | Scorer module | Yes | 3.13.9 [VERIFIED: `python3 --version`] | -- |
| pytest | Test suite | Yes | 8.4.2 [VERIFIED: `python3 -m pytest --version`] | -- |
| src.checker.robots_txt | compute_bot_score import | Yes | existing [VERIFIED: codebase] | -- |
| src.checker.llms_txt | compute_llms_score import | Yes | existing [VERIFIED: codebase] | -- |
| src.checker.contracts | All result types | Yes | existing [VERIFIED: codebase] | -- |

**Missing dependencies with no fallback:** None
**Missing dependencies with fallback:** None

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json`

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `python3 -m pytest tests/test_scorer.py -x` |
| Full suite command | `python3 -m pytest tests/test_scorer.py -v` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCORE-01 | Weighted overall score matches formula (robots 20%, llms 15%, schema 30%, content 35%) | unit | `pytest tests/test_scorer.py::test_weighted_score_calculation -x` | No - Wave 0 |
| SCORE-01 | All-zero module scores produce overall 0.0 | unit | `pytest tests/test_scorer.py::test_overall_score_all_zeros -x` | No - Wave 0 |
| SCORE-01 | All-max module scores produce expected max (robots capped at 0.99) | unit | `pytest tests/test_scorer.py::test_overall_score_all_max -x` | No - Wave 0 |
| SCORE-02 | Grade A assigned at 85 boundary | unit | `pytest tests/test_scorer.py::test_grade_boundary_A_low -x` | No - Wave 0 |
| SCORE-02 | Grade B assigned at 70 boundary (84.9 is B, 85.0 is A) | unit | `pytest tests/test_scorer.py::test_grade_boundary_AB_edges -x` | No - Wave 0 |
| SCORE-02 | All 5 grade boundaries return correct letter | unit | `pytest tests/test_scorer.py::test_grade_all_boundaries -x` | No - Wave 0 |
| SCORE-03 | Blocked GPTBot generates specific recommendation | unit | `pytest tests/test_scorer.py::test_recommendation_blocked_gptbot -x` | No - Wave 0 |
| SCORE-03 | Missing robots.txt generates recommendation | unit | `pytest tests/test_scorer.py::test_recommendation_missing_robots -x` | No - Wave 0 |
| SCORE-03 | Missing llms.txt generates recommendation | unit | `pytest tests/test_scorer.py::test_recommendation_missing_llms -x` | No - Wave 0 |
| SCORE-03 | Missing schema types generate recommendations | unit | `pytest tests/test_scorer.py::test_recommendation_missing_schema_types -x` | No - Wave 0 |
| SCORE-03 | Low content sub-scores generate targeted recommendations | unit | `pytest tests/test_scorer.py::test_recommendation_low_content_subscores -x` | No - Wave 0 |
| SCORE-03 | Recommendations sorted by priority (HIGH before MEDIUM before LOW) | unit | `pytest tests/test_scorer.py::test_recommendation_priority_sorting -x` | No - Wave 0 |
| SCORE-03 | Perfect module scores produce no recommendations for that module | unit | `pytest tests/test_scorer.py::test_no_recommendations_for_perfect_module -x` | No - Wave 0 |
| SCORE-04 | Report dict contains all required top-level keys | unit | `pytest tests/test_scorer.py::test_report_has_required_keys -x` | No - Wave 0 |
| SCORE-04 | Module breakdown includes scores and weights | unit | `pytest tests/test_scorer.py::test_report_module_breakdown -x` | No - Wave 0 |
| SCORE-04 | Timestamp is UTC datetime | unit | `pytest tests/test_scorer.py::test_report_timestamp_is_utc -x` | No - Wave 0 |
| SCORE-04 | Report is JSON-serializable (no BeautifulSoup, no complex objects) | integration | `pytest tests/test_scorer.py::test_report_json_serializable -x` | No - Wave 0 |
| Edge | robots.txt fetch error handled gracefully | unit | `pytest tests/test_scorer.py::test_robots_fetch_error_handling -x` | No - Wave 0 |
| Edge | Empty bots list produces baseline score 0.5 | unit | `pytest tests/test_scorer.py::test_empty_bots_score -x` | No - Wave 0 |
| Edge | All 7 bots blocked -> score still valid | unit | `pytest tests/test_scorer.py::test_all_blocked_score -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_scorer.py -x`
- **Per wave merge:** `python3 -m pytest tests/test_scorer.py -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_scorer.py` -- covers all 20 test cases listed above
- [ ] `src/checker/scorer.py` -- new module with all scoring/recommendation logic
- [ ] `src/checker/contracts.py` -- ScoreReport dataclass addition
- [ ] `src/checker/__init__.py` -- ScoreReport and generate_report exports

*(No existing test infrastructure for the scorer -- this is a new module.)*

## Security Domain

> `security_enforcement` is enabled (default -- not explicitly `false` in config)

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No auth in v1 |
| V3 Session Management | No | Stateless pipeline |
| V4 Access Control | No | Single-user tool |
| V5 Input Validation | Yes | Validate all score inputs are float and in range [0.0, 1.0]; reject NaN/Inf |
| V6 Cryptography | No | No crypto in scorer |

### Known Threat Patterns for Python Composition Layer

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| NaN/Inf propagation from upstream module | Denial of Service | Guard each score extraction with `math.isfinite()` check; coerce to 0.0 with warning log [ASSUMED: based on defensive programming practice] |
| Recommendation injection (user-controlled strings in module results) | Information Disclosure | Recommendations are generated server-side from typed data; no user input flows into message templates except module result fields which are validated by upstream modules [VERIFIED: codebase analysis -- all recommendation inputs come from typed dataclass fields] |
| Score overflow (scores outside [0,1] range) | Tampering | Clamp all extracted scores to [0.0, 1.0] before weighting; log warning if clamping occurred [ASSUMED: defensive default] |

## Sources

### Primary (HIGH confidence)
- Codebase inspection (`src/checker/contracts.py`, `robots_txt.py`, `llms_txt.py`, `schema_analyzer.py`, `content_analyzer.py`, `access_fetcher.py`, `__init__.py`) -- verified all module result types, score field availability, scoring function signatures, and import paths
- REQUIREMENTS.md -- verified SCORE-01 through SCORE-04 specification, weight values, grade boundaries
- ROADMAP.md -- verified phase dependencies, success criteria, cross-cutting constraints

### Secondary (MEDIUM confidence)
- Tests inspection (`tests/conftest.py`, `tests/test_robots.py`, `tests/test_schema.py`, `tests/test_content.py`) -- verified test patterns, fixture strategies, and pytest configuration
- `pyproject.toml` -- verified dependency versions, pytest configuration, Python version requirement

### Tertiary (LOW confidence)
- None -- all claims about existing code were verified by direct file inspection. Assumptions are logged in the Assumptions Log.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies needed; all requirements met by stdlib + existing checker modules
- Architecture: HIGH -- composition pattern is straightforward; existing module APIs and score extraction paths verified by code inspection
- Pitfalls: HIGH -- score range mismatch, grade boundaries, and empty-state handling all verified by running the actual code and inspecting source

**Research date:** 2026-05-03
**Valid until:** 2026-06-03 (30 days -- stable domain, no fast-moving external dependencies)
