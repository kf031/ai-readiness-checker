# Phase 07: Streamlit Dashboard - Pattern Map

**Mapped:** 2026-05-13
**Files analyzed:** 6 (4 new, 2 modified)
**Analogs found:** 6 / 6

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `app.py` | dashboard (Streamlit UI) | request-response | `src/checker/__main__.py` + `src/checker/cli_renderer.py` | role-different, data-flow-exact |
| `.streamlit/config.toml` | config | n/a | `pyproject.toml` | role-exact |
| `tests/test_dashboard.py` | test | n/a | `tests/test_cli_renderer.py` + `tests/test_orchestrator.py` | role-exact |
| `tests/conftest.py` | test (fixtures) | n/a | `tests/conftest.py` (existing fixtures) | exact (same file) |
| `src/checker/orchestrator.py` | service (orchestration) | pipeline (pipe-and-filter) | `src/checker/orchestrator.py` (existing return dict) | exact (same file) |
| `tests/test_orchestrator.py` | test | n/a | `tests/test_orchestrator.py` (existing test patterns) | exact (same file) |

---

## Pattern Assignments

### `app.py` (dashboard, request-response)

**Analogs:** `src/checker/__main__.py` (entry point pattern) + `src/checker/cli_renderer.py` (renderer consumption pattern)

**Imports pattern** (from `src/checker/__main__.py` lines 1-10 and `cli_renderer.py` lines 7-12):

```python
"""Streamlit dashboard for AI Readiness Checker.

Run: streamlit run app.py
"""
import streamlit as st

from src.checker.cli_renderer import GRADE_COLORS, MODULE_ORDER, MODULE_DISPLAY_NAMES
from src.checker.orchestrator import run_pipeline
```

Key observations:
- Module-level docstring explains what the file is and how to run it (matching `__main__.py` line 1-4 convention)
- Absolute imports from `src.checker.*` packages (matching D-01 requirement)
- Constants imported from `cli_renderer.py` rather than redefined (matching D-03 requirement for visual parity)

**Pipeline call pattern** (from `src/checker/__main__.py` lines 48-51):

```python
    # Run the full analysis pipeline
    result = run_pipeline(args.url, timeout=args.timeout, verbose=args.verbose)

    # Display the formatted score card
    display_score_card(result)
```

Translated to Streamlit:

```python
@st.cache_data(show_spinner="Checking robots.txt, llms.txt, schema, content, and generating your score...")
def analyze_url(url: str) -> dict:
    """Cached wrapper around run_pipeline()."""
    return run_pipeline(url, timeout=10.0)

# In the app flow:
if st.button("Analyze"):
    if url:
        result = analyze_url(url)
        st.session_state.analysis_done = True
        st.session_state.current_result = result
    else:
        st.warning("Please enter a URL.")
```

**Constants pattern** (from `src/checker/cli_renderer.py` lines 13-28):

```python
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
```

These are imported, not redefined. The dashboard maps the Rich color names to hex values per the UI-SPEC:

```python
GRADE_HEX = {
    "A": "#2ecc71",
    "B": "#3498db",
    "C": "#f1c40f",
    "D": "#e67e22",
    "F": "#e74c3c",
}
```

**Render function decomposition pattern** (from `src/checker/cli_renderer.py` lines 45-148):

The CLI renderer uses a single function `display_score_card()` that reads from a `pipeline_result` dict and calls Rich components. The dashboard follows the same data-access pattern but splits into render sub-functions:

```python
# Data access pattern (from cli_renderer.py lines 63-66):
report = pipeline_result["report"]
errors = pipeline_result["errors"]
complete = pipeline_result["complete"]
stages_run = pipeline_result["stages_run"]

# Streamlit equivalent -- sub-functions per render section:
def render_score_hero(result: dict):
    report = result["report"]
    # st.metric + st.markdown grade badge

def render_module_expanders(result: dict):
    report = result["report"]
    for module_key in MODULE_ORDER:
        # st.expander + st.progress + detail content

def render_recommendations(result: dict):
    report = result["report"]
    # st.dataframe or st.markdown table

def render_errors(result: dict):
    errors = result["errors"]
    # st.error + st.markdown per error
```

**Error display pattern** (from `src/checker/cli_renderer.py` lines 138-145):

```python
    # 7. Pipeline errors (if non-empty)
    if errors:
        console.print(
            Panel(
                "\n".join(errors),
                title="[red]Pipeline Errors[/red]",
                border_style="red",
            )
        )
```

Streamlit equivalent (matching D-04 -- verbatim error display):

```python
    if errors:
        st.error("Analysis failed for some stages. See details below.")
        for error in errors:
            st.markdown(f"- {error}")
```

**Empty state pattern** (no analog in project -- research-defined):

