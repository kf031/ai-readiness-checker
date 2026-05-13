# Phase 7: Streamlit Dashboard - Research

**Researched:** 2026-05-13
**Domain:** Streamlit data dashboard — single-tier Python web app
**Confidence:** HIGH

## Summary

Phase 7 builds an interactive Streamlit web UI for the AI Readiness Checker. It is a **data dashboard** — display and exploration only, no data entry beyond the URL input. The dashboard calls `run_pipeline()` (same function the CLI uses), caches results via `st.cache_data`, and renders scores, grade badges, per-module expanders with detail content, and recommendations.

The architecture is a single Streamlit server process with no separate API backend. All imports come from the existing `src.checker.*` package. The dashboard reuses the CLI's grade colors, module order, and display names from `cli_renderer.py` for visual consistency.

**Critical gap discovered:** The orchestrator's `run_pipeline()` return dict does not currently include raw module objects (`RobotsResult`, `LlmsResult`, `SchemaAnalysis`, `ContentAnalysis`). D-03 requires these for expander detail content. The orchestrator must be modified to add these 4 keys to its return dict before the dashboard can render module detail expanders. This is a small, low-risk patch to `orchestrator.py`.

**Primary recommendation:** Build a single `app.py` in project root. Use `@st.cache_data` (with URL as the hash key and `show_spinner` for loading UX) to wrap `run_pipeline()`. Store the result in `st.session_state` for rendering. Create `.streamlit/config.toml` with dark theme values from the UI-SPEC. Import `GRADE_COLORS`, `MODULE_ORDER`, and `MODULE_DISPLAY_NAMES` from `cli_renderer.py` for visual parity with the CLI.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| URL input capture | Browser (Streamlit) | — | `st.text_input` renders in browser, value sent to server on rerun |
| Pipeline execution | Streamlit Server | — | `run_pipeline()` runs synchronously in the Streamlit process |
| Result caching | Streamlit Server | — | `st.cache_data` stores pickled results server-side, keyed by URL |
| Score display (metric + grade badge) | Browser (Streamlit) | — | `st.metric` + `st.markdown` with inline HTML render in browser |
| Module detail expanders | Browser (Streamlit) | — | `st.expander` with `st.progress` bars and detail tables render in browser |
| Recommendations table | Browser (Streamlit) | — | `st.dataframe` or `st.markdown` table renders in browser |
| Error display | Browser (Streamlit) | — | `st.error` and inline error text render in browser |
| Theme / styling | Browser (Streamlit) | — | `.streamlit/config.toml` + inline CSS in `st.markdown(unsafe_allow_html=True)` |
| Grade color mapping | Shared (cli_renderer.py) | — | Imported from CLI contract; single source of truth |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Dashboard lives at `app.py` in the project root. Run with `streamlit run app.py`. All imports reference `src.checker.*` modules via absolute imports.
- **D-02:** Use `st.cache_data` with the URL as the cache key. The pipeline re-runs only when the URL changes. No `st.session_state` needed for the result — `cache_data` handles persistence across script reloads naturally.
- **D-03:** Pass the full pipeline result dict (including raw `RobotsResult`, `LlmsResult`, `SchemaAnalysis`, `ContentAnalysis`) to the dashboard render functions. Do NOT expand the `ScoreReport` dataclass — it stays as-is, shared with the CLI. The dashboard accesses raw module objects directly for expander detail content.
- **D-04:** Show all pipeline error strings verbatim in both the error banner and results area. Match CLI behavior — no parsing or categorization of error messages.

### Claude's Discretion

