"""Tests for orchestrator.py — covers pipeline execution, CrawlError handling, module failure recovery."""

from unittest.mock import Mock, patch

import pytest

from checker.contracts import (
    ContentAnalysis,
    FetchResult,
    LlmsResult,
    RobotsResult,
    SchemaAnalysis,
    ScoreReport,
)
from checker.orchestrator import run_pipeline


# ----- Test 1: Full success pipeline -----

def test_pipeline_full_success(sample_robots_result, sample_llms_result,
                               sample_schema_analysis, sample_content_analysis):
    """Verify run_pipeline() returns complete dict with all 5 stages on success."""
    with patch("checker.orchestrator.fetch_url") as mock_fetch, \
         patch("checker.orchestrator.fetch_access_signals") as mock_access, \
         patch("checker.orchestrator.analyze_schema") as mock_schema, \
         patch("checker.orchestrator.analyze_content") as mock_content, \
         patch("checker.orchestrator.generate_report") as mock_score:

        mock_fetch.return_value = FetchResult(
            url="https://example.com", final_url="https://example.com",
            status_code=200, html="<html></html>",
            soup=Mock(),
        )
        mock_access.return_value = (sample_robots_result, sample_llms_result)
        mock_schema.return_value = sample_schema_analysis
        mock_content.return_value = sample_content_analysis
        mock_score.return_value = ScoreReport(
            url="https://example.com", overall_score=75.0, grade="B",
            module_breakdown={}, recommendations=[],
        )

        result = run_pipeline("https://example.com")

        assert isinstance(result, dict)
        assert set(result.keys()) == {
            "report", "errors", "complete", "stages_run",
            "robots_result", "llms_result", "schema_analysis", "content_analysis",
            "fetch_result",
        }
        assert isinstance(result["robots_result"], RobotsResult)
        assert isinstance(result["llms_result"], LlmsResult)
        assert isinstance(result["schema_analysis"], SchemaAnalysis)
        assert isinstance(result["content_analysis"], ContentAnalysis)
        assert result["complete"] is True
        assert result["stages_run"] == ["crawl", "access_signals", "schema", "content", "score"]
        assert isinstance(result["report"], ScoreReport)
        assert result["report"].url == "https://example.com"


# ----- Test 2: CrawlError handling (schema/content skipped) -----

def test_pipeline_crawl_error(sample_robots_result, sample_llms_result,
                               sample_crawl_error):
    """CrawlError skips schema/content but still runs access signals and scoring."""
    with patch("checker.orchestrator.fetch_url") as mock_fetch, \
         patch("checker.orchestrator.fetch_access_signals") as mock_access, \
         patch("checker.orchestrator.analyze_schema") as mock_schema, \
         patch("checker.orchestrator.analyze_content") as mock_content, \
         patch("checker.orchestrator.generate_report") as mock_score:

        mock_fetch.return_value = sample_crawl_error
        mock_access.return_value = (sample_robots_result, sample_llms_result)
        mock_score.return_value = ScoreReport(
            url="https://example.com", overall_score=20.0, grade="F",
            module_breakdown={}, recommendations=[],
        )

        result = run_pipeline("https://example.com")

        assert result["complete"] is False
        assert "schema" not in result["stages_run"]
        assert "content" not in result["stages_run"]
        assert "crawl" in result["stages_run"]
        assert "access_signals" in result["stages_run"]
        assert "score" in result["stages_run"]
        assert any("timed out" in err for err in result["errors"])
        assert isinstance(result["report"], ScoreReport)
        assert result["report"].module_breakdown is not None

        # Schema and content analysis should NOT have been called
        mock_schema.assert_not_called()
        mock_content.assert_not_called()

        # Raw module objects should still be present (as empty fallbacks)
        assert isinstance(result["robots_result"], RobotsResult)
        assert isinstance(result["llms_result"], LlmsResult)
        assert isinstance(result["schema_analysis"], SchemaAnalysis)
        assert isinstance(result["content_analysis"], ContentAnalysis)


# ----- Test 3: Access signals failure (zero-score fallback) -----

