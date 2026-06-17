"""Skill discovery and execution for v2 LLM Advisor agent.

Each skill is a Python module in this package with:
    SKILL_NAME: str — unique name (e.g., "fix-schema")
    SKILL_DESCRIPTION: str — human-readable description
    execute(html: str, report: dict, **kwargs) -> dict

The agent discovers skills via _SKILL_REGISTRY and invokes them
via execute_skill().
"""

import importlib
from typing import Callable

_SKILL_REGISTRY: dict[str, str] = {
    "fix-schema":        "checker.skills.fix_schema",
    "fix-headings":      "checker.skills.fix_headings",
    "fix-readability":   "checker.skills.fix_readability",
    "fix-qa":            "checker.skills.fix_qa",
    "fix-llms-txt":      "checker.skills.fix_llms_txt",
    "render-preview":    "checker.skills.render_preview",
    "explain-changes":   "checker.skills.explain_changes",
}


def list_skills() -> list[str]:
    """Return sorted list of all registered skill names."""
    return sorted(_SKILL_REGISTRY.keys())


def load_skill(name: str) -> Callable:
    """Load a skill module by name. Returns the module object.

    Raises ValueError if the skill name is unknown.
    Raises ModuleNotFoundError if the skill module hasn't been created yet.
    """
    module_path = _SKILL_REGISTRY.get(name)
    if module_path is None:
        raise ValueError(f"Unknown skill: {name}")
    module = importlib.import_module(module_path)
    return module


def execute_skill(name: str, html: str, report: dict, **kwargs) -> dict:
    """Load and execute a skill by name.

    Args:
        name: Skill name (e.g., "fix-schema").
        html: Full page HTML string to operate on.
        report: v1 scoring report dict (score, grade, per-module breakdown).
        **kwargs: Additional arguments passed to the skill's execute().

    Returns:
        Dict with keys: changes, modified_html, target.
    """
    skill = load_skill(name)
    return skill.execute(html=html, report=report, **kwargs)
