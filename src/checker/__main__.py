"""CLI entry point for AI Readiness Checker.

Run: python -m checker <url> [--timeout SECONDS] [--verbose] [--fix]
     python -m checker --batch urls.csv [--output results.csv]
     python -m checker <url> --output report.json
"""

import argparse
import csv
import json
import sys
from typing import Any

from rich.box import ROUNDED
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from .cli_renderer import display_score_card
from .contracts import CrawlError
from .orchestrator import run_pipeline

# --- Animated progress display ---

STAGE_ORDER = ["crawl", "access_signals", "schema", "content", "score"]

STAGE_LABELS = {
    "crawl": "Fetching page",
    "access_signals": "Checking robots.txt & llms.txt",
    "schema": "Analyzing structured data",
    "content": "Analyzing content quality",
    "score": "Generating score report",
}


def _build_progress_panel(stage_states: dict) -> Group:
    """Build a Rich renderable showing current pipeline progress."""
    lines: list[Text] = []
    for key in STAGE_ORDER:
        label = STAGE_LABELS.get(key, key)
        state = stage_states.get(key, "pending")
        detail = stage_states.get(f"{key}_detail", "")

        if state == "pending":
            prefix, style = "  ○ ", "dim"
            suffix = ""
        elif state == "running":
            prefix, style = "  ◉ ", "bold cyan"
            suffix = ""
        else:  # done
            prefix, style = "  ✓ ", "bold green"
            suffix = f" — {detail}" if detail else ""

        lines.append(Text(f"{prefix}{label}{suffix}", style=style))

    return Group(*lines)