From RESEARCH.md Pattern 4: No placeholder content. Results area renders only when `st.session_state.analysis_done` is True. The URL input and Analyze button are always visible. Initial page load shows only the `st.title` + `st.text_input` + `st.button` row.

```python
st.title("AI Readiness Checker")
url = st.text_input("Enter a URL to analyze", placeholder="https://example.com")

if st.button("Analyze") and url:
    result = analyze_url(url)
    st.session_state.analysis_done = True
    st.session_state.current_result = result

if st.session_state.get("analysis_done"):
    render_results(st.session_state.current_result)
# Else: nothing rendered below the input row
```

---

### `.streamlit/config.toml` (config, n/a)

**Analog:** `pyproject.toml` (TOML structure pattern)

**TOML structure pattern** (from `pyproject.toml` lines 1-4, 26-35):

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[project]
name = "ai-readiness-checker"
version = "0.1.0"
...
```

Streamlit config equivalent:

```toml
[theme]
base = "dark"
primaryColor = "#3498db"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1a1d24"
textColor = "#e0e0e0"
font = "sans serif"
```

Values sourced from UI-SPEC.md lines 34-41 (Streamlit Theme Contract table). The TOML section header convention (`[section_name]`) and key-value formatting match `pyproject.toml`.

---

### `tests/test_dashboard.py` (test, n/a)

**Analogs:** `tests/test_cli_renderer.py` (display-layer test patterns) + `tests/test_orchestrator.py` (mock/patch patterns)

**Imports and test docstring** (from `tests/test_cli_renderer.py` lines 1-11):

```python
"""Tests for streamlit dashboard — covers URL input, pipeline trigger, rendering, caching.

Uses streamlit.testing.v1.AppTest for functional testing.
"""

from streamlit.testing.v1 import AppTest
```

**Helper/fixture pattern** (from `tests/test_cli_renderer.py` lines 13-20):

```python
def _make_pipeline_result(report, errors=None, complete=True, stages_run=None):
    """Helper to build the pipeline result dict consumed by display_score_card."""
    return {
        "report": report,
        "errors": errors if errors is not None else [],
        "complete": complete,
        "stages_run": stages_run or ["crawl", "access_signals", "schema", "content", "score"],
    }
```

Dashboard test equivalent -- the helper needs the 4 new raw module object keys:

```python
def _make_pipeline_result(report, errors=None, complete=True, stages_run=None,
                           robots_result=None, llms_result=None,
                           schema_analysis=None, content_analysis=None):
    """Helper to build the pipeline result dict for dashboard render functions."""
    from src.checker.contracts import (
        ContentAnalysis, LlmsResult, RobotsResult, SchemaAnalysis,
    )
    return {
        "report": report,
        "errors": errors if errors is not None else [],
        "complete": complete,
        "stages_run": stages_run or ["crawl", "access_signals", "schema", "content", "score"],
        "robots_result": robots_result or RobotsResult(url="https://example.com"),
        "llms_result": llms_result or LlmsResult(url="https://example.com"),
        "schema_analysis": schema_analysis or SchemaAnalysis(url="https://example.com"),
        "content_analysis": content_analysis or ContentAnalysis(url="https://example.com"),
    }
```

**Test structure pattern** (from `tests/test_cli_renderer.py` lines 23-42):

```python
def test_grade_A_colored_green():
    """ScoreReport with grade='A' renders without crash and output contains 'A'."""
    report = ScoreReport(
        url="https://example.com",
        overall_score=92.5,
        grade="A",
        module_breakdown={...},
    )
    pipeline_result = _make_pipeline_result(report)
    console = Console(force_terminal=True, width=120)
    with console.capture() as capture:
        display_score_card(pipeline_result, console=console)
    output = capture.get()
    assert "A" in output
    assert "92.5" in output
```

Streamlit AppTest equivalent:

```python
def test_grade_A_rendered():
    """Grade 'A' is rendered in the dashboard."""
    at = AppTest.from_file("app.py").run()
    # Set URL and click Analyze
    at.text_input[0].set_value("https://example.com").run()
    at.button[0].click().run()
    # Check output contains grade
    assert "A" in at.markdown  # grade badge rendered
    assert not at.exception
```

**Mock/patch pattern for pipeline** (from `tests/test_orchestrator.py` lines 21-50):

```python
def test_pipeline_full_success(sample_robots_result, sample_llms_result,
                               sample_schema_analysis, sample_content_analysis):
    """Verify run_pipeline() returns complete dict with all 5 stages on success."""
    with patch("src.checker.orchestrator.fetch_url") as mock_fetch, \
         patch("src.checker.orchestrator.fetch_access_signals") as mock_access, \
         patch("src.checker.orchestrator.analyze_schema") as mock_schema, \
         patch("src.checker.orchestrator.analyze_content") as mock_content, \
         patch("src.checker.orchestrator.generate_report") as mock_score:

        mock_fetch.return_value = FetchResult(...)
        mock_access.return_value = (sample_robots_result, sample_llms_result)
        mock_schema.return_value = sample_schema_analysis
        mock_content.return_value = sample_content_analysis
        mock_score.return_value = ScoreReport(...)

        result = run_pipeline("https://example.com")

        assert isinstance(result, dict)
        assert set(result.keys()) == {"report", "errors", "complete", "stages_run"}
