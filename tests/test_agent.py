"""Tests for v2 agent module — skill selection, merge, and orchestration."""

import pytest
from checker.agent import decide_skills, merge_results, run_llm_agent, build_agent_report
from checker.contracts import AgentOutput


REPORT_DICT_FIXTURE = {
    "url": "https://example.com",
    "overall_score": 55,
    "grade": "C",
    "modules": {
        "robots": {"score": 0.8},
        "llms_txt": {"score": 0.0},
        "schema": {
            "score": 0.3,
            "types_found": ["Product"],
            "types_missing": ["FAQPage", "BreadcrumbList"],
        },
        "content": {
            "score": 0.45,
            "readability": {"score": 0.5, "flesch_reading_ease": 35.2},
            "headings": {"score": 0.4, "h1_count": 2, "issues": ["Multiple H1s"]},
            "qa_density": {"score": 0.2, "question_count": 1},
        },
    },
}

HTML_FIXTURE = """<!DOCTYPE html>
<html>
<head><title>Test Page</title></head>
<body>
<h1>Welcome</h1>
<h1>Also Welcome</h1>
<p>This is a test page with some content that is fairly long and goes on for a while.</p>
</body>
</html>"""


def test_decide_skills_selects_based_on_threshold():
    skills = decide_skills(REPORT_DICT_FIXTURE)
    assert "fix-schema" in skills, "Schema score < 0.5 should trigger fix-schema"
    assert "fix-headings" in skills, "Headings score < 0.5 should trigger fix-headings"
    assert "fix-qa" in skills, "QA score < 0.5 should trigger fix-qa"
    assert "fix-llms-txt" in skills, "llms score < 0.5 should trigger fix-llms-txt"
    # readability is exactly 0.5 — threshold is < 0.5, so should NOT trigger
    assert "fix-readability" not in skills, "Readability at 0.5 should NOT trigger"


def test_decide_skills_none_when_all_pass():
    report = {
        "modules": {
            "robots": {"score": 1.0},
            "llms_txt": {"score": 1.0},
            "schema": {"score": 1.0, "types_found": [], "types_missing": []},
            "content": {
                "score": 1.0,
                "readability": {"score": 1.0},
                "headings": {"score": 1.0, "h1_count": 1, "issues": []},
                "qa_density": {"score": 1.0},
            },
        }
    }
    skills = decide_skills(report)
    assert skills == []


def test_merge_results_combines_head_and_body():
    results = [
        {"changes": ["Added FAQPage JSON-LD"], "modified_html": "<html><head><script>FAQ</script></head><body></body></html>", "target": "head"},
        {"changes": ["Fixed H1"], "modified_html": "<html><head></head><body><h1>Fixed</h1></body></html>", "target": "body"},
    ]
    merged, all_changes = merge_results(results, base_html=HTML_FIXTURE)
    assert "FAQ" in merged
    assert "Fixed" in merged
    assert len(all_changes) == 2


def test_merge_results_empty():
    merged, changes = merge_results([], base_html=HTML_FIXTURE)
    assert merged == HTML_FIXTURE
    assert changes == []


def test_run_llm_agent_produces_output():
    output = run_llm_agent(REPORT_DICT_FIXTURE, HTML_FIXTURE)
    assert isinstance(output, AgentOutput)
    assert output.improved_html
    # The explanation should contain the URL or score
    assert output.explanation
    assert len(output.skills_called) > 0
    assert len(output.changes) > 0


def test_run_llm_agent_no_failing_modules():
    report = {
        "url": "https://example.com",
        "overall_score": 100,
        "grade": "A",
        "modules": {
            "robots": {"score": 1.0},
            "llms_txt": {"score": 1.0},
            "schema": {"score": 1.0, "types_found": [], "types_missing": []},
            "content": {
                "score": 1.0,
                "readability": {"score": 1.0},
                "headings": {"score": 1.0, "h1_count": 1, "issues": []},
                "qa_density": {"score": 1.0},
            },
        },
    }
    output = run_llm_agent(report, HTML_FIXTURE)
    assert output.skills_called == []
    assert output.changes == []


# --- build_agent_report ---

def test_build_agent_report_from_pipeline_result():
    """build_agent_report constructs the right dict shape from pipeline output."""
    from checker.contracts import (
        ScoreReport, RobotsResult, LlmsResult, SchemaAnalysis, ContentAnalysis, CrawlError
    )

    pipeline = {
        "report": ScoreReport(url="https://example.com", overall_score=62, grade="C"),
        "robots_result": RobotsResult(url="https://example.com", exists=True, status_code=200),
        "llms_result": LlmsResult(url="https://example.com", found=False),
        "schema_analysis": SchemaAnalysis(
            url="https://example.com",
            detected_types={"Product"},
            score=0.3,
        ),
        "content_analysis": ContentAnalysis(
            url="https://example.com",
            readability_score=0.5,
            heading_score=0.4,
            qa_density_score=0.2,
            combined_score=0.45,
        ),
        "errors": [],
        "stages_run": ["crawl", "access_signals", "schema", "content", "score"],
    }
    report = build_agent_report(pipeline)
    assert report["url"] == "https://example.com"
    assert report["overall_score"] == 62
    assert report["modules"]["schema"]["score"] == 0.3
    assert "Product" in report["modules"]["schema"]["types_found"]
    assert report["modules"]["content"]["score"] == 0.45
    assert report["modules"]["content"]["headings"]["score"] == 0.4
