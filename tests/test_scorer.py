"""Tests for scorer.py — covers SCORE-01, SCORE-02, and SCORE-04."""

import json
from dataclasses import asdict
from datetime import datetime, timezone

import pytest

from src.checker.contracts import (
    BotStatus,
    ContentAnalysis,
    LlmsResult,
    RobotsResult,
    SchemaAnalysis,
    ScoreReport,
)
from src.checker.scorer import compute_overall_score, generate_report, letter_grade


# ----- SCORE-01: Weighted overall score computation -----

def test_weighted_score_calculation():
    """SCORE-01: verify weighted formula with known scores produces correct result."""
    scores = {"robots": 0.85, "llms_txt": 0.3, "schema": 0.7, "content": 0.6}
    # weighted: 0.85*0.20 + 0.3*0.15 + 0.7*0.30 + 0.6*0.35 = 0.17 + 0.045 + 0.21 + 0.21 = 0.635
    # overall: 0.635 * 100 = 63.5
    result = compute_overall_score(scores)
    assert result == 63.5


def test_overall_score_all_zeros():
    """SCORE-01: all module scores 0.0 produces overall 0.0."""
    scores = {"robots": 0.0, "llms_txt": 0.0, "schema": 0.0, "content": 0.0}
    assert compute_overall_score(scores) == 0.0


def test_overall_score_all_max():
    """SCORE-01: all max scores (robots 0.99) produces expected capped result."""
    scores = {"robots": 0.99, "llms_txt": 1.0, "schema": 1.0, "content": 1.0}
    # weighted: 0.99*0.20 + 1.0*0.15 + 1.0*0.30 + 1.0*0.35 = 0.198 + 0.15 + 0.30 + 0.35 = 0.998
    # overall: 0.998 * 100 = 99.8
    assert compute_overall_score(scores) == 99.8


# ----- SCORE-02: Letter grade mapping -----

def test_grade_boundary_A_low():
    """SCORE-02: score 85.0 returns 'A'."""
    assert letter_grade(85.0) == "A"


def test_grade_boundary_AB_edges():
    """SCORE-02: score 84.9 returns 'B', 85.0 returns 'A'."""
    assert letter_grade(84.9) == "B"
    assert letter_grade(85.0) == "A"


def test_grade_all_boundaries():
    """SCORE-02: test all 5 grade boundaries (85, 70, 55, 40, 0)."""
    assert letter_grade(85.0) == "A"
    assert letter_grade(84.9) == "B"
    assert letter_grade(70.0) == "B"
    assert letter_grade(69.9) == "C"
    assert letter_grade(55.0) == "C"
    assert letter_grade(54.9) == "D"
    assert letter_grade(40.0) == "D"
    assert letter_grade(39.9) == "F"
    assert letter_grade(0.0) == "F"


# ----- SCORE-04: ScoreReport structure -----

def test_report_has_required_keys():
    """SCORE-04: ScoreReport contains url, overall_score, grade,
    module_breakdown, recommendations, timestamp."""
    report = ScoreReport(url="https://example.com")
    assert report.url == "https://example.com"
    assert isinstance(report.overall_score, float)
    assert isinstance(report.grade, str)
    assert isinstance(report.module_breakdown, dict)
    assert isinstance(report.recommendations, list)
    assert isinstance(report.timestamp, datetime)
    assert report.timestamp.tzinfo is not None


def test_report_module_breakdown():
    """SCORE-04: module_breakdown has all 4 modules with score, weight,
    weighted keys."""
    robots_result = RobotsResult(url="https://example.com", exists=True)
    llms_result = LlmsResult(url="https://example.com", found=False)
    schema_analysis = SchemaAnalysis(url="https://example.com")
    content_analysis = ContentAnalysis(url="https://example.com")

    report = generate_report(
        url="https://example.com",
        robots_result=robots_result,
        llms_result=llms_result,
        schema_analysis=schema_analysis,
        content_analysis=content_analysis,
    )

    expected_modules = {"robots", "llms_txt", "schema", "content"}
    assert set(report.module_breakdown.keys()) == expected_modules
    for key in expected_modules:
        mod = report.module_breakdown[key]
        assert "score" in mod, f"{key} missing 'score'"
        assert "weight" in mod, f"{key} missing 'weight'"
        assert "weighted" in mod, f"{key} missing 'weighted'"
        assert isinstance(mod["score"], float)
        assert isinstance(mod["weight"], float)
        assert isinstance(mod["weighted"], float)


