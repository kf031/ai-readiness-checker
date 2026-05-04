"""CLI entry point for AI Readiness Checker.

Run: python -m checker <url> [--timeout SECONDS] [--verbose]
"""

import sys


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments, run the analysis pipeline, and display results.

    Args:
        argv: Argument list (defaults to sys.argv[1:] when None).

    Returns:
        Exit code: 0 on success.
    """
    import argparse
    from .orchestrator import run_pipeline
    from .cli_renderer import display_score_card

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
    args = parser.parse_args(argv)

    # Run the full analysis pipeline
    result = run_pipeline(args.url, timeout=args.timeout, verbose=args.verbose)

    # Display the formatted score card
    display_score_card(result)

    return 0


if __name__ == "__main__":
    sys.exit(main())