```

For Dashboard tests, the same mock pattern is applied but at the `app.py` module level:

```python
def test_analyze_triggers_pipeline(mock_pipeline_result):
    """Clicking Analyze with a URL triggers run_pipeline and renders results."""
    with patch("app.run_pipeline") as mock_run:
        mock_run.return_value = mock_pipeline_result

        at = AppTest.from_file("app.py").run()
        at.text_input[0].set_value("https://example.com").run()
        at.button[0].click().run()

        mock_run.assert_called_once_with("https://example.com", timeout=10.0)
```

---

### `tests/conftest.py` (test fixtures, n/a) -- MODIFY

**Analog:** Existing `tests/conftest.py` (same file, extend existing fixture pattern)

**Existing fixture definition pattern** (from `tests/conftest.py` lines 446-516, orchestrator fixtures section):

```python
# -- Orchestrator fixtures (Phase 6) --

@pytest.fixture
def sample_fetch_result():
    """Return a valid FetchResult for orchestrator tests."""
    from src.checker.contracts import FetchResult

    html = "<html><body><p>Test</p></body></html>"
    return FetchResult(
        url="https://example.com",
        final_url="https://example.com",
        status_code=200,
        html=html,
        soup=BeautifulSoup(html, 'lxml'),
    )


@pytest.fixture
def sample_robots_result():
    """Return a valid RobotsResult for orchestrator tests."""
    from src.checker.contracts import RobotsResult

    return RobotsResult(
        url="https://example.com",
        exists=True,
        bots=[],
    )
```

**New fixtures to add** (following same pattern -- section comment, docstring, import, return):

```python
# -- Dashboard fixtures (Phase 7) --

@pytest.fixture
def sample_score_report():
    """Return a complete ScoreReport for dashboard tests."""
    from src.checker.contracts import ScoreReport

    return ScoreReport(
        url="https://example.com",
        overall_score=78.5,
        grade="B",
        module_breakdown={
            "robots": {"score": 0.85, "weight": 0.20, "weighted": 17.0},
            "llms_txt": {"score": 0.90, "weight": 0.15, "weighted": 13.5},
            "schema": {"score": 0.60, "weight": 0.30, "weighted": 18.0},
            "content": {"score": 0.72, "weight": 0.35, "weighted": 25.2},
        },
        recommendations=[
            {"priority": "HIGH", "module": "robots", "message": "GPTBot is blocked"},
            {"priority": "MEDIUM", "module": "schema", "message": "No FAQPage schema found"},
        ],
    )


@pytest.fixture
def mock_pipeline_result(sample_score_report,
                          sample_robots_result, sample_llms_result,
                          sample_schema_analysis, sample_content_analysis):
    """Return a full pipeline result dict matching the new orchestrator return."""
    return {
        "report": sample_score_report,
        "errors": [],
        "complete": True,
        "stages_run": ["crawl", "access_signals", "schema", "content", "score"],
        "robots_result": sample_robots_result,
        "llms_result": sample_llms_result,
        "schema_analysis": sample_schema_analysis,
        "content_analysis": sample_content_analysis,
    }
```

---

### `src/checker/orchestrator.py` (service, pipeline) -- MODIFY

**Analog:** Existing orchestrator.py (same file, extend return dict)

**Current return dict** (from `orchestrator.py` lines 107-112):

```python
    return {
        "report": report,
        "errors": errors,
        "complete": complete,
        "stages_run": stages_run,
    }
```

**Modified return dict** (adding 4 raw module object keys):

```python
    return {
        "report": report,
        "errors": errors,
        "complete": complete,
        "stages_run": stages_run,
        "robots_result": robots_result or RobotsResult(url=url),
        "llms_result": llms_result or LlmsResult(url=url),
        "schema_analysis": schema_analysis or SchemaAnalysis(url=url),
        "content_analysis": content_analysis or ContentAnalysis(url=url),
    }
```

Validation detail: The variables `robots_result`, `llms_result`, `schema_analysis`, `content_analysis` already exist in the orchestrator's local scope (lines 46-50). The `or RobotsResult(url=url)` fallback handles the case where a variable remains None (e.g., schema/content not run because crawl failed). The existing imports at lines 11-17 already include `RobotsResult`, `LlmsResult`, `SchemaAnalysis`, `ContentAnalysis`.

---

### `tests/test_orchestrator.py` (test, n/a) -- MODIFY

**Analog:** Existing test_orchestrator.py (same file, update assertion)

**Current assertion** (from `tests/test_orchestrator.py` line 46):

```python
        assert set(result.keys()) == {"report", "errors", "complete", "stages_run"}