- Streamlit config.toml theme values (exact hex colors from UI-SPEC palette)
- Layout column ratios within the score hero section
- Expander default state (collapsed vs first one open)
- Exact `st.columns()` breakpoints for responsive layout

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | User can paste a URL into the web UI and click Analyze to trigger the full analysis pipeline | `st.text_input` + `st.button` → `run_pipeline()` call; requires orchestrator to expose raw module objects (see Gap below) |
| DASH-02 | Dashboard shows a loading spinner while analysis runs | `@st.cache_data(show_spinner="Analyzing...")` — native Streamlit spinner during cache miss |
| DASH-03 | Dashboard displays the overall score as a metric and grade as a color-coded badge (green/yellow/orange/red) | `st.metric("Overall Score", f"{score}/100")` + `st.markdown` with inline HTML badge using `GRADE_COLORS` from `cli_renderer.py` |
| DASH-04 | Dashboard shows per-module score bars and expandable detail sections for each of the four modules | `st.expander` per module with `st.progress(score)` bar inside; detail content from raw module objects (D-03) |
| DASH-05 | Dashboard displays the recommendations list at the bottom | Iterate `report.recommendations`; render priority-colored badges and messages |
| DASH-06 | Analysis results are cached so UI interactions (expanding sections, etc.) do not re-trigger the pipeline | `@st.cache_data` caches by URL; result stored in `st.session_state` for rendering; expander toggle is a UI-only event |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | 1.57.0 [VERIFIED: pip show] | Web UI framework — input, layout, caching, display | Official Streamlit project; only framework in the Python dashboard space with this component set |
| Python | 3.13.9 [VERIFIED: python3 --version] | Runtime | Already in use for the entire project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| src.checker.* | (existing) | Pipeline orchestration, contracts, scoring | Called directly from app.py — no new API layer needed |
| src.checker.cli_renderer | (existing) | GRADE_COLORS, MODULE_ORDER, MODULE_DISPLAY_NAMES | Imported for visual parity with CLI output |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Streamlit | Gradio | Gradio targets ML model demos; Streamlit has better layout primitives (columns, expanders, metrics) for dashboards |
| Streamlit | FastAPI + React | Adds a full frontend build chain; overkill for a single-page dashboard |
| `@st.cache_data` | `st.session_state` for caching | `cache_data` handles serialization, TTL, and cache invalidation natively; `session_state` would require manual hash management |

**Installation:**
```bash
# Streamlit is already in project dependencies (pyproject.toml)
pip install "streamlit>=1.57"
```

**Version verification:** Streamlit 1.57.0 confirmed installed [VERIFIED: pip show streamlit]. All required Streamlit API features (`st.cache_data`, `st.expander`, `st.metric`, `st.spinner`, `st.progress`, `st.columns`, `st.markdown` with HTML, `st.button`, `st.text_input`, `st.error`, `st.warning`) are stable and present in this version [VERIFIED: docs.streamlit.io 2025 release notes, no deprecations for these APIs through 1.57].

No additional packages are needed beyond what's already in `pyproject.toml` [VERIFIED: pyproject.toml dependencies list includes streamlit>=1.30].

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────────────────────────────────────┐
│                  USER'S BROWSER                   │
│  URL input ──► [Analyze] button                  │
│  ┌────────────────────────────────────────┐      │
│  │ Score Hero  │ Module Expanders         │      │
│  │ Metric+Badge│ Recommendations Table    │      │
│  │ Errors Callout                        │      │
│  └────────────────────────────────────────┘      │
└──────────────┬───────────────┬───────────────────┘
               │ HTTP (WebSocket)
               ▼
┌──────────────────────────────────────────────────┐
│              STREAMLIT SERVER (app.py)             │
│                                                    │
│  1. st.text_input + st.button                      │
│         │                                          │
│         ▼ (on click, if URL non-empty)             │
│  2. @st.cache_data → analyze_url(url)              │
│         │                                          │
│         │ cache MISS: calls run_pipeline(url)      │
│         │ cache HIT: returns pickled result        │
│         ▼                                          │
│  3. st.session_state.result = {dict}               │
│         │                                          │
│         ▼ (conditional: if result exists)          │
│  4. render_score_hero(result)                      │
│     render_module_expanders(result)   ◄── reads    │
│     render_recommendations(result)       raw module│
│     render_errors(result)                objects   │
│                                                    │
│  State: st.session_state tracks "analysis_done"    │
│  Theme: .streamlit/config.toml (dark)              │
└──────────────┬───────────────────────────────────┘
               │ Python import
               ▼
┌──────────────────────────────────────────────────┐
│          src.checker.orchestrator                  │
│  run_pipeline(url) → {report, errors, ...}         │
│  + raw module objects (robots_result, etc.)       │
└──────┬───────┬───────┬───────┬───────────────────┘
       │       │       │       │
       ▼       ▼       ▼       ▼
   crawler  access  schema  content  scorer
