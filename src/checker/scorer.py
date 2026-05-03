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
        recommendations=[],  # filled in Plan 02
        timestamp=datetime.now(timezone.utc),
    )
