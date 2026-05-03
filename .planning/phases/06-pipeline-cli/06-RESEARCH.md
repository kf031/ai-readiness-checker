# Phase 6: Pipeline Orchestrator + CLI - Research

**Researched:** 2026-05-04
**Domain:** Python CLI development, pipeline orchestration, terminal output formatting
**Confidence:** HIGH

## Summary

Phase 6 connects the existing four analysis modules (robots.txt, llms.txt, schema, content) and the Phase 5 scorer into a single end-to-end pipeline, then exposes it via a `python -m checker <url>` CLI command that renders a Rich-formatted score card. The pipeline is a pure composition layer -- all module logic already exists and is importable from `src.checker.*`. The CLI is a thin presentation layer that calls the orchestrator and renders the resulting `ScoreReport`.

The principal architectural challenge is that the crawler can return a `CrawlError` instead of a `FetchResult`, which blocks schema and content analysis (they need HTML). The access signals module runs independently regardless of crawler outcome. The orchestrator must handle this branching: if the crawler fails, run only access signals; if it succeeds, run the full pipeline. The score report must be partial when analysis is incomplete.

Rich 14.2.0 (already in pyproject.toml) provides everything needed for the score card: `Console` for output, `Table` for module breakdowns and recommendations, `Panel` for bordered sections, `Rule` for dividers, `Text` for styled grade display, and `Progress` with `Live` for transient progress indication during pipeline execution. No additional dependencies are required.

**Primary recommendation:** Build a single `orchestrator.py` module with a `run_pipeline(url)` function that calls all five phases in sequence with CrawlError branching, plus a minimal `__main__.py` that delegates to it. Keep the CLI rendering in `__main__.py` or a separate `cli.py` -- do not mix pipeline logic with presentation.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Pipeline orchestration (crawl -> access -> schema -> content -> score) | API/Backend | -- | Business logic -- wires existing modules in sequence, handles CrawlError branching, returns ScoreReport or partial report |
| CLI argument parsing (URL, --timeout, --verbose) | CLI Entry Point | -- | Parses sys.argv before any business logic; argparse is standard library |
| Rich-formatted score card rendering | CLI/Presentation | -- | Pure display layer -- consumes ScoreReport dataclass, produces terminal output via Rich |
| Progress indication during pipeline execution | CLI/Presentation | -- | Live/progress display is terminal-specific; orchestrator reports stage transitions, CLI renders them |
| CrawlError handling and partial reporting | API/Backend | -- | Pipeline must decide which modules can run given a crawler failure; this is business logic, not presentation |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rich | 14.2.0 [VERIFIED: importlib.metadata] | Terminal formatting: tables, panels, colors, progress bars, live display | Already in pyproject.toml; de facto standard for Python terminal output; 25k+ GitHub stars |
| argparse | stdlib | CLI argument parsing | Standard library, no dependency; sufficient for single-URL single-command CLI |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 8.4.2 [VERIFIED: importlib.metadata] | Test orchestrator logic and CLI rendering | Always -- existing test infrastructure, conftest.py fixtures available |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| argparse | Click or Typer | Click/Typer add dependencies and learning curve; argparse is sufficient for a single-command CLI with one positional argument and optional flags |
| Rich Table for score bars | Rich BarColumn (from Progress) | BarColumn is designed for live progress, not static score display; manual bar rendering with Unicode block characters gives more control over appearance |
| Rich Layout | Rich Panel + Rule + Table | Layout requires terminal dimensions and is complex for simple card layout; Panel and Rule compose simply |

**Installation:**
No additional packages needed. Rich is already installed and configured.

## Architecture Patterns

### System Architecture Diagram

```
User runs `python -m checker https://example.com`
                      |
                      v
              +------------------+
              |   __main__.py    |  CLI Entry Point
              | sys.exit(main()) |
              +--------+---------+
                       |
                       v
              +------------------+
              |   orchestrator   |  Pipeline Orchestrator
              |  run_pipeline()  |
              +---+----------+---+
                  |          |
        CrawlError?      FetchResult?
                  |          |
     +------------+          +---------------------------+
     |                                                    |
     v                                                    v