```

**Key flow:** URL text input → Analyze button clicked → `analyze_url(url)` via `@st.cache_data` → `run_pipeline()` → result stored in `st.session_state` → render functions display score hero, module expanders, recommendations, errors. On subsequent expander clicks, `st.cache_data` returns cached result instantly (no pipeline re-run).

### Recommended Project Structure

```
(project root)/
├── app.py                     # Streamlit dashboard entry point
├── .streamlit/
│   └── config.toml            # Dark theme configuration
├── src/
│   └── checker/
│       ├── orchestrator.py    # MODIFIED: add raw module objects to return dict
│       ├── contracts.py       # Unchanged — ScoreReport stays as-is
│       ├── cli_renderer.py    # Unchanged — GRADE_COLORS imported by dashboard
│       └── ...
└── tests/
    └── test_dashboard.py      # NEW: Streamlit app tests (Wave 0)
```

**Note:** No new Python package or module file is created inside `src/`. All dashboard code lives in `app.py` at project root per D-01. The `cli_renderer.py` is unchanged — the dashboard imports from it, not modifies it.

### Pattern 1: Cached Pipeline Execution
**What:** Wrap `run_pipeline()` call in `@st.cache_data` with URL as hash key. Use `show_spinner` parameter instead of separate `st.spinner()` context manager.
**When to use:** For any expensive function whose output depends solely on its arguments and should persist across Streamlit reruns.
**Example:**
```python
# Source: docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data
# Verified: Streamlit 1.57.0

@st.cache_data(show_spinner="Analyzing...")
def analyze_url(url: str, timeout: float = 10.0) -> dict:
    """Cached wrapper around run_pipeline()."""
    return run_pipeline(url, timeout=timeout)

# In the app flow:
url = st.text_input("Enter a URL to analyze", placeholder="https://example.com")
if st.button("Analyze"):
    if url:
        result = analyze_url(url)
        st.session_state.analysis_done = True
        st.session_state.current_result = result
    else:
        st.warning("Please enter a URL.")
```

**Why this pattern:** `@st.cache_data` automatically handles cache key hashing (by function arguments), serialization, TTL, and cache invalidation. The `show_spinner` parameter gives free loading UX. Using `st.session_state` to store the result object means the cached function is only called on cache miss; subsequent reruns (expander clicks, scroll) read `st.session_state.current_result` directly with zero overhead.

### Pattern 2: Grade Badge via st.markdown with Inline HTML
**What:** Render the letter grade as a large colored badge using `st.markdown(unsafe_allow_html=True)` with inline CSS styled against the `GRADE_COLORS` from `cli_renderer.py`.
**When to use:** When `st.metric()` doesn't support the visual treatment needed (48px bold grade letter with colored background).
**Example:**
```python
# Source: UI-SPEC typography + GRADE_COLORS from cli_renderer.py
# Verified: docs.streamlit.io st.markdown unsafe_allow_html support

from src.checker.cli_renderer import GRADE_COLORS