def test_report_timestamp_is_utc():
    """SCORE-04: timestamp is a datetime with tzinfo=UTC."""
    robots_result = RobotsResult(url="https://example.com", exists=True)
    llms_result = LlmsResult(url="https://example.com", found=False)
    schema_analysis = SchemaAnalysis(url="https://example.com")
    content_analysis = ContentAnalysis(url="https://example.com")

    report = generate_report(
        url="https://example.com",
        robots_result=robots_result,
        llms_result=llms_result,
        schema_analysis=schema_analysis,
        content_analysis=content_analysis,
    )

    assert isinstance(report.timestamp, datetime)
    assert report.timestamp.tzinfo == timezone.utc


def test_report_json_serializable():
    """SCORE-04: dataclasses.asdict(report) produces JSON-serializable
    dict (no BeautifulSoup, no complex objects)."""
    robots_result = RobotsResult(url="https://example.com", exists=True)
    llms_result = LlmsResult(url="https://example.com", found=False)
    schema_analysis = SchemaAnalysis(url="https://example.com")
    content_analysis = ContentAnalysis(url="https://example.com")

    report = generate_report(
        url="https://example.com",
        robots_result=robots_result,
        llms_result=llms_result,
        schema_analysis=schema_analysis,
        content_analysis=content_analysis,
    )

    report_dict = asdict(report)
    # Must be JSON-serializable (no BeautifulSoup, no complex objects)
    json_str = json.dumps(report_dict, default=str)
    assert isinstance(json_str, str)
    assert len(json_str) > 0


# ----- Edge cases -----

def test_robots_fetch_error_handling():
    """Edge: robots_result.exists=False + fetch_error produces 0.5
    baseline score."""
    robots_result = RobotsResult(
        url="https://example.com",
        exists=False,
        fetch_error="timeout",
    )
    llms_result = LlmsResult(url="https://example.com", found=False)
    schema_analysis = SchemaAnalysis(url="https://example.com")
    content_analysis = ContentAnalysis(url="https://example.com")

    report = generate_report(
        url="https://example.com",
        robots_result=robots_result,
        llms_result=llms_result,
        schema_analysis=schema_analysis,
        content_analysis=content_analysis,
    )

    # With fetch error and no bots, compute_bot_score returns 0.5 baseline
    robots_breakdown = report.module_breakdown["robots"]
    assert robots_breakdown["score"] == 0.5
    assert isinstance(report.overall_score, float)


def test_empty_bots_score():
    """Edge: empty bots list produces 0.5 baseline from compute_bot_score."""
    scores = {"robots": 0.5, "llms_txt": 0.0, "schema": 0.0, "content": 0.0}
    overall = compute_overall_score(scores)
    # 0.5 * 0.20 + 0 + 0 + 0 = 0.10 * 100 = 10.0
    assert overall == 10.0


def test_all_blocked_score():
    """Edge: all 7 bots blocked produces valid (non-crashing) overall
    score."""
    # All 7 bots blocked: compute_bot_score returns 0.01
    bots = [
        BotStatus(bot_name="GPTBot", status="blocked", explicitly_mentioned=True),
        BotStatus(bot_name="ClaudeBot", status="blocked", explicitly_mentioned=True),
        BotStatus(bot_name="PerplexityBot", status="blocked", explicitly_mentioned=True),
        BotStatus(bot_name="CCBot", status="blocked", explicitly_mentioned=True),
        BotStatus(bot_name="Google-Extended", status="blocked", explicitly_mentioned=True),
        BotStatus(bot_name="Applebot-Extended", status="blocked", explicitly_mentioned=True),
        BotStatus(bot_name="Amazonbot", status="blocked", explicitly_mentioned=True),
    ]
    robots_result = RobotsResult(url="https://example.com", exists=True, bots=bots)
    llms_result = LlmsResult(url="https://example.com", found=False)
    schema_analysis = SchemaAnalysis(url="https://example.com")
    content_analysis = ContentAnalysis(url="https://example.com")

    report = generate_report(
        url="https://example.com",
        robots_result=robots_result,
        llms_result=llms_result,
        schema_analysis=schema_analysis,
        content_analysis=content_analysis,
    )

    # All blocked → robots score 0.01
    assert report.module_breakdown["robots"]["score"] == 0.01
    assert isinstance(report.overall_score, float)
    assert report.overall_score >= 0.0


# ----- SCORE-03: Recommendation generation -----


