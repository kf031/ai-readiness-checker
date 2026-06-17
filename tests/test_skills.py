"""Tests for v2 skill discovery system and individual skill modules."""

import pytest
from checker.skills import list_skills, load_skill, execute_skill


def test_list_skills_returns_all_registered():
    skills = list_skills()
    expected = {
        "fix-schema", "fix-headings", "fix-readability",
        "fix-qa", "fix-llms-txt", "render-preview", "explain-changes"
    }
    assert expected == set(skills)
    assert len(skills) == 7


def test_load_skill_unknown_raises():
    with pytest.raises(ValueError, match="Unknown skill"):
        load_skill("nonexistent-skill")


def test_load_skill_returns_callable():
    skill = load_skill("fix-schema")
    assert callable(skill.execute)
    assert skill.SKILL_NAME == "fix-schema"


# --- fix-schema ---

def test_fix_schema_has_correct_name():
    from checker.skills.fix_schema import SKILL_NAME
    assert SKILL_NAME == "fix-schema"


def test_fix_schema_execute_returns_skill_result_structure():
    html = "<html><head></head><body><p>Buy our product. $19.99.</p></body></html>"
    report = {
        "modules": {
            "schema": {
                "score": 0.3,
                "types_found": ["Product"],
                "types_missing": ["FAQPage", "BreadcrumbList"]
            }
        }
    }
    result = execute_skill("fix-schema", html=html, report=report)
    assert "changes" in result
    assert "modified_html" in result
    assert "target" in result
    assert result["target"] == "head"
    assert len(result["changes"]) == 2
    assert "FAQPage" in result["modified_html"]


def test_fix_schema_no_missing_types():
    html = "<html><head></head><body></body></html>"
    report = {"modules": {"schema": {"score": 1.0, "types_found": [], "types_missing": []}}}
    result = execute_skill("fix-schema", html=html, report=report)
    assert result["changes"] == []
    assert result["modified_html"] == html


# --- fix-headings ---

def test_fix_headings_has_correct_name():
    from checker.skills.fix_headings import SKILL_NAME
    assert SKILL_NAME == "fix-headings"


def test_fix_headings_detects_duplicate_h1():
    html = "<html><body><h1>Welcome</h1><h1>Also Welcome</h1><h2>Details</h2></body></html>"
    report = {
        "modules": {
            "content": {
                "headings": {"score": 0.3, "h1_count": 2, "issues": ["Multiple H1s"]}
            }
        }
    }
    result = execute_skill("fix-headings", html=html, report=report)
    assert len(result["changes"]) > 0
    assert "H1" in result["changes"][0]
    assert result["target"] == "body"


def test_fix_headings_no_issues():
    html = "<html><body><h1>Welcome</h1><h2>Details</h2></body></html>"
    report = {"modules": {"content": {"headings": {"score": 1.0, "issues": []}}}}
    result = execute_skill("fix-headings", html=html, report=report)
    assert result["changes"] == []


# --- fix-readability ---

def test_fix_readability_has_correct_name():
    from checker.skills.fix_readability import SKILL_NAME
    assert SKILL_NAME == "fix-readability"


def test_fix_readability_identifies_long_sentences():
    html = "<html><body><p>This is a very long sentence that goes on and on and on and on for way too many words without any break in between whatsoever which makes it incredibly difficult to read and understand for the average reader on the web.</p></body></html>"
    report = {
        "modules": {
            "content": {
                "readability": {"score": 0.2, "flesch_reading_ease": 25.0}
            }
        }
    }
    result = execute_skill("fix-readability", html=html, report=report)
    assert len(result["changes"]) > 0


def test_fix_readability_passes_when_score_ok():
    html = "<html><body><p>Short text.</p></body></html>"
    report = {"modules": {"content": {"readability": {"score": 0.8}}}}
    result = execute_skill("fix-readability", html=html, report=report)
    assert result["changes"] == []


# --- fix-qa ---

def test_fix_qa_has_correct_name():
    from checker.skills.fix_qa import SKILL_NAME
    assert SKILL_NAME == "fix-qa"


def test_fix_qa_suggests_qa_when_density_low():
    html = "<html><body><h1>Product Info</h1><p>Our product is the best.</p></body></html>"
    report = {
        "modules": {
            "content": {
                "qa_density": {"score": 0.1, "question_count": 0}
            }
        }
    }
    result = execute_skill("fix-qa", html=html, report=report)
    assert len(result["changes"]) > 0
    assert "Q&A" in result["changes"][0] or "question" in result["changes"][0].lower()


def test_fix_qa_passes_when_score_ok():
    html = "<html><body></body></html>"
    report = {"modules": {"content": {"qa_density": {"score": 0.8}}}}
    result = execute_skill("fix-qa", html=html, report=report)
    assert result["changes"] == []


# --- fix-llms-txt ---

def test_fix_llms_txt_has_correct_name():
    from checker.skills.fix_llms_txt import SKILL_NAME
    assert SKILL_NAME == "fix-llms-txt"


def test_fix_llms_txt_generates_from_page_content():
    html = "<html><head><title>My Site</title></head><body><h1>My Site</h1><p>We sell amazing things.</p></body></html>"
    report = {
        "modules": {
            "llms_txt": {"score": 0.0}
        }
    }
    result = execute_skill("fix-llms-txt", html=html, report=report)
    assert len(result["changes"]) > 0
    assert "llms.txt" in result["changes"][0].lower()


# --- render-preview ---

def test_render_preview_has_correct_name():
    from checker.skills.render_preview import SKILL_NAME
    assert SKILL_NAME == "render-preview"


def test_render_preview_produces_diff_html():
    original = "<html><body><h1>Old Title</h1></body></html>"
    improved = "<html><body><h1>New Title</h1></body></html>"
    report = {"url": "https://example.com"}
    result = execute_skill("render-preview", html=original, report=report, improved_html=improved)
    assert "changes" in result
    assert len(result["changes"]) > 0


def test_render_preview_no_improved_html():
    original = "<html><body></body></html>"
    report = {"url": "https://example.com"}
    result = execute_skill("render-preview", html=original, report=report)
    assert result["modified_html"] == original


# --- explain-changes ---

def test_explain_changes_has_correct_name():
    from checker.skills.explain_changes import SKILL_NAME
    assert SKILL_NAME == "explain-changes"


def test_explain_changes_produces_summary():
    changes = [
        "Added FAQPage JSON-LD block",
        "Merged 2 H1s into single H1: 'Welcome'",
    ]
    report = {"url": "https://example.com", "overall_score": 55, "grade": "C"}
    result = execute_skill("explain-changes", html="<html></html>", report=report, changes=changes)
    assert "summary" in result
    assert "Changes Made" in result["summary"]


def test_explain_changes_no_changes():
    report = {"url": "https://example.com", "overall_score": 100, "grade": "A"}
    result = execute_skill("explain-changes", html="<html></html>", report=report)
    assert result["summary"] == "No changes were needed."
