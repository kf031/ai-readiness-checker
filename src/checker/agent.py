"""
v2 LLM Advisor Agent — decides which fix skills to invoke, merges results,
and produces final AgentOutput with improved HTML, diff, and explanation.

The agent is a lightweight loop: it takes the v1 scoring report and original
HTML, checks each module's score against a 0.5 threshold, invokes the
corresponding fix skills, and assembles the final output.
"""

import re

from checker.contracts import AgentOutput
from checker.skills import execute_skill


def build_agent_report(pipeline_result: dict) -> dict:
    """Build the rich report dict needed by the agent from pipeline output.

    Converts the orchestrator's raw module objects (RobotsResult, LlmsResult,
    SchemaAnalysis, ContentAnalysis, ScoreReport) into the nested dict
    structure that fix skills expect.

    Args:
        pipeline_result: Dict returned by orchestrator.run_pipeline().
            Must have keys: report, robots_result, llms_result,
            schema_analysis, content_analysis.

    Returns:
        Dict with url, overall_score, grade, and modules (nested per-module
        scores with per-component details for content sub-signals).
    """
    report = pipeline_result["report"]
    robots = pipeline_result.get("robots_result")
    llms = pipeline_result.get("llms_result")
    schema = pipeline_result.get("schema_analysis")
    content = pipeline_result.get("content_analysis")

    # Determine missing schema types
    from checker.schema_analyzer import TARGET_TYPES
    types_found = list(schema.detected_types) if schema else []
    types_missing = [t for t in TARGET_TYPES if t not in (types_found or [])]

    # Determine heading issues
    heading_issues = []
    if content and content.heading_analysis:
        ha = content.heading_analysis
        if ha.get("h1_count", 1) > 1:
            heading_issues.append("Multiple H1s")
        if ha.get("hierarchy_violations", 0) > 0:
            heading_issues.append("Missing H2 hierarchy")

    # Compute robots score (RobotsResult has no .score attribute directly)
    if robots is not None and hasattr(robots, 'bots'):
        from checker.robots_txt import compute_bot_score
        robots_score = compute_bot_score(robots.bots)
    else:
        robots_score = 0.0

    # Compute llms score (compute_llms_score takes found + valid, not LlmsResult)
    if llms is not None and hasattr(llms, 'found'):
        from checker.llms_txt import compute_llms_score
        llms_score = compute_llms_score(llms.found, llms.valid)
    else:
        llms_score = 0.0

    return {
        "url": getattr(report, "url", ""),
        "overall_score": getattr(report, "overall_score", 0),
        "grade": getattr(report, "grade", "N/A"),
        "modules": {
            "robots": {
                "score": robots_score,
                "details": {"exists": _safe_attr(robots, "exists")},
            },
            "llms_txt": {
                "score": llms_score,
                "details": {"found": _safe_attr(llms, "found")},
            },
            "schema": {
                "score": _safe_attr(schema, "score", 0.0),
                "types_found": types_found,
                "types_missing": types_missing,
            },
            "content": {
                "score": _safe_attr(content, "combined_score", 0.0),
                "readability": {
                    "score": _safe_attr(content, "readability_score", 0.0),
                    "flesch_reading_ease": _safe_attr(content, "flesch_raw", 0.0),
                },
                "headings": {
                    "score": _safe_attr(content, "heading_score", 0.0),
                    "h1_count": (_safe_attr(content, "heading_analysis") or {}).get("h1_count", 0),
                    "issues": heading_issues,
                },
                "qa_density": {
                    "score": _safe_attr(content, "qa_density_score", 0.0),
                    "question_count": (_safe_attr(content, "qa_analysis") or {}).get("question_count", 0),
                },
                "text_ratio": {
                    "score": _safe_attr(content, "text_ratio", 0.0),
                    "ratio": _safe_attr(content, "raw_text_ratio", 0.0),
                },
                "entity_score": _safe_attr(content, "entity_score", 0.0),
            },
        },
    }


def _safe_attr(obj, attr: str, default=None):
    """Safely get an attribute from an object that may be None."""
    if obj is None:
        return default
    return getattr(obj, attr, default)