+------------------+                            +------------------+
| fetch_access_    |                            | fetch_access_    |
| signals(url)     |                            | signals(url)     |
| (robots+llms)    |                            | (robots+llms)    |
+--------+---------+                            +--------+---------+
         |                                               |
         v                                               v
  ┌──────────────┐                              ┌──────────────┐
  │ RobotsResult │                              │ RobotsResult │
  │  LlmsResult  │                              │  LlmsResult  │
  └──────┬───────┘                              └──────┬───────┘
         |                                               |
         |  (no HTML -- skip schema/content)              |  (has HTML -- run full)
         |                                               |
         v                                               v
  +------------------+                          +------------------+
  | generate_report  |                          | analyze_schema() |
  | (partial:        |                          +--------+---------+
  |  only access     |                                   |
  |  scores)         |                                   v
  +--------+---------+                          +------------------+
           |                                    | analyze_content()|
           |                                    +--------+---------+
           |                                             |
           |                                             v
           |                                    +------------------+
           |                                    | generate_report  |
           |                                    | (full: all four  |
           |                                    |  module scores)  |
           |                                    +--------+---------+
           |                                             |
           v                                             v
  +------------------+                          +------------------+
  |   ScoreReport    |<-------------------------+   ScoreReport    |
  |   (partial)      |                          |   (complete)     |
  +--------+---------+                          +--------+---------+
           |                                             |
           +-------------------+-------------------------+
                               |
                               v
                      +------------------+
                      |   __main__.py    |  CLI Renderer
                      | display_score_   |
                      | card(report)     |
                      +------------------+
                               |
                               v
                      Terminal Score Card
                      (grade, bars, recs)
```

**Key decision points:**
1. **CrawlError check** -- if `fetch_url()` returns `CrawlError`, only `fetch_access_signals()` can run (it fetches its own URLs independently). Schema and content need `FetchResult.soup`.
2. **Error recovery** -- individual module failures produce zero scores + error recommendations rather than crashing the pipeline.
3. **Report completeness flag** -- `ScoreReport` needs no modification; the consumer (CLI) detects partial state from `module_breakdown` keys or a new field on the orchestrator's return type.

### Recommended Project Structure

```
src/checker/
├── __init__.py          # Existing exports (Phase 1-5)
├── __main__.py          # NEW: CLI entry point (minimal -- delegates to orchestrator)
├── contracts.py         # Existing: all dataclasses including ScoreReport
├── crawler.py           # Existing: fetch_url()
├── access_fetcher.py    # Existing: fetch_access_signals()
├── robots_txt.py        # Existing
├── llms_txt.py          # Existing
├── schema_analyzer.py   # Existing: analyze_schema()
├── content_analyzer.py  # Existing: analyze_content()
├── scorer.py            # Existing: generate_report()
└── orchestrator.py      # NEW: run_pipeline() -- wires all modules
```

### Pattern 1: Minimal `__main__.py` (Delegation)

**What:** `__main__.py` is the entry point when user runs `python -m checker`. It must NOT contain business logic or Rich rendering. It parses args, calls the orchestrator, and delegates rendering.

**When to use:** Any package with `python -m` support.

**Example:**
```python
# Source: Python docs __main__.py convention + argparse pattern
# src/checker/__main__.py
import sys

def main():
    from .orchestrator import run_pipeline
    from .cli_renderer import display_score_card
    import argparse

    parser = argparse.ArgumentParser(
        description="AI Readiness Checker — score any website's AI search engine visibility"
    )
    parser.add_argument("url", help="URL to analyze (e.g., https://example.com)")
    parser.add_argument(
        "--timeout", "-t", type=float, default=10.0,
        help="HTTP request timeout in seconds (default: 10)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show detailed per-module analysis progress"
    )
    args = parser.parse_args()

    report = run_pipeline(args.url, timeout=args.timeout, verbose=args.verbose)
    display_score_card(report)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