def test_pipeline_access_signals_failure(
    sample_schema_analysis, sample_content_analysis
):
    """Access signals failure produces zero-score fallback, pipeline continues."""
    with patch("checker.orchestrator.fetch_url") as mock_fetch, \
         patch("checker.orchestrator.fetch_access_signals") as mock_access, \
         patch("checker.orchestrator.analyze_schema") as mock_schema, \
         patch("checker.orchestrator.analyze_content") as mock_content, \
         patch("checker.orchestrator.generate_report") as mock_score:

        mock_fetch.return_value = FetchResult(
            url="https://example.com", final_url="https://example.com",
            status_code=200, html="<html></html>",
            soup=Mock(),
        )
        mock_access.side_effect = RuntimeError("network down")
        mock_schema.return_value = sample_schema_analysis
        mock_content.return_value = sample_content_analysis
        mock_score.return_value = ScoreReport(
            url="https://example.com", overall_score=50.0, grade="D",
            module_breakdown={"robots": {"score": 0.0, "weight": 0.20, "weighted": 0.0}},
            recommendations=[],
        )

        result = run_pipeline("https://example.com")

        # Pipeline should not crash
        assert isinstance(result, dict)
        assert any("Access signals failed" in err for err in result["errors"])
        # Schema and content should still run
        mock_schema.assert_called_once()
        mock_content.assert_called_once()
        # robots_score should still exist (zero-score fallback objects were passed to generate_report)
        assert "robots" in result["report"].module_breakdown


# ----- Test 4: Schema analysis failure -----

def test_pipeline_schema_failure(
    sample_robots_result, sample_llms_result,
    sample_content_analysis,
):
    """Schema failure produces zero-score fallback, pipeline continues to content + score."""
    with patch("checker.orchestrator.fetch_url") as mock_fetch, \
         patch("checker.orchestrator.fetch_access_signals") as mock_access, \
         patch("checker.orchestrator.analyze_schema") as mock_schema, \
         patch("checker.orchestrator.analyze_content") as mock_content, \
         patch("checker.orchestrator.generate_report") as mock_score:

        mock_fetch.return_value = FetchResult(
            url="https://example.com", final_url="https://example.com",
            status_code=200, html="<html></html>",
            soup=Mock(),
        )
        mock_access.return_value = (sample_robots_result, sample_llms_result)
        mock_schema.side_effect = ValueError("extruct failed")
        mock_content.return_value = sample_content_analysis
        mock_score.return_value = ScoreReport(
            url="https://example.com", overall_score=40.0, grade="D",
            module_breakdown={"schema": {"score": 0.0, "weight": 0.30, "weighted": 0.0}},
            recommendations=[],
        )

        result = run_pipeline("https://example.com")

        assert any("Schema analysis failed" in err for err in result["errors"])
        assert "schema" in result["stages_run"]
        mock_content.assert_called_once()
        mock_score.assert_called_once()


# ----- Test 5: Content analysis failure -----

def test_pipeline_content_failure(
    sample_robots_result, sample_llms_result,
    sample_schema_analysis,
):
    """Content failure produces zero-score fallback, pipeline still runs score stage."""
    with patch("checker.orchestrator.fetch_url") as mock_fetch, \
         patch("checker.orchestrator.fetch_access_signals") as mock_access, \
         patch("checker.orchestrator.analyze_schema") as mock_schema, \
         patch("checker.orchestrator.analyze_content") as mock_content, \
         patch("checker.orchestrator.generate_report") as mock_score:

        mock_fetch.return_value = FetchResult(
            url="https://example.com", final_url="https://example.com",
            status_code=200, html="<html></html>",
            soup=Mock(),
        )
        mock_access.return_value = (sample_robots_result, sample_llms_result)
        mock_schema.return_value = sample_schema_analysis
        mock_content.side_effect = RuntimeError("spaCy model missing")
        mock_score.return_value = ScoreReport(
            url="https://example.com", overall_score=30.0, grade="F",
            module_breakdown={"content": {"score": 0.0, "weight": 0.35, "weighted": 0.0}},
            recommendations=[],
        )

        result = run_pipeline("https://example.com")

        assert any("Content analysis failed" in err for err in result["errors"])
        assert "content" in result["stages_run"]
        mock_score.assert_called_once()


