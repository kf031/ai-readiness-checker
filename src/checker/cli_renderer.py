"""Rich-formatted terminal score card for the AI Readiness Checker.

Pure presentation layer — consumes a pipeline result dict containing
a ScoreReport and renders a premium score card using Rich components.
"""

from rich.align import Align
from rich.box import ROUNDED
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

GRADE_COLORS = {
    "A": "green",
    "B": "blue",
    "C": "yellow",
    "D": "orange3",
    "F": "red",
}

GRADE_BG = {
    "A": "on green",
    "B": "on blue",
    "C": "on yellow",
    "D": "on orange3",
    "F": "on red",
}

MODULE_ORDER = ["robots", "llms_txt", "schema", "content"]

MODULE_DISPLAY_NAMES = {
    "robots": "Robots.txt",
    "llms_txt": "llms.txt",
    "schema": "Schema",
    "content": "Content",
}

PRIORITY_ICONS = {
    "HIGH": ("▲", "red"),
    "MEDIUM": ("■", "yellow"),
    "LOW": ("▼", "dim"),
}

BAR_WIDTH = 20


def _render_score_bar(score: float, width: int = BAR_WIDTH) -> str:
    """Render a Unicode block character score bar."""
    filled = int(round(score * width))
    return "█" * filled + "░" * (width - filled)


def display_score_card(
    pipeline_result: dict,
    console: Console | None = None,
) -> None:
    """Render a premium Rich-formatted AI Readiness Score Card.

    Args:
        pipeline_result: Dict from run_pipeline() with keys:
            report, errors, complete, stages_run.
        console: Optional Rich Console. Created if None.
    """
    if console is None:
        console = Console()

    report = pipeline_result["report"]
    errors = pipeline_result["errors"]
    complete = pipeline_result["complete"]

    SP = Text("")  # spacer (empty line)

    # --- Build the card contents ---
    lines: list = []

    # Header
    lines.append(Align.center(Text("AI Readiness Score Card", style="bold")))
    lines.append(Align.center(Text(report.url, style="dim")))
    lines.append(SP)

    # Grade badge + overall score — built as inline text for single-line layout
    grade_color = GRADE_COLORS.get(report.grade, "white")
    grade_bg = GRADE_BG.get(report.grade, "on default")
    badge_text = Text(f" {report.grade} ", style=f"bold white {grade_bg}")
    score_text = Text(f"  {report.overall_score}/100", style=f"bold {grade_color}")
    lines.append(Align.center(Text.assemble(badge_text, score_text)))
    lines.append(SP)

    # Incomplete indicator
    if not complete:
        lines.append(
            Align.center(
                Text(
                    f"(Partial — {len(pipeline_result['stages_run'])} of 5 stages completed)",
                    style="dim",
                )
            )
        )
        lines.append(SP)

    # Module breakdown
    for module_key in MODULE_ORDER:
        data = report.module_breakdown.get(module_key)
        if data is None:
            continue
        score = data["score"]
        bar = _render_score_bar(score)
        name = MODULE_DISPLAY_NAMES[module_key]
        weight = data["weight"]
        line = Text.assemble(
            f"  {name:<13} ",
            (bar, "bold"),
            f"  ({score:.2f})",
            f"  w: {weight:.0%}",
        )
        lines.append(line)

    # Recommendations (if non-empty)
    if report.recommendations:
        lines.append(SP)
        for rec in report.recommendations:
            icon, style = PRIORITY_ICONS.get(rec["priority"], ("·", "dim"))
            line = Text.assemble(
                f"  {icon} ",
                (f"[{rec['priority']}]", style),
                "  ",
                rec["message"],
            )
            lines.append(line)

    # Pipeline errors
    if errors:
        lines.append(SP)
        for err in errors:
            lines.append(Text(f"  ✗ {err}", style="red"))

    lines.append(SP)

    # --- Render as outer card ---
    card = Panel(
        Group(*lines),
        box=ROUNDED,
        padding=(1, 0),
    )
    console.print()
    console.print(card)
    console.print()
