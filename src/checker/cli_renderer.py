"""Rich-formatted terminal score card renderer for the AI Readiness Checker.

Pure presentation layer — consumes a pipeline result dict containing
a ScoreReport and renders a formatted score card using Rich components.
"""

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

GRADE_COLORS = {
    "A": "green",
    "B": "blue",
    "C": "yellow",
    "D": "orange3",
    "F": "red",
}

MODULE_ORDER = ["robots", "llms_txt", "schema", "content"]

MODULE_DISPLAY_NAMES = {
    "robots": "Robots.txt",
    "llms_txt": "llms.txt",
    "schema": "Schema",
    "content": "Content",
}


def _render_score_bar(score: float, width: int = 20) -> str:
    """Render a Unicode block character score bar.

    Args:
        score: Float in [0.0, 1.0].
        width: Total character width of the bar.

    Returns:
        String of ``width`` characters using ``█`` (filled) and ``░`` (empty).
    """
    filled = int(round(score * width))
    return "█" * filled + "░" * (width - filled)


def display_score_card(
    pipeline_result: dict,
    console: Console | None = None,
) -> None:
    """Render a Rich-formatted AI Readiness Score Card to the terminal.

    Args:
        pipeline_result: Dict with keys:
            - ``report``: ScoreReport (never None)
            - ``errors``: list[str] (error messages, may be empty)
            - ``complete``: bool (True if all 5 stages ran)
            - ``stages_run``: list[str] (stage names in execution order)
        console: Optional Rich Console instance. If None, a default Console
            is created. Useful for test capture.
    """
    if console is None:
        console = Console()

    report = pipeline_result["report"]
    errors = pipeline_result["errors"]
    complete = pipeline_result["complete"]
    stages_run = pipeline_result["stages_run"]

    # 1. Blank line + header
    console.print()
    console.print(Rule(title="AI Readiness Score Card"))

    # 2. URL
    console.print(f"URL: {report.url}")

    # 3. Completeness indicator
    if not complete:
        console.print(
            f"  [dim](Partial report — {len(stages_run)} of 5 stages completed)[/dim]"
        )

    # 4. Grade display
    grade_color = GRADE_COLORS.get(report.grade, "white")
    grade_text = Text(f" {report.grade} ", style=f"bold {grade_color} on default")
    console.print(
        Panel(
            f"{grade_text}  Overall Score: {report.overall_score}/100",
            title="Result",
        )
    )

    # 5. Module breakdown table
    table = Table(title="Module Breakdown")
    table.add_column("Module", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Weight", justify="right")
    table.add_column("Weighted", justify="right")
    table.add_column("Bar", justify="left")

    for module_key in MODULE_ORDER:
        data = report.module_breakdown.get(module_key)
        if data is None:
            continue
        score = data["score"]
        bar = _render_score_bar(score)
        display_name = MODULE_DISPLAY_NAMES[module_key]
        table.add_row(
            display_name,
            f"{score:.2f}",
            f"{data['weight']:.0%}",
            f"{data['weighted']:.1f}",
            bar,
        )

    console.print(table)

    # 6. Recommendations (if non-empty)
    if report.recommendations:
        rec_table = Table(title="Recommendations")
        rec_table.add_column("Priority", style="bold")
        rec_table.add_column("Module", style="cyan")
        rec_table.add_column("Message")

        for rec in report.recommendations:
            priority_style = {
                "HIGH": "red",
                "MEDIUM": "yellow",
                "LOW": "dim",
            }.get(rec["priority"], "")
            rec_table.add_row(
                f"[{priority_style}]{rec['priority']}[/{priority_style}]",
                rec["module"],
                rec["message"],
            )

        console.print(rec_table)

    # 7. Pipeline errors (if non-empty)
    if errors:
        console.print(
            Panel(
                "\n".join(errors),
                title="[red]Pipeline Errors[/red]",
                border_style="red",
            )
        )

    # 8. Trailing blank line
    console.print()