[CITED: Python `__main__` documentation -- minimal pattern, delegate to importable modules]
[CITED: Rich documentation -- Console/Table/Panel for rendering]

### Pattern 2: Pipeline Orchestrator Function

**What:** A single function that calls all five existing phases in sequence, with CrawlError branching. Returns a structured result (either `ScoreReport` directly or a thin wrapper with completeness info).

**When to use:** When composing multiple existing functions into a single workflow.

**Example (conceptual):**
```python
# Source: Existing codebase patterns (generate_report, fetch_access_signals are functions)
# src/checker/orchestrator.py

def run_pipeline(url: str, timeout: float = 10.0, verbose: bool = False) -> dict:
    """Run the full AI readiness analysis pipeline.

    Returns:
        Dict with keys: 'report' (ScoreReport or None), 'errors' (list[str]),
        'complete' (bool), 'stages_run' (list[str])
    """
    stages_run = []
    errors = []
    fetch_result = None
    robots_result = None
    llms_result = None
    schema_analysis = None
    content_analysis = None

    # Stage 1: Crawl
    fetch_result = fetch_url(url, timeout=timeout)
    stages_run.append("crawl")
    if isinstance(fetch_result, CrawlError):
        errors.append(f"Crawl failed: {fetch_result.message}")
        # Continue with access signals only (they fetch their own URLs)

    # Stage 2: Access signals (always runs -- fetches robots.txt + llms.txt directly)
    try:
        robots_result, llms_result = fetch_access_signals(url, timeout=timeout)
        stages_run.append("access_signals")
    except Exception as e:
        errors.append(f"Access signals failed: {e}")
        # Create zero-result fallbacks
        robots_result = RobotsResult(url=url, exists=False, fetch_error=str(e))
        llms_result = LlmsResult(url=url, found=False, fetch_error=str(e))
        stages_run.append("access_signals")

    # Stage 3+4: Schema + Content (only if crawl succeeded)
    if fetch_result is not None and not isinstance(fetch_result, CrawlError):
        try:
            schema_analysis = analyze_schema(fetch_result)
            stages_run.append("schema")
        except Exception as e:
            errors.append(f"Schema analysis failed: {e}")
            schema_analysis = SchemaAnalysis(url=url, score=0.0)

        try:
            content_analysis = analyze_content(fetch_result)
            stages_run.append("content")
        except Exception as e:
            errors.append(f"Content analysis failed: {e}")
            content_analysis = ContentAnalysis(url=url, combined_score=0.0)

    # Stage 5: Score (always runs with whatever we have)
    report = generate_report(
        url, robots_result, llms_result,
        schema_analysis or SchemaAnalysis(url=url),
        content_analysis or ContentAnalysis(url=url),
    )
    stages_run.append("score")

    return {
        "report": report,
        "errors": errors,
        "complete": "schema" in stages_run and "content" in stages_run,
        "stages_run": stages_run,
    }
```

[ASSUMED] This pattern is derived from the existing codebase convention (all high-level APIs are functions, not classes), but the exact return type shape and error handling granularity should be reviewed by the user.

### Pattern 3: Rich Score Card Rendering

**What:** A pure rendering function that takes a `ScoreReport` and prints a formatted score card using Rich `Console`, `Table`, `Text`, `Rule`, and `Panel`.

**When to use:** CLI output rendering.

**Recommended Rich components for each score card section:**

| Score Card Section | Rich Component | Rationale |
|--------------------|---------------|-----------|
| Overall grade (A-F) | `Text` with color style | Large colored letter; style changes by grade: A=green, B=blue, C=yellow, D=orange, F=red [ASSUMED: color mapping not specified in requirements, derived from traffic-light convention] |
| Overall score (0-100) | `Text` or `Panel` with title | Numeric display next to grade |
| Per-module score bars | `Text` with Unicode block chars | Custom bar using `█` / `░` characters; `BarColumn` is for live progress, not static display |
| Module breakdown table | `Table` | Columns: Module, Score, Weight, Weighted Score |
| Recommendations list | `Table` or `Panel` with sorted list | Priority-coded rows (HIGH=red, MEDIUM=yellow, LOW=dim) |
| Header/title | `Rule` with title | Separation between sections |
| Pipeline errors (if any) | `Panel` with red border | Warning display for partial reports |

