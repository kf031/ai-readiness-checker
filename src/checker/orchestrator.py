"""
Pipeline orchestrator — wires all five analysis phases into a single run_pipeline().

Composition layer: all module logic exists; this module just calls them
in order and handles the FetchResult | CrawlError union type at the
crawler boundary.
"""

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


def run_pipeline(url: str, timeout: float = 10.0, verbose: bool = False) -> dict:
    """Run the full AI readiness analysis pipeline.

    Calls all five stages in order: crawl, access_signals, schema,
    content, score. Handles CrawlError branching (skip schema/content
    when crawl fails) and individual module failure recovery (zero-score
    fallback objects instead of crashing).

    Args:
        url: The URL to analyze (e.g., "https://example.com").
        timeout: HTTP request timeout in seconds. Default 10.0.
        verbose: If True, print stage names as they execute.

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

    # ---- Stage 1: Crawl ----
    if verbose:
        print("[crawl] Fetching page...")
    fetch_result = fetch_url(url, timeout=timeout)
    stages_run.append("crawl")

    if isinstance(fetch_result, CrawlError):
        errors.append(f"Crawl failed: {fetch_result.message}")

    # ---- Stage 2: Access signals (always runs — fetches its own URLs) ----
    if verbose:
        print("[access_signals] Checking robots.txt and llms.txt...")
    try:
        robots_result, llms_result = fetch_access_signals(url, timeout=timeout)
    except Exception as e:
        errors.append(f"Access signals failed: {e}")
        robots_result = RobotsResult(url=url, exists=False, fetch_error=str(e))
        llms_result = LlmsResult(url=url, found=False, fetch_error=str(e))
    stages_run.append("access_signals")

    # ---- Stage 3: Schema analysis (only if crawl succeeded) ----
    if verbose:
        print("[schema] Analyzing structured data...")
    if fetch_result is not None and not isinstance(fetch_result, CrawlError):
        try:
            schema_analysis = analyze_schema(fetch_result)
        except Exception as e:
            errors.append(f"Schema analysis failed: {e}")
            schema_analysis = SchemaAnalysis(url=url, score=0.0)
        stages_run.append("schema")

    # ---- Stage 4: Content analysis (only if crawl succeeded) ----
    if verbose:
        print("[content] Analyzing content quality...")
    if fetch_result is not None and not isinstance(fetch_result, CrawlError):
        try:
            content_analysis = analyze_content(fetch_result)
        except Exception as e:
            errors.append(f"Content analysis failed: {e}")
            content_analysis = ContentAnalysis(url=url, combined_score=0.0)
        stages_run.append("content")

    # ---- Stage 5: Score (always runs with whatever we have) ----
    if verbose:
        print("[score] Generating report...")
    report = generate_report(
        url,
        robots_result or RobotsResult(url=url),
        llms_result or LlmsResult(url=url),
        schema_analysis or SchemaAnalysis(url=url),
        content_analysis or ContentAnalysis(url=url),
    )
    stages_run.append("score")

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
        "fetch_result": fetch_result,  # FetchResult or CrawlError — has .html for v2 agent
    }
