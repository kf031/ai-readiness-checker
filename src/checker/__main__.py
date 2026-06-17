"""CLI entry point for AI Readiness Checker.

Run: python -m checker <url> [--timeout SECONDS] [--verbose] [--fix]
"""

import argparse
import sys

from .cli_renderer import display_score_card
from .contracts import CrawlError
from .orchestrator import run_pipeline


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
    args = parser.parse_args(argv)

    # --mcp mode: launch MCP server (does not run pipeline)
    if args.mcp:
        from .mcp_server import main as mcp_main
        import asyncio
        asyncio.run(mcp_main())
        return 0

    # Run the full analysis pipeline
    result = run_pipeline(args.url, timeout=args.timeout, verbose=args.verbose)

    # Display the formatted score card
    display_score_card(result)

    # --fix mode: invoke the v2 agent after scoring
    if args.fix:
        _run_fix(result)

    return 0


def _run_fix(pipeline_result: dict) -> None:
    """Run the v2 LLM agent and display improvement results."""
    from .agent import build_agent_report, run_llm_agent

    fetch_result = pipeline_result.get("fetch_result")
    if fetch_result is None or isinstance(fetch_result, CrawlError):
        print("\n[fix] Cannot generate improvements — page fetch failed.")
        return

    html = fetch_result.html if hasattr(fetch_result, 'html') else ""
    if not html:
        print("\n[fix] Cannot generate improvements — no HTML content available.")
        return

    report = build_agent_report(pipeline_result)
    output = run_llm_agent(report, html)

    print(f"\n{'─' * 60}")
    print("AI Improvement Summary")
    print(f"{'─' * 60}")
    if output.skills_called:
        print(f"Skills invoked: {', '.join(output.skills_called)}")
        print(f"Changes made: {len(output.changes)}")
        for change in output.changes:
            print(f"  • {change}")
    else:
        print("No improvements needed — all modules scored above threshold.")
    print(f"\n{output.explanation}")


if __name__ == "__main__":
    sys.exit(main())