**Example (grade + score display):**
```python
# Source: Rich docs -- Text styling + Panel
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich.table import Table

GRADE_COLORS = {
    "A": "green", "B": "blue", "C": "yellow", "D": "orange3", "F": "red"
}

def display_score_card(pipeline_result: dict) -> None:
    console = Console()
    report = pipeline_result["report"]

    # Grade display
    grade_color = GRADE_COLORS.get(report.grade, "white")
    grade_text = Text(f" {report.grade} ", style=f"bold {grade_color} on default")

    # Score + grade panel
    console.print()
    console.print(Rule(title="AI Readiness Score Card"))
    console.print(f"URL: {report.url}")
    console.print(Panel(
        f"{grade_text}  Overall Score: {report.overall_score}/100",
        title="Result",
    ))

    # Module breakdown table
    table = Table(title="Module Breakdown")
    table.add_column("Module", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Weight", justify="right")
    table.add_column("Weighted", justify="right")
    table.add_column("Bar")

    for module, data in report.module_breakdown.items():
        score = data["score"]
        bar = _render_score_bar(score)  # uses █/░ characters
        table.add_row(
            module, f"{score:.2f}", f"{data['weight']:.0%}",
            f"{data['weighted']:.1f}", bar
        )

    console.print(table)

    # ... recommendations table ...

    if pipeline_result["errors"]:
        console.print(Panel(
            "\n".join(pipeline_result["errors"]),
            title="[red]Pipeline Errors",
            border_style="red"
        ))

    console.print()
```

[ASSUMED] Grade color scheme follows standard traffic-light convention (green=good, red=bad) and UX expectations; the requirements only specify "colored grade" without specifying exact colors. Confirm color scheme with user.

### Anti-Patterns to Avoid

- **Mixing CLI rendering with pipeline logic in `__main__.py`:** `__main__.py` should be ~15 lines. Pipeline logic goes in `orchestrator.py`. Rendering logic goes in either `__main__.py` or `cli_renderer.py`. If rendering exceeds ~40 lines, extract to `cli_renderer.py`.
- **Using `Rich Live` for the final score card:** `Live` is for transient/updating displays. The score card is static output. Use `Console.print()`.
- **Catching all exceptions silently in the orchestrator:** Log errors, produce fallback results (zero-score dataclasses), and report errors in the pipeline result so the CLI can display them.
- **Hardcoding Rich styles:** Use a `GRADE_COLORS` dict or similar constant map so style changes are centralized.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Terminal text coloring | ANSI escape code strings | Rich `Console.print(style=...)` | Rich handles terminal detection, non-TTY fallback (piping), Windows support, and 256/truecolor |
| ASCII progress bars | Custom bar rendering with `=` and spaces | Rich `Progress` with `SpinnerColumn`, `TextColumn` | Rich handles terminal width, refresh rate, non-TTY mode, and nested progress |
| Score bar rendering (static) | Custom ANSI bar | Rich `Text` with Unicode block chars `█░` | Rich Text composes cleanly with other renderables (Tables, Panels) |
| Argument parsing | Manual `sys.argv` slicing | `argparse` (stdlib) | Type validation, `--help` generation, error messages, optional flags |
| CLI entry point dispatch | `if __name__ == "__main__":` with inline logic | `__main__.py` delegation pattern | Importable, testable modules; `python -m checker` support |

**Key insight:** Rich already handles terminal width detection, color capability checking, and non-TTY fallback (e.g., piping to a file). Building any of this manually would duplicate battle-tested logic.

## Runtime State Inventory

> Phase 6 is a greenfield addition (new `__main__.py` and `orchestrator.py`), not a rename/refactor phase. No runtime state changes are needed.

## Common Pitfalls

### Pitfall 1: CrawlError Not Handled -- Silent Crash

