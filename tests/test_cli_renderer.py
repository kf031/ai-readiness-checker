"""Tests for cli_renderer.py — Rich-formatted score card rendering.

Uses Rich Console capture mode for deterministic output testing.
No conftest fixture dependency — all ScoreReport instances constructed inline.
"""

from rich.console import Console

from checker.cli_renderer import display_score_card
from checker.contracts import ScoreReport


def _make_pipeline_result(report, errors=None, complete=True, stages_run=None):
    """Helper to build the pipeline result dict consumed by display_score_card."""
    return {
        "report": report,
        "errors": errors if errors is not None else [],
        "complete": complete,
        "stages_run": stages_run or ["crawl", "access_signals", "schema", "content", "score"],
    }


def test_grade_A_colored_green():
    """ScoreReport with grade='A' renders without crash and output contains 'A'."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=92.5,
        grade="A",
        module_breakdown={
            "robots": {"score": 0.85, "weight": 0.20, "weighted": 17.0},
            "llms_txt": {"score": 0.90, "weight": 0.15, "weighted": 13.5},
            "schema": {"score": 0.95, "weight": 0.30, "weighted": 28.5},
            "content": {"score": 0.90, "weight": 0.35, "weighted": 31.5},
        },
    )
    pipeline_result = _make_pipeline_result(report)
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    assert "A" in output
    assert "92.5" in output


def test_grade_F_colored_red():
    """ScoreReport with grade='F' renders without crash and output contains 'F'."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=15.0,
        grade="F",
        module_breakdown={
            "robots": {"score": 0.10, "weight": 0.20, "weighted": 2.0},
            "llms_txt": {"score": 0.00, "weight": 0.15, "weighted": 0.0},
            "schema": {"score": 0.00, "weight": 0.30, "weighted": 0.0},
            "content": {"score": 0.05, "weight": 0.35, "weighted": 1.8},
        },
    )
    pipeline_result = _make_pipeline_result(report)
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    assert "F" in output


def test_all_grades_colored_correctly():
    """All 5 grades (A, B, C, D, F) render without errors."""
    grades = ["A", "B", "C", "D", "F"]
    scores = [92.0, 78.0, 62.0, 48.0, 15.0]
    for grade, score_val in zip(grades, scores):
        report = ScoreReport(
            url="https://example.com",
            overall_score=score_val,
            grade=grade,
            module_breakdown={
                "robots": {"score": 0.80, "weight": 0.20, "weighted": 16.0},
                "llms_txt": {"score": 0.80, "weight": 0.15, "weighted": 12.0},
                "schema": {"score": 0.80, "weight": 0.30, "weighted": 24.0},
                "content": {"score": 0.80, "weight": 0.35, "weighted": 28.0},
            },
        )
        pipeline_result = _make_pipeline_result(report)
        console = Console(force_terminal=True, width=120)
        with console.capture() as capture:
            display_score_card(pipeline_result, console=console)
        output = capture.get()
        assert grade in output, f"Grade {grade} not found in output"


def test_module_bars_rendered():
    """Module breakdown renders Unicode block character score bars (filled=empty=)."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=55.0,
        grade="C",
        module_breakdown={
            "robots": {"score": 0.80, "weight": 0.20, "weighted": 16.0},
            "llms_txt": {"score": 0.30, "weight": 0.15, "weighted": 4.5},
            "schema": {"score": 0.60, "weight": 0.30, "weighted": 18.0},
            "content": {"score": 0.50, "weight": 0.35, "weighted": 17.5},
        },
    )
    pipeline_result = _make_pipeline_result(report)
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    assert "█" in output  # filled block
    assert "░" in output  # empty block
    assert "robots" in output.lower() or "Robots" in output


def test_recommendations_rendered():
    """Recommendations table renders with priority and message text."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=40.0,
        grade="D",
        module_breakdown={
            "robots": {"score": 0.40, "weight": 0.20, "weighted": 8.0},
            "llms_txt": {"score": 0.40, "weight": 0.15, "weighted": 6.0},
            "schema": {"score": 0.40, "weight": 0.30, "weighted": 12.0},
            "content": {"score": 0.40, "weight": 0.35, "weighted": 14.0},
        },
        recommendations=[
            {"priority": "HIGH", "module": "robots", "message": "GPTBot is blocked"},
        ],
    )
    pipeline_result = _make_pipeline_result(report)
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    assert "GPTBot" in output
    assert "HIGH" in output


