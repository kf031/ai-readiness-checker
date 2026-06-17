"""
Pipeline orchestrator — wires all five analysis phases into a single run_pipeline().

Composition layer: all module logic exists; this module just calls them
in order and handles the FetchResult | CrawlError union type at the
crawler boundary.
"""

from collections.abc import Callable

from checker.access_fetcher import fetch_access_signals
from checker.content_analyzer import analyze_content
from checker.contracts import (
    ContentAnalysis,
    CrawlError,
    LlmsResult,
    RobotsResult,
    SchemaAnalysis,
)
from checker.crawler import fetch_url
from checker.schema_analyzer import analyze_schema
from checker.scorer import generate_report


def run_pipeline(
    url: str,
    timeout: float = 10.0,
    verbose: bool = False,
    on_stage: Callable[[str, str, str | None], None] | None = None,
) -> dict:
    """Run the full AI readiness analysis pipeline.

    Calls all five stages in order: crawl, access_signals, schema,
    content, score. Handles CrawlError branching (skip schema/content
    when crawl fails) and individual module failure recovery (zero-score
    fallback objects instead of crashing).

    Args:
        url: The URL to analyze (e.g., "https://example.com").
        timeout: HTTP request timeout in seconds. Default 10.0.
        verbose: If True, print stage names as they execute.
        on_stage: Optional callback(stage_key, status, detail) for
            progress display. Called once with "running" before each
            stage and once with "done" after. ``detail`` is None for
            "running" and a human-readable summary for "done".

    Returns:
        Dict with keys:
        - report (ScoreReport): the generated score report
        - errors (list[str]): error messages from any failed stages
        - complete (bool): True if crawl succeeded and both schema/content ran
        - stages_run (list[str]): names of all stages that were attempted
        - robots_result (RobotsResult): raw robots.txt analysis (None replaced with empty fallback)
        - llms_result (LlmsResult): raw llms.txt analysis (None replaced with empty fallback)
        - schema_analysis (SchemaAnalysis): raw schema extraction result (None replaced with empty fallback)
        - content_analysis (ContentAnalysis): raw content analysis result (None replaced with empty fallback)
    """
    stages_run: list[str] = []
    errors: list[str] = []

    robots_result = None
    llms_result = None
    schema_analysis = None
    content_analysis = None

    def _stage_start(key: str):
        if on_stage:
            on_stage(key, "running", None)
        if verbose:
            labels = {
                "crawl": "Fetching page",
                "access_signals": "Checking robots.txt and llms.txt",
                "schema": "Analyzing structured data",
                "content": "Analyzing content quality",
                "score": "Generating score report",
            }
            print(f"[{key}] {labels.get(key, key)}...")

    def _stage_done(key: str, detail: str):
        if on_stage:
            on_stage(key, "done", detail)

    # ---- Stage 1: Crawl ----
    _stage_start("crawl")
    fetch_result = fetch_url(url, timeout=timeout)
    stages_run.append("crawl")

    if isinstance(fetch_result, CrawlError):
        errors.append(f"Crawl failed: {fetch_result.message}")
        _stage_done("crawl", f"Failed: {fetch_result.message}")
    else:
        size_kb = len(fetch_result.html) / 1024
        _stage_done("crawl", f"200 OK, {size_kb:.1f}KB")

    # ---- Stage 2: Access signals (always runs — fetches its own URLs) ----
    _stage_start("access_signals")
    try:
        robots_result, llms_result = fetch_access_signals(url, timeout=timeout)
    except Exception as e:
        errors.append(f"Access signals failed: {e}")
        robots_result = RobotsResult(url=url, exists=False, fetch_error=str(e))
        llms_result = LlmsResult(url=url, found=False, fetch_error=str(e))
    stages_run.append("access_signals")

    robots_detail = _robots_summary(robots_result)
    llms_detail = _llms_summary(llms_result)
    _stage_done("access_signals", f"robots.txt {robots_detail}, llms.txt {llms_detail}")

    # ---- Stage 3: Schema analysis (only if crawl succeeded) ----
    _stage_start("schema")
    if fetch_result is not None and not isinstance(fetch_result, CrawlError):
        try:
            schema_analysis = analyze_schema(fetch_result)
        except Exception as e:
            errors.append(f"Schema analysis failed: {e}")
            schema_analysis = SchemaAnalysis(url=url, score=0.0)
        stages_run.append("schema")
        _stage_done("schema", _schema_summary(schema_analysis))

    # ---- Stage 4: Content analysis (only if crawl succeeded) ----
    _stage_start("content")
    if fetch_result is not None and not isinstance(fetch_result, CrawlError):
        try:
            content_analysis = analyze_content(fetch_result)
        except Exception as e:
            errors.append(f"Content analysis failed: {e}")
            content_analysis = ContentAnalysis(url=url, combined_score=0.0)
        stages_run.append("content")
        _stage_done("content", _content_summary(content_analysis))

    # ---- Stage 5: Score (always runs with whatever we have) ----
    _stage_start("score")
    report = generate_report(
        url,
        robots_result or RobotsResult(url=url),
        llms_result or LlmsResult(url=url),
        schema_analysis or SchemaAnalysis(url=url),
        content_analysis or ContentAnalysis(url=url),
    )
    stages_run.append("score")
    _stage_done("score", f"Grade {report.grade}, {report.overall_score}/100")

    complete = "schema" in stages_run and "content" in stages_run

    return {
        "report": report,
        "errors": errors,
        "complete": complete,
        "stages_run": stages_run,
        "robots_result": robots_result or RobotsResult(url=url),
        "llms_result": llms_result or LlmsResult(url=url),
        "schema_analysis": schema_analysis or SchemaAnalysis(url=url),
        "content_analysis": content_analysis or ContentAnalysis(url=url),
        "fetch_result": fetch_result,
    }


# ---------------------------------------------------------------------------
# Detail helpers — build human-readable one-liners for each stage
# ---------------------------------------------------------------------------

def _robots_summary(r: RobotsResult) -> str:
    if not r.exists:
        return "not found"
    allowed = sum(1 for b in r.bots if b.status == "allowed")
    blocked = sum(1 for b in r.bots if b.status == "blocked")
    return f"{allowed} allowed, {blocked} blocked"


def _llms_summary(ll: LlmsResult) -> str:
    if not ll.found:
        return "not found"
    if ll.valid:
        return "valid"
    return f"found ({len(ll.raw_text or '')} chars)"


def _schema_summary(sa: SchemaAnalysis) -> str:
    if not sa.detected_types:
        return "no types detected"
    count = len(sa.detected_types)
    types = ", ".join(sorted(sa.detected_types)[:3])
    suffix = ", …" if count > 3 else ""
    return f"{count} type(s): {types}{suffix}"


def _content_summary(ca: ContentAnalysis) -> str:
    parts = [f"Flesch {ca.flesch_raw:.0f}"]
    if ca.entities:
        ent_count = sum(len(v) for v in ca.entities.values())
        parts.append(f"{ent_count} entities")
    qa = ca.qa_analysis
    if qa and qa.get("question_count", 0) > 0:
        parts.append(f"{qa['question_count']} Q&A pairs")
    return ", ".join(parts)