def _run_pipeline_with_progress(url: str, timeout: float, verbose: bool) -> dict:
    """Run the pipeline with an animated progress display.

    In verbose mode, stage names are printed as text.
    In normal mode, a Rich Live display shows animated stage progress.
    """
    if verbose:
        return run_pipeline(url, timeout=timeout, verbose=True)

    stages: dict[str, str] = {}

    def on_stage(key: str, status: str, detail: str | None):
        stages[key] = status
        if detail:
            stages[f"{key}_detail"] = detail

    with Live(
        _build_progress_panel(stages),
        console=None,
        refresh_per_second=8,
        transient=True,
    ):
        return run_pipeline(url, timeout=timeout, verbose=False, on_stage=on_stage)


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, run the analysis pipeline, and display results.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).

    Returns:
        Exit code: 0 on success.
    """

    parser = argparse.ArgumentParser(
        prog="python -m checker",
        description=(
            "AI Readiness Checker — score any website's AI search engine visibility"
        ),
        epilog="Example: python -m checker https://example.com",
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=None,
        help="URL to analyze (e.g., https://example.com)",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=float,
        default=10.0,
        help="HTTP request timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed per-stage analysis progress",
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Generate AI-improved version of the page using fix skills",
    )
    parser.add_argument(
        "--mcp", action="store_true",
        help="Start MCP server for LLM tool integration (ignores url)",
    )
    parser.add_argument(
        "--llm-backend",
        choices=["ollama", "openai", "anthropic"],
        default=None,
        help="Use an LLM backend for AI-powered fix generation (requires --fix)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Write JSON report to file (e.g., --output report.json)",
    )
    parser.add_argument(
        "--batch", "-b",
        type=str,
        default=None,
        help="Batch-process URLs from a CSV file (one URL per row, first column)",
    )
    parser.add_argument(
        "--serve", "-s",
        action="store_true",
        help="Start FastAPI server (python -m checker --serve --port 8000)",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8000,
        help="Port for --serve or --mcp (default: 8000)",
    )
    args = parser.parse_args(argv)

    # --serve mode: launch FastAPI server
    if args.serve:
        from .api_server import serve
        serve(port=args.port)
        return 0

    # --mcp mode: launch MCP server (does not run pipeline)
    if args.mcp:
        from .mcp_server import main as mcp_main
        import asyncio
        asyncio.run(mcp_main())
        return 0

    # --batch mode: process multiple URLs from CSV
    if args.batch:
        return _run_batch(args.batch, args.timeout, args.verbose, args.fix,
                          args.llm_backend, args.output)

    # Single URL is required unless --batch or --mcp
    if not args.url:
        parser.error("url is required (or use --batch or --mcp)")

    # Run the full analysis pipeline (with animated progress in non-verbose mode)
    result = _run_pipeline_with_progress(args.url, timeout=args.timeout, verbose=args.verbose)

    # Display the formatted score card
    display_score_card(result)

    # --fix mode: invoke the v2 agent after scoring
    if args.fix:
        _run_fix(result, args.llm_backend)

    # --output: write JSON report to file
    if args.output:
        _write_json_output(result, args.output)

    return 0


def _run_fix(pipeline_result: dict, backend_name: str | None = None) -> None:
    """Run the v2 LLM agent and display improvement results.

    Args:
        pipeline_result: Dict from run_pipeline().
        backend_name: Optional LLM backend name (ollama, openai, anthropic).
    """
    from .agent import build_agent_report, run_llm_agent

    console = Console()

    fetch_result = pipeline_result.get("fetch_result")
    if fetch_result is None or isinstance(fetch_result, CrawlError):
        console.print()
        console.print(
            Panel("[bold red]Cannot generate improvements[/] — page fetch failed.",
                  box=ROUNDED)
        )
        return

    html = fetch_result.html if hasattr(fetch_result, 'html') else ""
    if not html:
        console.print()
        console.print(
            Panel("[bold red]Cannot generate improvements[/] — no HTML content available.",
                  box=ROUNDED)
        )
        return

    report = build_agent_report(pipeline_result)

    # Initialize LLM backend if requested
    backend = None
    if backend_name:
        try:
            from .llm_backends import get_backend
            backend = get_backend(backend_name)
            console.print(f"\n[bold]Using LLM backend:[/] {backend_name}")
        except Exception as e:
            console.print(f"\n[bold red]LLM backend '{backend_name}' unavailable:[/] {e}")
            console.print("[dim]Falling back to template-based skills.[/]")

    output = run_llm_agent(report, html, backend=backend)

    # Build fix summary panel
    fix_lines: list[Text] = []
    if output.skills_called:
        fix_lines.append(Text(f"\n{len(output.skills_called)} skill(s) applied:", style="bold"))
        for i, change in enumerate(output.changes):
            is_last = (i == len(output.changes) - 1)
            prefix = "  └─" if is_last else "  ├─"
            fix_lines.append(Text(f"{prefix} {change}"))
    else:
        fix_lines.append(Text("No improvements needed — all modules scored above threshold."))

    if output.explanation:
        fix_lines.append(Text(""))
        fix_lines.append(Text(output.explanation, style="dim"))

    console.print()
    console.print(Panel(Group(*fix_lines), title="AI Fix Summary", box=ROUNDED))

    # Meta-skill routing
    _print_skill_routing(report, set(output.skills_called), console)


def _print_skill_routing(report: dict, skills_used: set[str], console: Console | None = None) -> None:
    """Print meta-skill routing for issues not covered by built-in fix skills."""
    modules = report.get("modules", {})
    routes = []

    content = modules.get("content", {})
    readability = content.get("readability", {})
    text_ratio = content.get("text_ratio", {})

    if readability.get("score", 1.0) < 0.5 and "fix-readability" not in skills_used:
        routes.append(("Low readability", "taste skill (copy tone & clarity)"))
    if text_ratio.get("score", 1.0) < 0.3:
        routes.append(("Low text-to-HTML ratio", "uiux-promax, max-ui (clean layout)"))
    if content.get("entity_score", 1.0) < 0.3:
        routes.append(("Few named entities detected", "taste skill (add brand mentions)"))
    if content.get("headings", {}).get("score", 1.0) < 0.5 and "fix-headings" not in skills_used:
        routes.append(("Weak heading structure", "uiux-promax (hierarchy audit)"))

    if not routes:
        return

    if console is None:
        console = Console()

    route_lines = [Text("Complementary tools for remaining issues:", style="bold")]
    for issue, suggestion in routes:
        route_lines.append(Text(f"  {issue} → {suggestion}"))
    route_lines.append(Text(""))
    route_lines.append(Text("Tip: Claude Code users can invoke these as skills", style="dim"))

    console.print()
    console.print(Panel(Group(*route_lines), title="Beyond Built-in Fixes", box=ROUNDED))


def score_attr(modules: dict, module: str, attr: str) -> float | None:
    """Safely drill into the report dict structure."""
    m = modules.get(module, {})
    val = m.get(attr, m.get("score"))
    return float(val) if val is not None else None


def _run_batch(batch_file: str, timeout: float, verbose: bool, fix: bool,
               backend_name: str | None, output_file: str | None) -> int:
    """Run pipeline on multiple URLs from a CSV file.

    Args:
        batch_file: Path to CSV file (one URL per row, first column).
        timeout: HTTP timeout.
        verbose: Show progress.
        fix: Run agent fixes after scoring.
        backend_name: LLM backend for fixes.
        output_file: Write results to this CSV file.

    Returns:
        Exit code: 0 on success.
    """
    urls = []
    try:
        with open(batch_file, newline="") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and row[0].strip():
                    urls.append(row[0].strip())
    except FileNotFoundError:
        print(f"Error: file not found: {batch_file}", file=sys.stderr)
        return 1

    if not urls:
        print("No URLs found in batch file.", file=sys.stderr)
        return 1

    results = []
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] {url}", end="", flush=True)
        try:
            result = run_pipeline(url, timeout=timeout, verbose=verbose)
            report = result.get("report")
            results.append({
                "url": url,
                "overall_score": report.overall_score if report else "N/A",
                "grade": report.grade if report else "N/A",
                "complete": result.get("complete", False),
                "errors": len(result.get("errors", [])),
            })
            print(f"  → {report.grade if report else 'ERR'} ({report.overall_score if report else 'N/A'})")
        except Exception as e:
            results.append({
                "url": url,
                "overall_score": "ERR",
                "grade": "ERR",
                "complete": False,
                "errors": 1,
            })
            print(f"  → error: {e}")

    # Print summary table
    print(f"\n{'─' * 72}")
    print(f"{'URL':<50} {'Score':>8} {'Grade':>6}")
    print(f"{'─' * 72}")
    for r in results:
        print(f"{r['url']:<50} {r['overall_score']:>8} {r['grade']:>6}")

    if fix:
        print("\n[fix] --fix is not yet supported in batch mode. Run individually with --fix.")

    # Write output CSV if requested
    if output_file:
        with open(output_file, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["url", "overall_score", "grade", "complete", "errors"])
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults written to {output_file}")

    return 0


def _write_json_output(pipeline_result: dict, path: str) -> None:
    """Serialize the pipeline result to JSON and write to a file.

    Strips non-serializable objects (soup, fetch_result, raw module objects).
    Keeps the ScoreReport, errors, complete, stages_run.
    """
    report = pipeline_result.get("report")
    data = _serialize_report(report)
    data["errors"] = pipeline_result.get("errors", [])
    data["complete"] = pipeline_result.get("complete", False)
    data["stages_run"] = pipeline_result.get("stages_run", [])

    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"\nReport written to {path}")


def _serialize_report(report) -> dict[str, Any]:
    """Convert a ScoreReport to a JSON-safe dict."""
    return {
        "url": getattr(report, "url", ""),
        "overall_score": getattr(report, "overall_score", 0.0),
        "grade": getattr(report, "grade", "N/A"),
        "module_breakdown": _safe_dict(getattr(report, "module_breakdown", {})),
        "recommendations": _safe_list(getattr(report, "recommendations", [])),
        "timestamp": str(getattr(report, "timestamp", "")),
    }


def _safe_dict(d):
    """Recursively convert dataclass-in-dict to plain dict."""
    if hasattr(d, "items"):
        return {str(k): _safe_dict(v) for k, v in d.items()}
    if isinstance(d, list):
        return [_safe_dict(i) for i in d]
    return d


def _safe_list(lst):
    return [_safe_dict(i) for i in (lst or [])]


if __name__ == "__main__":
    sys.exit(main())