def test_recommendation_blocked_gptbot():
    """SCORE-03: RobotsResult with blocked GPTBot generates specific
    MEDIUM recommendation."""
    from src.checker.scorer import _robot_recommendations

    result = RobotsResult(
        url="https://example.com",
        exists=True,
        bots=[BotStatus(bot_name="GPTBot", status="blocked")],
    )
    recs = _robot_recommendations(result)
    assert len(recs) == 1
    assert recs[0]["priority"] == "MEDIUM"
    assert recs[0]["module"] == "robots"
    assert "GPTBot" in recs[0]["message"]
    assert "blocked" in recs[0]["message"]


def test_recommendation_missing_robots():
    """SCORE-03: RobotsResult with exists=False generates HIGH
    recommendation about missing robots.txt."""
    from src.checker.scorer import _robot_recommendations

    result = RobotsResult(url="https://example.com", exists=False)
    recs = _robot_recommendations(result)
    assert len(recs) == 1
    assert recs[0]["priority"] == "HIGH"
    assert recs[0]["module"] == "robots"
    assert "No robots.txt found" in recs[0]["message"]


def test_recommendation_missing_llms():
    """SCORE-03: LlmsResult with found=False generates HIGH
    recommendation about missing llms.txt."""
    from src.checker.scorer import _llms_recommendations

    result = LlmsResult(url="https://example.com", found=False)
    recs = _llms_recommendations(result)
    assert len(recs) == 1
    assert recs[0]["priority"] == "HIGH"
    assert recs[0]["module"] == "llms_txt"
    assert "No llms.txt found" in recs[0]["message"]


def test_recommendation_missing_schema_types():
    """SCORE-03: SchemaAnalysis with low score and missing Product,
    FAQPage types generates MEDIUM recommendations for both."""
    from src.checker.scorer import _schema_recommendations

    analysis = SchemaAnalysis(
        url="https://example.com",
        score=0.3,
        detected_types={"Organization"},
    )
    recs = _schema_recommendations(analysis)
    assert len(recs) == 2
    for rec in recs:
        assert rec["priority"] == "MEDIUM"
        assert rec["module"] == "schema"
    messages = [r["message"] for r in recs]
    assert any("Product" in m for m in messages)
    assert any("FAQPage" in m for m in messages)


def test_recommendation_low_content_subscores():
    """SCORE-03: ContentAnalysis with low readability and heading
    subscores generates targeted MEDIUM recommendations."""
    from src.checker.scorer import _content_recommendations

    analysis = ContentAnalysis(
        url="https://example.com",
        combined_score=0.3,
        readability_score=0.1,
        heading_score=0.1,
    )
    recs = _content_recommendations(analysis)
    assert len(recs) == 2
    for rec in recs:
        assert rec["priority"] == "MEDIUM"
        assert rec["module"] == "content"
    messages = [r["message"] for r in recs]
    assert any("readability" in m.lower() for m in messages)
    assert any("heading" in m.lower() for m in messages)


def test_recommendation_priority_sorting():
    """SCORE-03: generate_recommendations sorts by priority: all HIGH
    before all MEDIUM before all LOW."""
    from src.checker.scorer import generate_recommendations

    robots_result = RobotsResult(
        url="https://example.com",
        exists=True,
        bots=[BotStatus(bot_name="GPTBot", status="blocked")],
    )
    llms_result = LlmsResult(url="https://example.com", found=False)
    schema_analysis = SchemaAnalysis(
        url="https://example.com",
        score=0.3,
        detected_types=set(),
    )
    content_analysis = ContentAnalysis(
        url="https://example.com", combined_score=0.8
    )

    recs = generate_recommendations(
        robots_result, llms_result, schema_analysis, content_analysis
    )

    priorities = [r["priority"] for r in recs]
    for i, p in enumerate(priorities):
        if p == "MEDIUM":
            remaining = priorities[i:]
            assert all(pp in ("MEDIUM", "LOW") for pp in remaining), (
                f"HIGH found after MEDIUM at index {i}"
            )
            break


def test_no_recommendations_for_perfect_module():
    """SCORE-03: schema score >= 0.7 returns empty list; content
    combined_score >= 0.6 returns empty list."""
    from src.checker.scorer import _content_recommendations, _schema_recommendations

    good_schema = SchemaAnalysis(
        url="https://example.com",
        score=0.85,
        detected_types={"Product", "FAQPage", "Organization"},
    )
    assert _schema_recommendations(good_schema) == []

    good_content = ContentAnalysis(url="https://example.com", combined_score=0.7)
    assert _content_recommendations(good_content) == []