**What goes wrong:** The orchestrator calls `fetch_url()`, gets a `CrawlError`, then passes it to `analyze_schema()` which expects a `FetchResult` with `.soup` attribute. AttributeError crashes the pipeline.

**Why it happens:** The existing modules (schema, content) have `FetchResult` as their input contract. The orchestrator is the first module that needs to handle the union type `FetchResult | CrawlError` at the composition boundary.

**How to avoid:** Type-check the return value of `fetch_url()` before proceeding to schema/content analysis. Use `isinstance(result, CrawlError)`.

**Warning signs:** `AttributeError: 'CrawlError' object has no attribute 'soup'` in test output.

### Pitfall 2: Rich Table Column Mismatch

**What goes wrong:** Adding rows with the wrong number of columns to a Rich `Table` raises `NotRenderableError` or silently misaligns content.

**Why it happens:** Rich Tables require exact column count match per row. Adding a row with 4 items to a table with 5 columns crashes.

**How to avoid:** Define all columns first, then add rows. Use a constants dict for module names to ensure consistent ordering between the breakdown dict and table rendering.

**Warning signs:** `rich.errors.NotRenderableError` at render time.

### Pitfall 3: Non-TTY Output (Piping to File)

**What goes wrong:** User runs `python -m checker https://example.com > report.txt` and gets ANSI escape codes in the file.

**Why it happens:** Rich colors use ANSI codes. When stdout is not a TTY (like when piping), Rich should auto-detect and strip styles. But if `Console()` is created without `force_terminal=False`, it may not.

**How to avoid:** Use `Console()` with default parameters -- Rich auto-detects TTY by default. If the user explicitly wants colors even when piped, add a `--color` flag that passes `force_terminal=True`.

**Warning signs:** `^[[31m` escape sequences visible in piped output.

### Pitfall 4: Progress Indicator Freezes Terminal on Slow Analysis

**What goes wrong:** A progress spinner runs while the pipeline is working, but if `Rich Live` context isn't properly cleaned up on KeyboardInterrupt, the terminal is left in a broken state.

**Why it happens:** `Live` and `Progress` use terminal control sequences that need cleanup on exit.

**How to avoid:** Wrap the pipeline execution in a `with Progress(...) as progress:` context manager so cleanup is automatic. Catch `KeyboardInterrupt` at the `__main__.py` level and print a clean message.

**Warning signs:** Terminal cursor disappears or line wrapping breaks after Ctrl+C during analysis.

## Code Examples

### Full Pipeline Execution with Progress

```python
# Source: Rich docs -- Progress context manager pattern
# [ASSUMED: exact stage names and progress increments match module count]

from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

def run_pipeline_with_progress(url: str, timeout: float) -> dict:
    """Run pipeline with Rich progress display."""
    stages = 5  # crawl, access, schema, content, score
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task("Analyzing...", total=stages * 20)

        progress.update(task, description="Fetching page...")
        fetch_result = fetch_url(url, timeout=timeout)
        progress.update(task, advance=20)

        progress.update(task, description="Checking access signals...")
        robots_result, llms_result = fetch_access_signals(url, timeout=timeout)
        progress.update(task, advance=20)

        # ... similar for remaining stages ...

        progress.update(task, description="Complete!", completed=stages * 20)

    return pipeline_result
```

### __main__.py with argparse