# ----- Test 6: Stages run in exact order -----

def test_pipeline_stages_run_order(
    sample_robots_result, sample_llms_result,
    sample_schema_analysis, sample_content_analysis,
):
    """Verify stages_run list preserves exact execution order."""
    with patch("checker.orchestrator.fetch_url") as mock_fetch, \
         patch("checker.orchestrator.fetch_access_signals") as mock_access, \
         patch("checker.orchestrator.analyze_schema") as mock_schema, \
         patch("checker.orchestrator.analyze_content") as mock_content, \
         patch("checker.orchestrator.generate_report") as mock_score:

        mock_fetch.return_value = FetchResult(
            url="https://example.com", final_url="https://example.com",
            status_code=200, html="<html></html>",
            soup=Mock(),
        )
        mock_access.return_value = (sample_robots_result, sample_llms_result)
        mock_schema.return_value = sample_schema_analysis
        mock_content.return_value = sample_content_analysis
        mock_score.return_value = ScoreReport(
            url="https://example.com", overall_score=80.0, grade="B",
            module_breakdown={}, recommendations=[],
        )

        result = run_pipeline("https://example.com")

        assert result["stages_run"] == ["crawl", "access_signals", "schema", "content", "score"]


# ----- Test 7: Fallback objects compatible with generate_report -----

def test_pipeline_fallback_objects_compatible_with_generate_report():
    """Verify fallback objects with minimal fields don't cause AttributeError/KeyError in generate_report."""
    from checker.scorer import generate_report

    robots_result = RobotsResult(url="https://example.com", exists=False)
    llms_result = LlmsResult(url="https://example.com", found=False)
    schema_analysis = SchemaAnalysis(url="https://example.com")
    content_analysis = ContentAnalysis(url="https://example.com")

    try:
        report = generate_report(
            "https://example.com",
            robots_result,
            llms_result,
            schema_analysis,
            content_analysis,
        )
    except (AttributeError, KeyError) as e:
        pytest.fail(f"Fallback objects caused unexpected error in generate_report: {e}")

    assert hasattr(report, "overall_score")
    assert hasattr(report, "grade")
    assert isinstance(report.overall_score, (int, float))


# ----- Test 8: Multiple module failures -----

def test_pipeline_multi_module_failure():
    """Multiple module failures produce multiple error messages without crashing."""
    with patch("checker.orchestrator.fetch_url") as mock_fetch, \
         patch("checker.orchestrator.fetch_access_signals") as mock_access, \
         patch("checker.orchestrator.analyze_schema") as mock_schema, \
         patch("checker.orchestrator.analyze_content") as mock_content, \
         patch("checker.orchestrator.generate_report") as mock_score:

        mock_fetch.return_value = FetchResult(
            url="https://example.com", final_url="https://example.com",
            status_code=200, html="<html></html>",
            soup=Mock(),
        )
        mock_access.side_effect = RuntimeError("network unreachable")
        mock_schema.return_value = SchemaAnalysis(url="https://example.com", score=0.5)
        mock_content.side_effect = ValueError("textstat error")
        mock_score.return_value = ScoreReport(
            url="https://example.com", overall_score=15.0, grade="F",
            module_breakdown={
                "robots": {"score": 0.0, "weight": 0.20, "weighted": 0.0},
                "content": {"score": 0.0, "weight": 0.35, "weighted": 0.0},
            },
            recommendations=[],
        )

        result = run_pipeline("https://example.com")

        # Should have TWO error messages
        access_errors = [e for e in result["errors"] if "Access signals" in e]
        content_errors = [e for e in result["errors"] if "Content analysis" in e]
        assert len(access_errors) >= 1
        assert len(content_errors) >= 1
        # stages_run should still contain all expected stages
        assert "access_signals" in result["stages_run"]
        assert "content" in result["stages_run"]
        assert "score" in result["stages_run"]
