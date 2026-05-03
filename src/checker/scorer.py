"""
Phase 5: Scorer + Report Generator.

Composition layer that combines all four module scores into a weighted
overall score, letter grade, and structured report.

Imports existing scoring functions rather than re-implementing them.
"""

import logging
import math
from datetime import datetime, timezone

from src.checker.contracts import (
    ContentAnalysis,
    LlmsResult,
    RobotsResult,
    SchemaAnalysis,
    ScoreReport,
)
from src.checker.robots_txt import compute_bot_score
from src.checker.llms_txt import compute_llms_score

logger = logging.getLogger(__name__)

# SCORE-01: Weight configuration
MODULE_WEIGHTS = {
    "robots": 0.20,
    "llms_txt": 0.15,
    "schema": 0.30,
    "content": 0.35,
}

# SCORE-02: Grade boundaries (tested from top down, first match wins)
GRADE_BOUNDARIES = [
    (85, "A"),
    (70, "B"),
    (55, "C"),
    (40, "D"),
    (0, "F"),
]

PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _validate_score(value: float, label: str) -> float:
    """Coerce a score value to a valid float in [0.0, 1.0].

    Returns 0.0 and logs warning for NaN, Inf, or out-of-range values.
    """
    if not math.isfinite(value):
        logger.warning(f"Non-finite {label} score ({value}); coercing to 0.0")
        return 0.0
    if value < 0.0 or value > 1.0:
        logger.warning(
            f"{label} score {value} outside [0.0, 1.0]; clamping"
        )
        return max(0.0, min(1.0, value))
    return value


def _extract_scores(
    robots_result: RobotsResult,
    llms_result: LlmsResult,
    schema_analysis: SchemaAnalysis,
    content_analysis: ContentAnalysis,
) -> dict[str, float]:
    """Extract 0.0-1.0 scores from all four module results."""
    robots_score = compute_bot_score(robots_result.bots)
    llms_score = compute_llms_score(llms_result.found, llms_result.valid)

    return {
        "robots": _validate_score(robots_score, "robots"),
        "llms_txt": _validate_score(llms_score, "llms_txt"),
        "schema": _validate_score(schema_analysis.score, "schema"),
        "content": _validate_score(content_analysis.combined_score, "content"),
    }


def compute_overall_score(scores: dict[str, float]) -> float:
    """Compute weighted 0-100 overall score from module scores.

    Args:
        scores: Dict with keys matching MODULE_WEIGHTS, values in [0.0, 1.0].

    Returns:
        Float rounded to 1 decimal place in [0.0, 100.0].
    """
    weighted = sum(
        scores[key] * MODULE_WEIGHTS[key]
        for key in MODULE_WEIGHTS
    )
    return round(weighted * 100.0, 1)


def letter_grade(overall_score: float) -> str:
    """Map 0-100 score to A-F letter grade.

    Args:
        overall_score: Float in [0.0, 100.0].

    Returns:
        Single character string: "A", "B", "C", "D", or "F".
    """
    for threshold, grade in GRADE_BOUNDARIES:
        if overall_score >= threshold:
            return grade
    return "F"


# Recommendation quality gate thresholds (per Pitfall 4 in RESEARCH.md)
SCHEMA_REC_THRESHOLD = 0.7   # skip schema recs if score >= 0.7
CONTENT_REC_THRESHOLD = 0.6  # skip content recs if combined_score >= 0.6
CONTENT_SUB_THRESHOLD = 0.3  # trigger rec for sub-score below 0.3

IMPORTANT_SCHEMA_TYPES = ["Product", "FAQPage"]

CONTENT_SUBSCORE_CONFIG = [
    ("readability_score", "readability"),
    ("text_ratio", "content-to-HTML ratio"),
    ("entity_score", "named entity presence"),
    ("heading_score", "heading structure"),
    ("qa_density_score", "Q&A density"),
]

CONTENT_REC_MESSAGES = {
    "readability": (
        "Your content readability is low (score: {value:.1f}). "
        "Simplify sentence structure and use shorter paragraphs."
    ),
    "content-to-HTML ratio": (
        "Your content-to-HTML ratio is low (score: {value:.1f}). "
        "Reduce HTML markup relative to visible text content."
    ),
    "named entity presence": (
        "Few named entities detected (score: {value:.1f}). "
        "Ensure your page clearly mentions your organization, products, or location."
    ),
    "heading structure": (
        "Your heading structure needs improvement (score: {value:.1f}). "
        "Use a single H1, organize content under H2/H3 headings, "
        "and make headings descriptive."
    ),
    "Q&A density": (
        "Your Q&A density is low (score: {value:.1f}). "
        "Add question-and-answer sections to help AI models extract information."
    ),
}

SCHEMA_REC_MESSAGES = {
    "Product": (
        "No Product schema found. Adding Product structured data "
        "helps AI search engines display rich product snippets."
    ),
    "FAQPage": (
        "No FAQPage schema found. Adding FAQPage markup can help "
        "your content appear in AI-generated answers."
    ),
}


