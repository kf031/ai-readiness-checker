"""Rich-formatted terminal score card for the AI Readiness Checker.

Pure presentation layer — consumes a pipeline result dict containing
a ScoreReport and renders a premium score card using Rich components.

Themes:
    default  — modern score card with colored grade badge
    dbz      — Dragon Ball Z scouter power-level display
"""


from rich.align import Align
from rich.box import HEAVY, ROUNDED
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
    "HIGH": ("▲", "red"),      # ▲
    "MEDIUM": ("■", "yellow"),  # ■
    "LOW": ("▼", "dim"),        # ▼
}

BAR_WIDTH = 20


def _render_score_bar(score: float, width: int = BAR_WIDTH) -> str:
    """Render a Unicode block character score bar."""
    filled = int(round(score * width))
    return "█" * filled + "░" * (width - filled)


# ═══════════════════════════════════════════════════════════════════════════════
# Theme: Default
# ═══════════════════════════════════════════════════════════════════════════════

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

    SP = Text("")

    lines: list = []

    # Header
    lines.append(Align.center(Text("AI Readiness Score Card", style="bold")))
    lines.append(Align.center(Text(report.url, style="dim")))
    lines.append(SP)

    # Grade badge + overall score
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

    # Recommendations
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

    card = Panel(Group(*lines), box=ROUNDED, padding=(1, 0))
    console.print()
    console.print(card)
    console.print()


# ═══════════════════════════════════════════════════════════════════════════════
# Theme: DBZ Scouter
# ═══════════════════════════════════════════════════════════════════════════════

# Power level thresholds (score 0-100 mapped to 0-9000 scale)
# "It's over 9000!" is the iconic DBZ meme
POWER_MAX = 9000

# DBZ warrior classes by power level
POWER_CLASSES = [
    (9000, "IT'S OVER 9000!!!", "bold bright_green"),
    (7000, "Legendary Warrior", "bold green"),
    (4000, "Super Elite", "green"),
    (1500, "Elite Warrior", "bright_green"),
    (500, "Low-Class Warrior", "green"),
    (0, "Civilian", "dim green"),
]

SCOUTER_BAR_WIDTH = 24


def _power_level(score: float) -> int:
    """Map a 0.0-1.0 score to a 0-9000 DBZ power level."""
    return min(int(round(score * POWER_MAX)), POWER_MAX)


def _warrior_class(power: int) -> tuple[str, str]:
    """Return (class_name, rich_style) for a given power level."""
    for threshold, name, style in POWER_CLASSES:
        if power >= threshold:
            return name, style
    return "Civilian", "dim green"


def _scouter_bar(score: float, width: int = SCOUTER_BAR_WIDTH) -> str:
    """Render a scouter-style power bar (green)."""
    filled = int(round(score * width))
    return "█" * filled + "▒" * (width - filled)


def display_scouter_card(
    pipeline_result: dict,
    console: Console | None = None,
) -> None:
    """Render a DBZ Scouter Power Level display.

    Green monochrome theme — feels like you're looking through a scouter visor.
    Scores become power levels, grades become warrior classes.
    """
    if console is None:
        console = Console()

    report = pipeline_result["report"]
    errors = pipeline_result["errors"]
    complete = pipeline_result["complete"]

    power = _power_level(report.overall_score / 100.0)
    class_name, class_style = _warrior_class(power)

    SP = Text("")

    lines: list = []

    # ── Scouter header ──
    # ASCII scouter lens motif
    lines.append(Align.center(Text(
        "┌──────────────┐\n"
        "│     ◉     │\n"
        "└──────────────┘",
        style="bold green",
    )))
    lines.append(Align.center(Text("S C O U T E R", style="bold green")))
    lines.append(Align.center(Text("P O W E R   L E V E L   R E A D I N G", style="green")))
    lines.append(SP)

    # ── Target ──
    lines.append(Align.center(Text(f"TARGET: {report.url}", style="dim green")))
    lines.append(SP)

    # ── Power level reading ──
    power_text = Text(f" {power} ", style="bold bright_green on black")

    power_box = Panel(
        Group(
            Align.center(power_text),
            Align.center(Text(f"CLASS: {class_name}", style=class_style)),
        ),
        box=ROUNDED,
        border_style="bright_green",
        padding=(0, 2),
    )
    lines.append(Align.center(power_box))
    lines.append(SP)

    # ── Module readings (scouter-style bars) ──
    for module_key in MODULE_ORDER:
        data = report.module_breakdown.get(module_key)
        if data is None:
            continue
        score = data["score"]
        bar = _scouter_bar(score)
        name = MODULE_DISPLAY_NAMES[module_key]
        pct = int(round(score * 100))
        line = Text.assemble(
            f"  {name:<13} ",
            (bar, "green"),
            f"  {pct}%",
        )
        lines.append(line)

    # ── Incomplete indicator ──
    if not complete:
        lines.append(SP)
        lines.append(
            Align.center(
                Text(
                    f"[INCOMPLETE SCAN — {len(pipeline_result['stages_run'])}/5 stages]",
                    style="dim yellow",
                )
            )
        )

    # ── Threat assessment (recommendations) ──
    if report.recommendations:
        lines.append(SP)
        lines.append(Text("  THREAT ASSESSMENT:", style="bold green"))
        for rec in report.recommendations:
            icon = _threat_icon(rec["priority"])
            line = Text.assemble(
                f"    {icon} ",
                (f"[{rec['priority']}]", "yellow"),
                "  ",
                Text(rec["message"], style="green"),
            )
            lines.append(line)

    # ── Scan errors ──
    if errors:
        lines.append(SP)
        for err in errors:
            lines.append(Text(f"  ✗ SCAN ERROR: {err}", style="red"))

    lines.append(SP)

    # ── Render in scouter frame ──
    card = Panel(
        Group(*lines),
        box=HEAVY,
        border_style="green",
        padding=(1, 1),
    )
    console.print()
    console.print(card)
    console.print()


def _threat_icon(priority: str) -> str:
    """DBZ-themed threat level icons."""
    return {"HIGH": "⚠", "MEDIUM": "◆", "LOW": "○"}.get(
        priority, "·"
    )  # ⚠, ◆, ○


# ═══════════════════════════════════════════════════════════════════════════════
# Scouter progress labels (used by __main__.py when --dbz is active)
# ═══════════════════════════════════════════════════════════════════════════════

SCOUTER_STAGE_LABELS = {
    "crawl": "Locking onto target",
    "access_signals": "Scanning defense systems",
    "schema": "Reading energy signature",
    "content": "Analyzing combat data",
    "score": "Computing battle power",
}