def render_grade_badge(grade: str):
    color_hex = {
        "A": "#2ecc71", "B": "#3498db", "C": "#f1c40f",
        "D": "#e67e22", "F": "#e74c3c",
    }.get(grade, "#6c757d")
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
    ">{grade}</div>
    """, unsafe_allow_html=True)
```

### Pattern 3: Module Expander with st.progress Score Bar
**What:** Each module gets an `st.expander` labeled with module name and score. Inside: `st.progress(score)` bar and module-specific detail content from raw module objects.
**When to use:** For all 4 modules (robots, llms_txt, schema, content) in MODULE_ORDER sequence.
**Example:**
```python
# Source: docs.streamlit.io st.expander + st.progress
# Verified: Streamlit 1.57.0

from src.checker.cli_renderer import MODULE_ORDER, MODULE_DISPLAY_NAMES

def render_module_expanders(pipeline_result: dict):
    report = pipeline_result["report"]
    for module_key in MODULE_ORDER:
        data = report.module_breakdown.get(module_key)
        if data is None:
            continue
        score = data["score"]
        display_name = MODULE_DISPLAY_NAMES[module_key]
        with st.expander(f"{display_name} (score: {score:.2f})"):
            st.progress(score)
            _render_module_detail(module_key, pipeline_result)
```

### Pattern 4: Empty State — No Placeholder Content
**What:** Before the first analysis, show only the URL input and Analyze button. No "Enter a URL to analyze" prompt text, no "Results will appear here" message.
**When to use:** Initial page load and after any full page refresh.
**Example:**
```python
# No conditional "no results yet" block.
# Results area renders only when st.session_state.analysis_done is True.
if st.session_state.get("analysis_done"):
    result = st.session_state.current_result
    render_score_hero(result)
    render_module_expanders(result)
    render_recommendations(result)
    render_errors(result)
# Else: nothing rendered below the input row
```

### Anti-Patterns to Avoid
- **Don't put `run_pipeline()` directly in the script body:** Would execute on every rerun (every widget interaction). Must be behind `st.cache_data` AND triggered by button click.
- **Don't use `st.spinner()` context manager separately:** `@st.cache_data(show_spinner=...)` already handles the spinner. Adding an extra `with st.spinner():` creates redundant UI elements.
- **Don't hash non-serializable objects:** `st.cache_data` uses pickle. The pipeline result dict contains Python objects (dataclasses) which are fully picklable — verified safe.
- **Don't mutate cached `st.cache_resource` objects:** Not applicable here (using `st.cache_data` which returns copies). But if accidentally switched to `cache_resource`, mutations would corrupt cross-user state.
- **Don't expand ScoreReport for dashboard rendering:** D-03 prohibits this. Keep ScoreReport as-is for CLI compatibility. Access raw module objects directly for detail content.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Function result caching | Custom dict-based cache with manual hash | `@st.cache_data` | Handles serialization, TTL, cache eviction, cross-session scope, and hash invalidation correctly |
| Loading spinner UX | Custom progress bar or `st.spinner()` context | `@st.cache_data(show_spinner="...")` | Native integration — spinner auto-shows on cache miss, hides on return |
| Score bars | Unicode block character rendering (`_render_score_bar`) | `st.progress(score_value)` | Native Streamlit component with consistent styling, accessibility, and responsive width |
| Responsive columns | Manual CSS flexbox/grid | `st.columns([ratio, ...])` | Streamlit handles breakpoints, wrapping, and consistent gap spacing |
| Layout spacing | Manual HTML divs with margins | `st.columns` gap + markdown spacing (md/lg tokens from UI-SPEC) | Streamlit's layout primitives respect the theme's spacing scale |

**Key insight:** Streamlit is the "don't hand-roll" for dashboard UI. Every custom solution (manual caching, custom CSS layouts, hand-built progress bars) adds maintenance burden for zero UX improvement. The Streamlit component set already maps 1:1 to every display requirement in this phase.

## Orchestrator Gap: Raw Module Objects Not in Return Dict

**What's missing:** `run_pipeline()` in `orchestrator.py` returns:
```python
{"report": ScoreReport, "errors": list[str], "complete": bool, "stages_run": list[str]}
```
But D-03 requires it to also include the raw module objects:
```python
{"report": ScoreReport, "errors": list[str], "complete": bool, "stages_run": list[str],
 "robots_result": RobotsResult, "llms_result": LlmsResult,
 "schema_analysis": SchemaAnalysis, "content_analysis": ContentAnalysis}
```

**Impact:** Without this change, the dashboard cannot render module detail expanders. The `ScoreReport.module_breakdown` has scores and weights but not the raw data needed: bot-by-bot status tables, llms.txt validation errors, schema type details, content sub-signal breakdowns.

**Fix:** Add 4 lines to the return statement in `orchestrator.py`:
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

This is low-risk — the variables already exist in the orchestrator's local scope. This change is backward-compatible with the CLI (it adds keys, doesn't remove or rename any).

## Runtime State Inventory

> This is NOT a rename/refactor/migration phase. Skip.

## Common Pitfalls

### Pitfall 1: st.button Resets on Rerun (stale "True" state)
**What goes wrong:** In older Streamlit versions, `st.button` returns True on click and stays True for the entire rerun, causing double-execution. In 1.57.0, `st.button` returns True only on the click-triggered rerun and False on subsequent reruns. But if `run_pipeline()` is called directly (not cached), clicking another widget would re-trigger it.
**Why it happens:** Streamlit's reactive execution model re-runs the entire script on any widget interaction. `st.button` uses a callback-based state that resets after one cycle.
**How to avoid:** Always gate expensive calls behind both (a) the button click check AND (b) `st.cache_data`. The cache ensures even if the button fires, cached results return instantly:
```python
if st.button("Analyze") and url:
    result = analyze_url(url)  # cached — returns instantly on re-click with same URL
```
**Warning signs:** Pipeline runs on every widget click, spinner appears repeatedly, "Analysis complete" message appears when clicking an expander.

### Pitfall 2: cache_data Keyed by Non-Hashable or Overly-Specific Arguments
**What goes wrong:** If `@st.cache_data` is applied to a function that receives a `timeout` float that varies per call, each unique timeout value creates a separate cache entry. The cache never hits for the same URL with different timeouts.
**Why it happens:** `st.cache_data` hashes ALL arguments by default. Different timeout values produce different hash keys.
**How to avoid:** Use a fixed timeout (10.0 per project default) for the cached wrapper, or exclude `timeout` from hashing:
```python
@st.cache_data(show_spinner="Analyzing...")
def analyze_url(url: str) -> dict:
    return run_pipeline(url, timeout=10.0)
```
**Warning signs:** Multiple cache entries for the same URL, cache grows unbounded, spinner shows even though URL hasn't changed.

### Pitfall 3: Expander Content Rendered Even When Collapsed
**What goes wrong:** Streamlit renders ALL expander body content even when collapsed. Expensive detail computations inside expanders slow down every rerun.
**Why it happens:** Streamlit executes the entire script top-to-bottom on each rerun. `with st.expander(...):` is a context manager — all code inside it executes regardless of expander state. Only the display is toggled.
**How to avoid:** Since all expensive work is cached in `analyze_url()`, rendering detail content from already-retrieved data is cheap. This pitfall is naturally avoided by the architecture. But if any additional computation is added inside expanders, it should be guarded:
```python
with st.expander("Details"):
    # This runs even when collapsed — keep it cheap
    st.write(cached_result["some_field"])  # OK: reading from cache
```
**Warning signs:** Slow UI response when expanding/collapsing sections, high CPU usage on every rerun.

### Pitfall 4: HTML/CSS in st.markdown Leaking to Other Elements
**What goes wrong:** CSS injected via `st.markdown(..., unsafe_allow_html=True)` with `<style>` tags is global — it affects ALL matching elements on the page, including those added by Streamlit's own rendering.
**Why it happens:** Streamlit doesn't scope `<style>` tags to individual `st.markdown` calls. All styles are added to the page's global stylesheet.
**How to avoid:** Use specific selectors. Prefer the `data-testid` attributes that Streamlit exposes for targeted overrides:
```python
st.markdown("""
<style>
/* Good — targets only the grade badge, not all divs */
div.grade-badge { background-color: #2ecc71; }
</style>
<div class="grade-badge">A</div>
""", unsafe_allow_html=True)
```
For general styling, use the theme config.toml or Streamlit's built-in parameters (`border=True`, `label_visibility`, etc.) instead of raw CSS.
**Warning signs:** Button colors changing unexpectedly, expander headers getting wrong fonts, other UI elements appearing with custom colors meant for the grade badge.

### Pitfall 5: st.cache_data with Mutable Data — Accidental Mutation
**What goes wrong:** Although `st.cache_data` returns a copy (pickle round-trip), developers sometimes hold a reference and mutate the returned dict. If another part of the code also holds a reference, they diverge. More critically, if the *original* cached value inside Streamlit's cache is somehow mutated (unlikely with cache_data but possible with misuse), all users see corrupted data.
**Why it happens:** Python's reference semantics. Dicts and lists are mutable. Assigning `result = cached_func()` and then `result["report"] = None` mutates only your copy, but subtle bugs arise when the same reference is passed to multiple render functions that expect consistent structure.
**How to avoid:** Treat the pipeline result dict as read-only. Render functions should read, never write. If transformation is needed, deep-copy first:
```python
import copy
display_data = copy.deepcopy(result)
```
**Warning signs:** Data appearing different between render functions, "None" appearing where a module result was expected, recommendation list shrinking between renders.

## Code Examples

Verified patterns from official Streamlit 1.57.0 documentation:

### Config.toml Dark Theme
```toml
# Source: docs.streamlit.io/develop/api-reference/configuration/config.toml
# Verified: Streamlit 1.57.0 theme section
# File: .streamlit/config.toml

[theme]
base = "dark"
primaryColor = "#3498db"
backgroundColor = "#0e1117"
secondaryBackgroundColor = "#1a1d24"
textColor = "#e0e0e0"
font = "sans serif"
```

### st.metric for Overall Score
```python
# Source: docs.streamlit.io/develop/api-reference/data/st.metric
# Verified: Streamlit 1.57.0

st.metric(
    label="Overall Score",
    value=f"{report.overall_score}/100",
    border=True,
)
```

### st.expander with Conditional Content
```python
# Source: docs.streamlit.io st.expander
# Verified: Streamlit 1.57.0

with st.expander("Robots.txt (score: 0.85)"):
    st.progress(0.85)
    st.write("Detail content here...")
```

### st.error for Pipeline Errors
```python
# Source: docs.streamlit.io st.error
# Verified: Streamlit 1.57.0

if errors:
    st.error("Analysis failed for some stages. See details below.")
    for error in errors:
        st.markdown(f"- {error}")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@st.cache` (legacy, pre-1.18) | `@st.cache_data` / `@st.cache_resource` | Streamlit 1.18 (2023) | `cache_data` replaces `cache` for data; clearer semantics |
| `st.experimental_dialog` / `st.experimental_fragment` | Removed (never stabilized) | Streamlit 1.51 | Not used in this phase — no impact |
| Python 3.9 support | Dropped — requires >=3.10 | Streamlit 1.51 | Project uses 3.13.9 — no impact |
| `st.bokeh_chart` | Removed | Streamlit 1.52 | Not used — no impact |
| `**kwargs` in `st.write` | Removed | Streamlit 1.50 | Not used — no impact |

**Deprecated/outdated:**
- `@st.cache`: Still available for backward compatibility but `cache_data`/`cache_resource` are the current API. Do not use `@st.cache`.
- `st.cache(suppress_st_warning=True)`: This was a common workaround in old Streamlit; not needed with `cache_data`.
- `st.spinner()` as a standalone context manager wrapping a cached function: Redundant with `@st.cache_data(show_spinner=...)`. Do not double-wrap.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3 | Runtime | YES | 3.13.9 [VERIFIED] | — |
| Streamlit | Web UI framework | YES | 1.57.0 [VERIFIED] | — |
| spaCy en_core_web_sm | Content analysis (via pipeline) | YES | 3.8.14 [VERIFIED] | — |
| rich | CLI renderer (GRADE_COLORS import) | YES | 13.9.4 [VERIFIED] | — |
| pytest | Dashboard tests | YES | 8.4.2 [VERIFIED] | — |

**Missing dependencies with no fallback:** None. All required dependencies are installed and version-compatible.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 |
| Config file | `pyproject.toml` (tool.pytest.ini_options) |
| Quick run command | `pytest tests/test_dashboard.py -x -v --tb=short` |
| Full suite command | `pytest tests/ -x -v --tb=short` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | URL input + Analyze button triggers pipeline | integration | `pytest tests/test_dashboard.py::test_analyze_on_click -x` | NO — Wave 0 |
| DASH-02 | Loading spinner appears during pipeline execution | integration | `pytest tests/test_dashboard.py::test_spinner_during_analysis -x` | NO — Wave 0 |
| DASH-03 | Score metric and grade badge rendered with correct color | unit | `pytest tests/test_dashboard.py::test_grade_badge_color` -x | NO — Wave 0 |
| DASH-04 | Module expanders with st.progress bars display per-module scores | unit | `pytest tests/test_dashboard.py::test_module_expanders` -x | NO — Wave 0 |
| DASH-05 | Recommendations list rendered at bottom with priority colors | unit | `pytest tests/test_dashboard.py::test_recommendations_rendered` -x | NO — Wave 0 |
| DASH-06 | Cached results returned without re-running pipeline on UI interaction | integration | `pytest tests/test_dashboard.py::test_cache_prevents_rerun` -x | NO — Wave 0 |

### Streamlit Testing Strategy
Streamlit apps are tested using `streamlit.testing.v1.AppTest` [VERIFIED: docs.streamlit.io]. This API allows simulating user interactions and asserting on rendered output without a browser. Key patterns:

```python
# Source: docs.streamlit.io/develop/concepts/testing/app_testing
from streamlit.testing.v1 import AppTest

def test_analyze_on_click():
    at = AppTest.from_file("app.py").run()
    at.text_input[0].set_value("https://example.com")
    at.button[0].click().run()
    assert not at.exception  # Pipeline completed without error
```

**Limitation:** `AppTest` verifies Streamlit element structure but cannot test actual browser rendering (CSS, layout). Visual verification requires manual review. `AppTest` is sufficient for functional correctness (DASH-01 through DASH-06 logic).

### Sampling Rate
- **Per task commit:** `pytest tests/test_dashboard.py -x -v --tb=short`
- **Per wave merge:** `pytest tests/ -x -v --tb=short`
- **Phase gate:** Full suite green + manual visual review against UI-SPEC before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_dashboard.py` — covers all DASH-01 through DASH-06
- [ ] Test fixtures for mock pipeline results (ScoreReport + raw module objects) — add to `tests/conftest.py`
- [ ] Verify `streamlit.testing.v1.AppTest` import availability (included in streamlit>=1.28, confirmed in 1.57.0)
- [ ] `tests/test_orchestrator.py` — update if orchestrator return dict is modified to include raw module objects

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | N/A — no user auth in v1 |
| V3 Session Management | No | N/A — stateless; no sessions beyond Streamlit's websocket |
| V4 Access Control | No | N/A — public dashboard, no auth |
| V5 Input Validation | Yes | URL validation already handled by `crawler.fetch_url()` (SSRF guard, scheme check). Dashboard adds `st.warning("Please enter a URL.")` for empty input. |
| V6 Cryptography | No | N/A — no secrets stored or transmitted by the dashboard |

### Known Threat Patterns for Streamlit

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious pickle payload via `st.cache_data` | Elevation of Privilege | `run_pipeline()` returns only project-defined dataclasses — no untrusted sources feed the cache. Risk is theoretical only if an attacker controls the pipeline input, which they do (the URL). But the pipeline validates URLs and processes only fetched content; no remote code execution path exists. |
| XSS via `st.markdown(unsafe_allow_html=True)` | Information Disclosure | Grade badge and error display use hardcoded color values, not user-controlled strings. If recommendation messages contain HTML-unsafe content, they should be escaped. Verify: `report.recommendations[i].message` comes from `scorer.py` string literals — no user HTML injection possible. |
| URL SSRF via text input | Spoofing | Already mitigated by `crawler.fetch_url()` which blocks localhost/private network URLs before any request is made [VERIFIED: src/checker/crawler.py SSRF guard]. |

## How the Rerun Model Affects This Dashboard

Streamlit re-executes the entire `app.py` script on every user interaction (button click, expander toggle, tab switch). This is the fundamental execution model. For this dashboard, the implications are:

1. **Everything in the script body runs every time.** Variable assignments, imports, function definitions — all re-execute.
2. **`st.cache_data` is the defense.** It short-circuits the expensive `run_pipeline()` call, returning the cached result instantly when the URL hasn't changed.
3. **`st.session_state` persists across reruns.** It's the only place to store things that survive script re-execution. The `analysis_done` flag and `current_result` dict live here.
4. **Expander clicks cause a full rerun.** When the user clicks an expander, the script re-executes. But `st.session_state.current_result` is already populated, so the code path `if st.session_state.get("analysis_done"): render_results(...)` runs with the cached data. The pipeline is not re-run.
5. **The spinner appears only on cache miss.** `@st.cache_data(show_spinner=...)` shows the spinner during the first `analyze_url()` call. On cache hits, the function returns instantly with no spinner.

This model is why the architecture MUST separate the "trigger analysis" step (button click + cache miss) from the "render results" step (session_state read + display functions). If `run_pipeline()` were called unconditionally in the script body, it would run on every rerun regardless of caching.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `st.cache_data` with scope="global" (default) is correct for this single-user dashboard. Training data suggests scope="session" might be more appropriate in Streamlit Cloud deployments, but config says this is local dev. | Standard Stack / Caching | If deployed to Streamlit Cloud with multiple users, global scope would share cached results across all users. Session scope would cache per-user. Local dev is unaffected. |
| A2 | Streamlit `AppTest` is sufficient for testing DASH-06 (cache behavior). Training data suggests AppTest can verify cache state via `at.session_state`, but this may not fully exercise the cache internals. | Validation Architecture | If AppTest cannot verify cache behavior, DASH-06 test would need manual verification or a different test approach. |
| A3 | The orchestrator modification (adding 4 raw object keys to return dict) is backward-compatible with the CLI. The CLI's `display_score_card()` accesses `pipeline_result["report"]`, `pipeline_result["errors"]`, `pipeline_result["complete"]`, `pipeline_result["stages_run"]` — none of these change. | Orchestrator Gap | CLI would break if it accesses keys by index or iterates the dict and encounters unexpected keys. Verified: CLI uses explicit key access, no iteration. |

## Open Questions (RESOLVED)

1. **Should the first module expander be open by default?** — RESOLVED: All expanders collapsed by default (`expanded=False`, the Streamlit default). Matches UI-SPEC wireframe. Implemented in Plan 07-02.

2. **How should the orchestrator patch be handled?** — RESOLVED: First task in Plan 07-01. The change is 4 lines adding raw module objects to the return dict. Unblocking prerequisite for dashboard.

3. **What if `st.cache_data` pickle fails for complex dataclass objects?** — RESOLVED: Verify pickle-ability during Plan 07-02 implementation. All objects are plain dataclasses/dicts/lists — expected to be picklable. Fall back to shallow-copy preprocessing if any object fails.

## Sources

### Primary (HIGH confidence)
- [Streamlit st.cache_data API](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data) — caching decorator signature, parameters, scope behavior
- [Streamlit st.metric API](https://docs.streamlit.io/develop/api-reference/data/st.metric) — metric component parameters, CSS customization, no-delta display
- [Streamlit Theme Configuration](https://docs.streamlit.io/develop/api-reference/configuration/config.toml) — full [theme] section options, dark/light mode, font configuration
- [Streamlit Caching Overview](https://docs.streamlit.io/develop/concepts/architecture/caching) — cache_data vs cache_resource, mutation safety, widget in cached functions
- [Streamlit 2025 Release Notes](https://docs.streamlit.io/develop/quick-reference/release-notes/2025) — breaking changes, deprecations through v1.52
- `src/checker/orchestrator.py` — current return dict structure, local variables available
- `src/checker/contracts.py` — ScoreReport, RobotsResult, LlmsResult, SchemaAnalysis, ContentAnalysis dataclass shapes
- `src/checker/cli_renderer.py` — GRADE_COLORS, MODULE_ORDER, MODULE_DISPLAY_NAMES constants
- `src/checker/scorer.py` — MODULE_WEIGHTS, GRADE_BOUNDARIES, recommendation generation
- `.planning/phases/07-streamlit-dashboard/07-UI-SPEC.md` — approved UI design contract: theme, typography, spacing, color, layout, copywriting
- `.planning/phases/07-streamlit-dashboard/07-CONTEXT.md` — implementation decisions D-01 through D-04
- `pip show streamlit` / `python3 -c "import streamlit; print(streamlit.__version__)"` — verified v1.57.0 installed

### Secondary (MEDIUM confidence)
- [Streamlit Common Bugs & Fixes](https://fixdevs.com/blog/streamlit-not-working/) — session_state reset, cache not re-running, spinner patterns
- [Streamlit Testing (AppTest)](https://docs.streamlit.io/develop/concepts/testing/app_testing) — AppTest API for functional dashboard tests

### Tertiary (LOW confidence)
- None — all key claims are verified against official docs or project source code.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Streamlit version verified via `pip show`; all required API features confirmed present in docs for 1.57.0; no additional packages needed.
- Architecture: HIGH — patterns verified against official Streamlit caching documentation; pipeline integration point confirmed by reading orchestrator source; UI-SPEC provides approved layout contract.
- Pitfalls: HIGH — pitfalls sourced from official Streamlit caching docs, community bug reports, and the Streamlit rerun model documentation.
- Orchestrator gap: HIGH — confirmed by reading `orchestrator.py` source (return statement at line 107-112).
- Environment: HIGH — all dependencies verified via `pip list` and `python3 -c` imports.

**Research date:** 2026-05-13
**Valid until:** 2026-06-13 (30 days — Streamlit API is stable; 1.57.0 is a recent release)