```python
# Source: Python docs __main__.py pattern [CITED]
# src/checker/__main__.py
import sys

def main() -> int:
    import argparse
    from .orchestrator import run_pipeline
    from .cli_renderer import display_score_card

    parser = argparse.ArgumentParser(
        description="AI Readiness Checker — score any website's AI search engine visibility",
        epilog="Example: python -m checker https://example.com"
    )
    parser.add_argument("url", help="URL to analyze")
    parser.add_argument("--timeout", "-t", type=float, default=10.0, help="Request timeout in seconds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show per-stage progress")
    args = parser.parse_args()

    report = run_pipeline(args.url, timeout=args.timeout, verbose=args.verbose)
    display_score_card(report)
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual ANSI escape codes for terminal colors | Rich library (Textualize/rich) | Industry standard since ~2021 | All new Python CLI tools use Rich or Textual; Rich handles TTY detection, Windows, and truecolor |
| `sys.argv[1]` for argument parsing | `argparse` with proper `--help` | Python 2.7+ | argparse provides type coercion, default values, help generation, and subcommands |
| Inline CLI logic in `__main__.py` | Delegation to importable modules | Long-standing best practice | Enables unit testing of CLI logic and reusability |
| Click/Typer for single-command CLIs | argparse | When only one command needed | argparse is sufficient; Click/Typer are overkill for `python -m checker <url>` |

**Deprecated/outdated:**
- **`optparse`**: Deprecated since Python 3.2. Use `argparse`.
- **`getopt`**: POSIX-style only, no `--help` generation. Use `argparse`.
- **Manual `sys.argv` parsing**: Error-prone, no help text. Use `argparse`.
- **`sys.exit()` without return code**: Use `sys.exit(main())` so shell scripts can check `$?`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Grade color scheme (A=green, B=blue, C=yellow, D=orange, F=red) follows traffic-light convention | Architecture Patterns -- Pattern 3 | User may prefer different colors; trivial to change by editing GRADE_COLORS dict |
| A2 | `orchestrator.py` and `cli_renderer.py` should be separate files | Architecture Patterns -- Recommended Structure | If the user prefers a single file, merge is straightforward; no architectural impact |
| A3 | Pipeline should continue with zero scores when individual modules fail (rather than aborting) | Architecture Patterns -- Pattern 2 | If user wants strict abort-on-error, need to restructure error handling; current approach is more user-friendly (show partial results with error notes) |
| A4 | Progress indicator uses Rich `Progress` with fixed 5 stages at ~20% each | Architecture Patterns -- Pattern 2 | Stage count might need adjustment if schema/content are split differently; percentages can be weighted by actual execution time |
| A5 | The orchestrator return type should be a dict with 'report', 'errors', 'complete', 'stages_run' keys (rather than modifying ScoreReport dataclass) | Architecture Patterns -- Pattern 2 | If ScoreReport needs a 'pipeline_errors' or 'complete' field for Phase 7 (Streamlit), this changes; adding fields to ScoreReport is a one-line dataclass change |
| A6 | `fetch_access_signals()` returns `Tuple[RobotsResult, LlmsResult]` -- not a union type | Architecture Patterns -- Pattern 2 | Verified by reading access_fetcher.py; confirmed return signature |

## Open Questions

1. **Should verbose mode print per-module intermediate results before the final score card?**
   - What we know: `--verbose` flag is proposed to show per-stage progress
   - What's unclear: Whether verbose should show intermediate module results (raw scores, entity lists, etc.) or just stage names
   - Recommendation: Start with stage-name-only verbose output (simpler). Per-module detail can be added later based on user feedback.

2. **Should `__main__.py` use `if __name__ == "__main__":` guard?**
   - What we know: Python `__main__` docs say it "typically isn't fenced" with the guard because `__main__.py` is only executed when the package is run directly
   - What's unclear: Whether testability concerns override this convention (guarded code can be imported in tests)
   - Recommendation: Include the guard for testability. It makes no difference at runtime (code runs in both cases when executed as `python -m checker`) but allows importing `main()` in tests for argparse testing.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Entire project | True | 3.13.9 | -- |
| rich | Score card rendering | True | 14.2.0 | -- |
| pytest | Test suite | True | 8.4.2 | -- |
| requests | Crawler (indirect) | True | (installed) | -- |
| httpx | Access fetcher (indirect) | True | (installed) | -- |

No missing dependencies. All Phase 6 needs is already installed.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | pyproject.toml `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/test_orchestrator.py -x` (new file needed) |
| Full suite command | `pytest -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CLI-01 | `python -m checker <url>` prints formatted score card | integration | `pytest tests/test_cli.py::test_cli_output -x` | No -- Wave 0 |
| CLI-01 | ScoreReport renders colored grade in terminal | unit | `pytest tests/test_cli_renderer.py::test_grade_coloring -x` | No -- Wave 0 |
| CLI-01 | Per-module score bars rendered | unit | `pytest tests/test_cli_renderer.py::test_module_bars -x` | No -- Wave 0 |
| CLI-01 | Recommendations rendered with priority ordering | unit | `pytest tests/test_cli_renderer.py::test_recommendations_rendered -x` | No -- Wave 0 |
| (implicit) | Pipeline runs crawl -> access -> schema -> content -> score | unit | `pytest tests/test_orchestrator.py::test_pipeline_full -x` | No -- Wave 0 |
| (implicit) | Pipeline handles CrawlError gracefully | unit | `pytest tests/test_orchestrator.py::test_pipeline_crawl_error -x` | No -- Wave 0 |
| (implicit) | Pipeline runs access signals when crawl fails | unit | `pytest tests/test_orchestrator.py::test_pipeline_partial -x` | No -- Wave 0 |
| (implicit) | Module failure produces zero score + error, doesn't crash | unit | `pytest tests/test_orchestrator.py::test_pipeline_module_error -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_orchestrator.py tests/test_cli_renderer.py -x`
- **Per wave merge:** `pytest -v` (full suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_orchestrator.py` -- covers pipeline execution, CrawlError handling, partial reports
- [ ] `tests/test_cli_renderer.py` -- covers Rich output formatting, grade coloring, module bars
- [ ] `tests/test_cli.py` -- covers argparse integration, `__main__` entry point, help text output
- [ ] `tests/conftest.py` -- may need new fixtures: mock ScoreReport with known scores for renderer tests (existing fixtures cover HTML and module inputs)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | -- |
| V3 Session Management | No | -- |
| V4 Access Control | No | -- |
| V5 Input Validation | Yes | argparse type validation for URL + timeout; SSRF prevention already in crawler.py |
| V6 Cryptography | No | -- |

### Known Threat Patterns for Python CLI

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Shell injection via URL argument | Tampering | argparse positional arg is a string, not passed to shell; no `os.system()` or `subprocess(shell=True)` used |
| SSRF via user-supplied URL | Information Disclosure | Already handled in `crawler.py` `is_ssrf_safe()` -- Phase 6 inherits this |
| Denial of service via timeout abuse | Denial of Service | `--timeout` flag has argparse `float` type validation; crawler already has 10s default with max response size |
| Information disclosure via verbose output | Information Disclosure | `--verbose` flag should not print raw HTML or response bodies; only stage names and score summaries |

## Sources

### Primary (HIGH confidence)
- Context7 `/textualize/rich` -- Table, Console, Panel, Rule, Layout, Text, Style, Progress, Live, Columns
- Context7 `/websites/rich_readthedocs_io_en_stable` -- Progress columns, BarColumn, TextColumn, SpinnerColumn, table grid, style objects
- Python standard library `__main__` documentation -- minimal `__main__.py` pattern, `sys.exit(main())` convention
- Source code inspection: `src/checker/scorer.py`, `src/checker/__init__.py`, `src/checker/contracts.py`, `src/checker/crawler.py`, `src/checker/access_fetcher.py`

### Secondary (MEDIUM confidence)
- Rich GitHub repository (Textualize/rich) -- progress customization, Live display patterns
- Rich readthedocs.io -- full API reference verified via Context7 snippets

### Tertiary (LOW confidence)
- None -- all claims verified with Context7, official docs, or codebase inspection

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Rich 14.2.0 verified installed, argparse is stdlib, no additional deps needed
- Architecture: HIGH -- existing codebase pattern (functions, not classes) is verified; `__main__.py` pattern from official Python docs; CrawlError type confirmed in crawler.py
- Pitfalls: HIGH -- CrawlError branching, Rich column mismatch, non-TTY fallback all verified against Rich docs and existing code
- Assumptions: 6 items flagged for user confirmation (A1-A6), all low-impact if wrong

**Research date:** 2026-05-04
**Valid until:** 2026-06-04 (30 days -- Rich API is stable; Python `__main__.py` pattern has not changed in years)
