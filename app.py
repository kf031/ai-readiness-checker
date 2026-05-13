"""Streamlit dashboard for the AI Readiness Checker.

Run: streamlit run app.py
"""
import streamlit as st

from src.checker.cli_renderer import GRADE_COLORS, MODULE_ORDER, MODULE_DISPLAY_NAMES
from src.checker.orchestrator import run_pipeline

st.set_page_config(
    page_title="AI Readiness Checker",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Grade badge hex colors -- maps CLI Rich color names to UI-SPEC hex values
GRADE_HEX = {
    "A": "#2ecc71",
    "B": "#3498db",
    "C": "#f1c40f",
    "D": "#e67e22",
    "F": "#e74c3c",
}

# Priority badge hex colors -- for recommendation priority indicators
PRIORITY_HEX = {
    "HIGH": "#e74c3c",
    "MEDIUM": "#f1c40f",
    "LOW": "#6c757d",
}

# Bot status hex colors -- for robots.txt per-bot status badges
STATUS_HEX = {
    "allowed": "#2ecc71",
    "blocked": "#e74c3c",
    "not_mentioned": "#6c757d",
}


@st.cache_data(show_spinner="Checking robots.txt, llms.txt, schema, content, and generating your score...")
def analyze_url(url: str) -> dict:
    """Cached wrapper around run_pipeline(). Cache is keyed by URL string.

    On cache miss: runs the full pipeline and stores result.
    On cache hit: returns instantly with no spinner.
    """
    return run_pipeline(url, timeout=10.0)


def render_score_hero(result: dict) -> None:
    """Render the overall score metric and grade badge."""
    report = result["report"]
    grade = report.grade

    # Column layout: score on left, grade badge on right
    col_score, col_grade = st.columns([2, 1])

    with col_score:
        st.metric(
            label="Overall Score",
            value=f"{report.overall_score}/100",
            border=True,
        )

    with col_grade:
        color_hex = GRADE_HEX.get(grade, "#6c757d")
        st.markdown(f"""
        <div style="
            display: inline-block;
            background-color: {color_hex};
            color: white;
            font-size: 48px;
            font-weight: 700;
            line-height: 1.1;
            padding: 8px 24px;
            border-radius: 8px;
            text-align: center;
            min-width: 80px;
        ">{grade}</div>
        """, unsafe_allow_html=True)


def render_module_expanders(result: dict) -> None:
    """Render per-module expandable sections with score bars and detail content."""
    report = result["report"]
    st.subheader("Module Breakdown")

    for module_key in MODULE_ORDER:
        data = report.module_breakdown.get(module_key)
        if data is None:
            continue
        score = data["score"]
        display_name = MODULE_DISPLAY_NAMES[module_key]

        with st.expander(f"{display_name} (score: {score:.2f})", expanded=False):
            st.progress(score)
            _render_module_detail(module_key, result)


def _render_module_detail(module_key: str, result: dict) -> None:
    """Render module-specific detail content inside an expander."""
    if module_key == "robots":
        _render_robots_detail(result)
    elif module_key == "llms_txt":
        _render_llms_detail(result)
    elif module_key == "schema":
        _render_schema_detail(result)
    elif module_key == "content":
        _render_content_detail(result)


def _render_robots_detail(result: dict) -> None:
    """Render robots.txt bot status table inside the Robots expander."""
    robots = result.get("robots_result")
    if robots is None or not robots.bots:
        st.write("No bot data available.")
        return

    if not robots.exists:
        st.write("robots.txt not found.")
        return

    # Build a markdown table: Bot Name | Status | Rule
    lines = ["| Bot | Status | Rule |", "|-----|--------|------|"]
    for bot in robots.bots:
        status_color = STATUS_HEX.get(bot.status, "#6c757d")
        status_badge = (
            f'<span style="color:{status_color};font-weight:600;">'
            f'{bot.status.replace("_", " ").title()}</span>'
        )
        rule = bot.rule_line if bot.rule_line else "—"
        lines.append(f"| {bot.bot_name} | {status_badge} | {rule} |")

    st.markdown("\n".join(lines), unsafe_allow_html=True)


def _render_llms_detail(result: dict) -> None:
    """Render llms.txt details inside the llms.txt expander."""
    llms = result.get("llms_result")
    if llms is None:
        st.write("No data available.")
        return

    if llms.found:
        st.write("**Status:** Found")
        if llms.valid is not None:
            valid_text = "Valid" if llms.valid else "Invalid"
            valid_color = "#2ecc71" if llms.valid else "#e74c3c"
            st.markdown(
                f'**Format:** <span style="color:{valid_color};">{valid_text}</span>',
                unsafe_allow_html=True,
            )
        if llms.validation_errors:
            st.write("**Validation Errors:**")
            for err in llms.validation_errors:
                st.markdown(f"- {err}")
        if llms.content_preview:
            st.write("**Content Preview:**")
            st.code(llms.content_preview, language="markdown")
        if llms.raw_text:
            st.write(f"**Full Content** ({len(llms.raw_text)} chars):")
            st.code(llms.raw_text, language="markdown")
    else:
        st.write("**Status:** Not Found")
        if llms.fetch_error:
            st.write(f"**Error:** {llms.fetch_error}")


def _render_schema_detail(result: dict) -> None:
    """Render schema extraction details inside the Schema expander."""
    schema = result.get("schema_analysis")
    if schema is None:
        st.write("No data available.")
        return

    # Detected types
    if schema.detected_types:
        st.write("**Detected Schema Types:**")
        for stype in sorted(schema.detected_types):
            details = schema.type_details.get(stype, {})
            count = details.get("count", 0)
            formats = details.get("formats", [])
            fmt_str = ", ".join(formats) if formats else "—"
            st.markdown(f"- **{stype}** ({count} instance(s), formats: {fmt_str})")
    else:
        st.write("No schema types detected.")

    # Raw format breakdown
    if schema.raw:
        st.write("**Raw Format Breakdown:**")
        for fmt_name, items in schema.raw.items():
            st.write(f"- {fmt_name}: {len(items)} block(s)")


def _render_content_detail(result: dict) -> None:
    """Render content analysis details inside the Content expander."""
    content = result.get("content_analysis")
    if content is None:
        st.write("No data available.")
        return

    # Readability scores
    st.write("**Readability**")
    st.write(f"- Flesch Reading Ease: {content.flesch_raw:.1f}")
    st.write(f"- Gunning Fog Index: {content.fog_raw:.1f}")

    # Text ratio
    st.write(f"**Content-to-HTML Ratio:** {content.raw_text_ratio:.1%}")

    # Entity breakdown
    if content.entities:
        st.write("**Named Entities:**")
        for entity_type in ["ORG", "PRODUCT", "GPE", "PERSON"]:
            entities_list = content.entities.get(entity_type, [])
            if entities_list:
                preview = ", ".join(entities_list[:5])
                suffix = f" and {len(entities_list) - 5} more" if len(entities_list) > 5 else ""
                st.write(f"- {entity_type}: {preview}{suffix}")
            else:
                st.write(f"- {entity_type}: none")

    # Heading structure
    ha = content.heading_analysis
    if ha:
        st.write("**Heading Structure:**")
        st.write(f"- H1 count: {ha.get('h1_count', 0)}")
        st.write(f"- H1 unique: {'Yes' if ha.get('h1_unique', False) else 'No'}")
        st.write(f"- H2 count: {ha.get('h2_count', 0)}")
        st.write(f"- H3 count: {ha.get('h3_count', 0)}")
        violations = ha.get('hierarchy_violations', [])
        if violations:
            st.write(f"- Hierarchy violations: {len(violations)}")

    # Q&A density
    qa = content.qa_analysis
    if qa:
        st.write("**Q&A Density:**")
        st.write(f"- Questions: {qa.get('question_count', 0)}")
        st.write(f"- Answers: {qa.get('answer_count', 0)}")
        total = qa.get('total_sentences', 1)
        st.write(f"- Total sentences: {total}")


def render_recommendations(result: dict) -> None:
    """Render prioritized recommendations table."""
    report = result["report"]
    recs = report.recommendations
    if not recs:
        return  # Empty state: render nothing

    st.subheader("Recommendations")

    # Build markdown table with priority-colored badges
    lines = ["| Priority | Module | Recommendation |", "|----------|--------|----------------|"]
    for rec in recs:
        priority = rec["priority"]
        color = PRIORITY_HEX.get(priority, "#6c757d")
        badge = f'<span style="color:{color};font-weight:600;">{priority}</span>'
        lines.append(f"| {badge} | {rec['module']} | {rec['message']} |")

    st.markdown("\n".join(lines), unsafe_allow_html=True)


def render_errors(result: dict) -> None:
    """Render pipeline errors. Show verbatim error strings."""
    errors = result.get("errors", [])
    if not errors:
        return  # Empty state: render nothing

    st.error("Analysis failed for some stages. See details below.")
    for error in errors:
        st.markdown(f"- {error}")


# --- Main layout ---
st.title("AI Readiness Checker")

url = st.text_input(
    "Enter a URL to analyze",
    placeholder="https://example.com",
    key="url_input",
)

col_input, col_spacer = st.columns([1, 4])
with col_input:
    analyze_clicked = st.button("Analyze", type="primary")

if analyze_clicked and url:
    st.session_state.current_url = url
    st.session_state.analysis_done = True
elif analyze_clicked and not url:
    st.warning("Please enter a URL.")

# --- Results area (only if analysis has been run) ---
if st.session_state.get("analysis_done"):
    result = analyze_url(st.session_state.current_url)

    render_score_hero(result)
    st.markdown("<br>", unsafe_allow_html=True)  # lg spacing (24px)
    render_module_expanders(result)
    st.markdown("<br>", unsafe_allow_html=True)  # xl spacing (32px)
    render_recommendations(result)
    st.markdown("<br>", unsafe_allow_html=True)
    render_errors(result)