# Skill trigger map: skill_name -> lambda that returns True if skill should run
_SKILL_TRIGGERS = {
    "fix-schema": lambda r: r.get("modules", {}).get("schema", {}).get("score", 1.0) < 0.5,
    "fix-headings": lambda r: r.get("modules", {}).get("content", {}).get("headings", {}).get("score", 1.0) < 0.5,
    "fix-readability": lambda r: r.get("modules", {}).get("content", {}).get("readability", {}).get("score", 1.0) < 0.5,
    "fix-qa": lambda r: r.get("modules", {}).get("content", {}).get("qa_density", {}).get("score", 1.0) < 0.5,
    "fix-llms-txt": lambda r: r.get("modules", {}).get("llms_txt", {}).get("score", 1.0) < 0.5,
}


def decide_skills(report: dict) -> list[str]:
    """Decide which fix skills to invoke based on module scores.

    A skill is selected when its corresponding module score is below 0.5.
    Scores at or above 0.5 are considered passing and skip the fix.

    Args:
        report: Dict with structure matching ScoreReport JSON output.
            Must have a "modules" key with per-module score dicts.

    Returns:
        List of skill names to invoke, in deterministic order.
    """
    return [name for name, trigger in _SKILL_TRIGGERS.items() if trigger(report)]


def merge_results(results: list[dict], base_html: str) -> tuple[str, list[str]]:
    """Merge multiple skill results into a single improved HTML.

    Composes changes by target:
    - "head" results: merge <head> content from the head-target result
    - "body"/"full" results: take the last result's modified_html
    - All changes from all results are collected into one flat list

    Args:
        results: List of skill result dicts (each with changes, modified_html, target).
        base_html: The original HTML to start from.

    Returns:
        Tuple of (merged_html, all_changes_list).
    """
    modified = base_html
    all_changes: list[str] = []
    head_results: list[dict] = []
    body_results: list[dict] = []

    for result in results:
        all_changes.extend(result.get("changes", []))
        target = result.get("target", "full")
        if target == "head":
            head_results.append(result)
        elif target == "full":
            body_results.append(result)
        else:
            body_results.append(result)

    # Apply body/full results in order (last one wins for full replacement)
    for result in body_results:
        modified = result.get("modified_html", modified)

    # Apply head results — merge their <head> content into the body-modified HTML
    for result in head_results:
        modified = _merge_head_change(modified, result.get("modified_html", ""))

    return modified, all_changes


def _merge_head_change(base: str, head_source: str) -> str:
    """Merge <head> content from head_source into base HTML."""
    head_match = re.search(
        r"<head[^>]*>(.*?)</head>", head_source, re.DOTALL | re.IGNORECASE
    )
    if not head_match:
        return base
    new_head_content = head_match.group(1)
    return re.sub(
        r"(<head[^>]*>)(.*?)(</head>)",
        lambda m: m.group(1) + new_head_content + m.group(3),
        base,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )


def run_llm_agent(report: dict, html: str, backend=None) -> AgentOutput:
    """Run the full agent pipeline: decide skills, invoke, merge, render, explain.

    Args:
        report: v1 scoring report dict (as returned by orchestrator).
        html: Original page HTML string.
        backend: Optional LLMBackend instance (v3). When provided, skills can
            use the LLM to generate better fixes instead of templates alone.

    Returns:
        AgentOutput with improved_html, diff_html, explanation, skills_called, changes.
    """
    skill_names = decide_skills(report)

    results = []
    for name in skill_names:
        try:
            kwargs = {}
            if backend is not None:
                kwargs["backend"] = backend
            result = execute_skill(name, html=html, report=report, **kwargs)
            results.append(result)
        except Exception:
            # If a skill fails, skip it and continue with others
            pass

    improved, all_changes = merge_results(results, base_html=html)

    # Render before/after preview
    preview_result = execute_skill(
        "render-preview", html=html, report=report, improved_html=improved
    )

    # Generate change explanations
    explain_result = execute_skill(
        "explain-changes", html=html, report=report, changes=all_changes
    )

    return AgentOutput(
        improved_html=improved,
        diff_html=preview_result.get("modified_html", ""),
        explanation=explain_result.get("summary", ""),
        skills_called=skill_names,
        changes=all_changes,
    )