```

**Updated assertion** (to include the 4 new keys):

```python
        assert set(result.keys()) == {
            "report", "errors", "complete", "stages_run",
            "robots_result", "llms_result", "schema_analysis", "content_analysis",
        }
```

This change applies to all tests that check the return dict keys. The same assertion pattern appears in:
- `test_pipeline_full_success` (line 46)
- Any other test that inspects return dict keys

**Additional assertions to add** (verify raw object types are correct):

```python
        from src.checker.contracts import (
            ContentAnalysis, LlmsResult, RobotsResult, SchemaAnalysis,
        )
        assert isinstance(result["robots_result"], RobotsResult)
        assert isinstance(result["llms_result"], LlmsResult)
        assert isinstance(result["schema_analysis"], SchemaAnalysis)
        assert isinstance(result["content_analysis"], ContentAnalysis)
```

---

## Shared Patterns

### Pipeline Result Dict Shape (cross-cutting contract)

**Source:** `src/checker/orchestrator.py` lines 36-42 (docstring) + post-modification return statement
**Apply to:** `app.py`, `tests/test_dashboard.py`, `tests/test_orchestrator.py`

All consumers access the pipeline result dict with these keys:

```python
result = run_pipeline(url)
# Always present:
result["report"]          # ScoreReport
result["errors"]          # list[str]
result["complete"]        # bool
result["stages_run"]      # list[str]
# After Phase 7 orchestrator patch:
result["robots_result"]   # RobotsResult
result["llms_result"]     # LlmsResult
result["schema_analysis"] # SchemaAnalysis
result["content_analysis"]  # ContentAnalysis
```

### Grade Color Constants (cross-cutting visual consistency)

**Source:** `src/checker/cli_renderer.py` lines 13-19
**Apply to:** `app.py` (import, do not redefine)

```python
from src.checker.cli_renderer import GRADE_COLORS, MODULE_ORDER, MODULE_DISPLAY_NAMES
```

The dashboard maps the Rich color names to hex values at usage sites (inline in `render_grade_badge()`). No new constants file needed.

### Recommendation Priority Ordering (cross-cutting display consistency)

**Source:** `src/checker/cli_renderer.py` lines 123-128
**Apply to:** `app.py` render_recommendations()

```python
priority_style = {
    "HIGH": "red",
    "MEDIUM": "yellow",
    "LOW": "dim",
}
```

Dashboard maps to hex from UI-SPEC:

```python
priority_hex = {
    "HIGH": "#e74c3c",
    "MEDIUM": "#f1c40f",
    "LOW": "#6c757d",
}
```

### Error Display -- Verbatim (D-04)

**Source:** `src/checker/cli_renderer.py` lines 138-145
**Apply to:** `app.py` render_errors()

Both CLI and dashboard show error strings verbatim. No parsing, no categorization. The only difference is the display component (Rich Panel vs Streamlit error/warning).

### Fixture Dependency Injection (test pattern)

**Source:** `tests/test_orchestrator.py` lines 21-23 (function signature with fixture args)
**Apply to:** `tests/test_dashboard.py`, `tests/conftest.py`

Fixtures are passed as function arguments by name. The `mock_pipeline_result` fixture composes `sample_score_report`, `sample_robots_result`, `sample_llms_result`, `sample_schema_analysis`, `sample_content_analysis` into a single dict matching the orchestrator's return shape.

---

## No Analog Found

None. All 6 files have strong analogs in the existing codebase.

---

## Metadata

**Analog search scope:** `src/checker/`, `tests/`, project root
**Files scanned:** 13 (all Python files in `src/checker/` and `tests/`)
**Pattern extraction date:** 2026-05-13
**Key references:**
- `src/checker/__main__.py` -- entry point and import patterns
- `src/checker/cli_renderer.py` -- renderer consumption, constants, display patterns
- `src/checker/orchestrator.py` -- pipeline result dict contract
- `src/checker/contracts.py` -- ScoreReport and module result dataclass shapes
- `src/checker/scorer.py` -- MODULE_WEIGHTS, GRADE_BOUNDARIES, recommendation generation
- `tests/conftest.py` -- fixture definition patterns
- `tests/test_cli_renderer.py` -- display-layer test structure
- `tests/test_orchestrator.py` -- mock/patch patterns and return dict assertions
- `pyproject.toml` -- TOML config file structure
- `.planning/phases/07-streamlit-dashboard/07-UI-SPEC.md` -- approved visual design contract
