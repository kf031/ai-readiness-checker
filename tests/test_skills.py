"""Tests for v2 skill discovery system."""

import pytest
from src.checker.skills import list_skills, load_skill


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