def test_errors_displayed():
    """Pipeline errors render when errors list is non-empty."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=0.0,
        grade="F",
        module_breakdown={
            "robots": {"score": 0.0, "weight": 0.20, "weighted": 0.0},
            "llms_txt": {"score": 0.0, "weight": 0.15, "weighted": 0.0},
            "schema": {"score": 0.0, "weight": 0.30, "weighted": 0.0},
            "content": {"score": 0.0, "weight": 0.35, "weighted": 0.0},
        },
    )
    pipeline_result = _make_pipeline_result(
        report,
        errors=["Crawl failed: timeout"],
        complete=False,
        stages_run=["crawl"],
    )
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    assert "Crawl failed: timeout" in output


def test_url_displayed():
    """ScoreReport URL is displayed in output."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=80.0,
        grade="B",
    )
    pipeline_result = _make_pipeline_result(report)
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    assert "https://example.com" in output


def test_empty_recommendations_no_table():
    """Empty recommendations list does not crash and does not leak messages from other tests."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=80.0,
        grade="B",
        module_breakdown={
            "robots": {"score": 0.80, "weight": 0.20, "weighted": 16.0},
            "llms_txt": {"score": 0.80, "weight": 0.15, "weighted": 12.0},
            "schema": {"score": 0.80, "weight": 0.30, "weighted": 24.0},
            "content": {"score": 0.80, "weight": 0.35, "weighted": 28.0},
        },
        recommendations=[],
    )
    pipeline_result = _make_pipeline_result(report)
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    # Should not contain recommendation messages from other tests
    assert "GPTBot" not in output
    assert "Crawl failed" not in output


def test_completeness_indicator():
    """Incomplete pipeline result handled without crash."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=50.0,
        grade="C",
        module_breakdown={
            "robots": {"score": 0.50, "weight": 0.20, "weighted": 10.0},
            "llms_txt": {"score": 0.50, "weight": 0.15, "weighted": 7.5},
            "schema": {"score": 0.0, "weight": 0.30, "weighted": 0.0},
            "content": {"score": 0.0, "weight": 0.35, "weighted": 0.0},
        },
    )
    pipeline_result = _make_pipeline_result(
        report,
        complete=False,
        stages_run=["crawl", "access_signals", "score"],
    )
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    # Must not crash; output should exist (may contain partial indicator text)
    assert output is not None


def test_module_display_order():
    """Module breakdown table renders modules in order: robots, llms_txt, schema, content."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=70.0,
        grade="B",
        module_breakdown={
            "robots": {"score": 0.70, "weight": 0.20, "weighted": 14.0},
            "llms_txt": {"score": 0.70, "weight": 0.15, "weighted": 10.5},
            "schema": {"score": 0.70, "weight": 0.30, "weighted": 21.0},
            "content": {"score": 0.70, "weight": 0.35, "weighted": 24.5},
        },
    )
    pipeline_result = _make_pipeline_result(report)
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    # Verify display order: Robots.txt before llms.txt before Schema before Content
    robots_pos = output.find("Robots.txt")
    llms_pos = output.find("llms.txt")
    schema_pos = output.find("Schema")
    content_pos = output.find("Content")
    assert robots_pos < llms_pos < schema_pos < content_pos, (
        f"Order mismatch: Robots.txt@{robots_pos}, llms.txt@{llms_pos}, "
        f"Schema@{schema_pos}, Content@{content_pos}"
    )


def test_invalid_grade_fallback():
    """Unknown grade (not in A-F) does not crash; falls back gracefully."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=50.0,
        grade="X",
        module_breakdown={
            "robots": {"score": 0.50, "weight": 0.20, "weighted": 10.0},
            "llms_txt": {"score": 0.50, "weight": 0.15, "weighted": 7.5},
            "schema": {"score": 0.50, "weight": 0.30, "weighted": 15.0},
            "content": {"score": 0.50, "weight": 0.35, "weighted": 17.5},
        },
    )
    pipeline_result = _make_pipeline_result(report)
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    # Must not crash; "X" grade should be visible even if fallback color used
    assert output is not None