def _robot_recommendations(result: RobotsResult) -> list[dict]:
    """Generate recommendations based on robots.txt analysis."""
    recs = []
    if not result.exists:
        if result.fetch_error:
            recs.append({
                "priority": "HIGH",
                "module": "robots",
                "message": (
                    f"Could not fetch robots.txt ({result.fetch_error}). "
                    f"Check that your site is reachable."
                ),
            })
        else:
            recs.append({
                "priority": "HIGH",
                "module": "robots",
                "message": (
                    "No robots.txt found. Create one to control AI bot access."
                ),
            })
        return recs
    for bot in result.bots:
        if bot.status == "blocked":
            recs.append({
                "priority": "MEDIUM",
                "module": "robots",
                "message": (
                    f"{bot.bot_name} is blocked in your robots.txt. "
                    f"Unblock it to allow AI search engines to index your content."
                ),
            })
    return recs


def _llms_recommendations(result: LlmsResult) -> list[dict]:
    """Generate recommendations based on llms.txt analysis."""
    recs = []
    if result.fetch_error:
        recs.append({
            "priority": "HIGH",
            "module": "llms_txt",
            "message": (
                f"Could not fetch llms.txt ({result.fetch_error}). "
                f"Check that your site is reachable."
            ),
        })
        return recs
    if not result.found:
        recs.append({
            "priority": "HIGH",
            "module": "llms_txt",
            "message": (
                "No llms.txt found. Create one to help AI models "
                "understand your site structure."
            ),
        })
    elif result.valid is False:
        recs.append({
            "priority": "MEDIUM",
            "module": "llms_txt",
            "message": (
                "Your llms.txt has formatting errors. Fix validation "
                "issues to improve AI readability."
            ),
        })
    return recs


def _schema_recommendations(analysis: SchemaAnalysis) -> list[dict]:
    """Generate recommendations based on schema extraction analysis."""
    if analysis.score >= SCHEMA_REC_THRESHOLD:
        return []
    recs = []
    for schema_type in IMPORTANT_SCHEMA_TYPES:
        if schema_type not in analysis.detected_types:
            recs.append({
                "priority": "MEDIUM",
                "module": "schema",
                "message": SCHEMA_REC_MESSAGES[schema_type],
            })
    if not recs and analysis.score < SCHEMA_REC_THRESHOLD:
        recs.append({
            "priority": "LOW",
            "module": "schema",
            "message": (
                "Consider adding more schema types to improve structured "
                "data coverage. Common types include: Organization, "
                "BreadcrumbList, Article."
            ),
        })
    return recs


def _content_recommendations(analysis: ContentAnalysis) -> list[dict]:
    """Generate recommendations based on content quality analysis."""
    if analysis.combined_score >= CONTENT_REC_THRESHOLD:
        return []
    recs = []
    for field_name, label in CONTENT_SUBSCORE_CONFIG:
        value = getattr(analysis, field_name, 0.0)
        if value < CONTENT_SUB_THRESHOLD:
            recs.append({
                "priority": "MEDIUM",
                "module": "content",
                "message": CONTENT_REC_MESSAGES[label].format(value=value),
            })
    if not recs and analysis.combined_score < CONTENT_REC_THRESHOLD:
        recs.append({
            "priority": "LOW",
            "module": "content",
            "message": (
                "Your content quality is below the recommended threshold. "
                "Review readability, headings, and entity usage."
            ),
        })
    return recs


def generate_recommendations(
    robots_result: RobotsResult,
    llms_result: LlmsResult,
    schema_analysis: SchemaAnalysis,
    content_analysis: ContentAnalysis,
) -> list[dict]:
    """Generate prioritized plain-English recommendations from all modules.

    Inspects each module result for failure conditions and produces
    specific, actionable recommendations. Sorts by priority:
    HIGH before MEDIUM before LOW.

    Returns:
        List of recommendation dicts, each with keys:
        priority ("HIGH"/"MEDIUM"/"LOW"), module (str), message (str).
    """
    all_recs = (
        _robot_recommendations(robots_result)
        + _llms_recommendations(llms_result)
        + _schema_recommendations(schema_analysis)
        + _content_recommendations(content_analysis)
    )
    all_recs = sorted(all_recs, key=lambda r: PRIORITY_ORDER.get(r["priority"], 99))
    return all_recs


def generate_report(
    url: str,
    robots_result: RobotsResult,
    llms_result: LlmsResult,
    schema_analysis: SchemaAnalysis,
    content_analysis: ContentAnalysis,
) -> ScoreReport:
    """Generate a complete scored AI-readiness report.

    Composes all four module scores into a weighted overall score,
    maps to a letter grade, and assembles a structured report.

    Args:
        url: The URL that was analyzed.
        robots_result: robots.txt analysis result from Phase 2.
        llms_result: llms.txt analysis result from Phase 2.
        schema_analysis: Schema extraction result from Phase 3.
        content_analysis: Content quality result from Phase 4.

    Returns:
        ScoreReport with overall_score, grade, module_breakdown,
        empty recommendations (filled in Plan 02), and UTC timestamp.
    """
    scores = _extract_scores(
        robots_result, llms_result, schema_analysis, content_analysis
    )
    overall = compute_overall_score(scores)
    grade = letter_grade(overall)

    module_breakdown = {
        key: {
            "score": scores[key],
            "weight": MODULE_WEIGHTS[key],
            "weighted": round(scores[key] * MODULE_WEIGHTS[key] * 100.0, 1),
        }
        for key in MODULE_WEIGHTS
    }

    return ScoreReport(
        url=url,
        overall_score=overall,
        grade=grade,
        module_breakdown=module_breakdown,
        recommendations=generate_recommendations(
            robots_result, llms_result, schema_analysis, content_analysis
        ),
        timestamp=datetime.now(timezone.utc),
    )
