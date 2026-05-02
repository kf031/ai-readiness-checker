# Architecture Research

**Domain:** Python web analysis / scoring pipeline with Streamlit UI
**Researched:** 2026-05-02
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Entry Points                           │
│  ┌──────────────────┐         ┌──────────────────────────┐  │
│  │  CLI             │         │  Streamlit UI            │  │
│  │  python -m       │         │  dashboard/app.py        │  │
│  │  checker <url>   │         │  (calls pipeline fn)     │  │
│  └────────┬─────────┘         └──────────────┬───────────┘  │
└───────────┼──────────────────────────────────┼──────────────┘
            │                                  │
            └──────────────┬───────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│                   Pipeline Orchestrator                     │
│           checker/pipeline.py  run(url) → AnalysisResult   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ crawler  │  │ robots_  │  │ llms_txt │  │ schema_  │   │
│  │ .py      │→ │ analyzer │  │ _checker │  │ analyzer │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       │                                                     │
│       ↓                                                     │
│  ┌──────────────────┐                                      │
│  │ content_analyzer │                                      │
│  └──────────────────┘                                      │
├─────────────────────────────────────────────────────────────┤
│                   Scoring + Reporting                       │
│  ┌───────────────┐           ┌───────────────────────────┐  │
│  │  scorer.py    │ ────────→ │  report.py                │  │
│  │  (weights,    │           │  (recommendations,        │  │
│  │   A-F grade)  │           │   per-module summaries)   │  │
│  └───────────────┘           └───────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│                    Shared Data Contracts                    │
│         checker/models.py  (dataclasses / TypedDicts)      │
└─────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Boundary Rule |
|-----------|---------------|---------------|
| `crawler.py` | Fetches raw HTML, headers, status code; handles redirects and errors | Returns a `FetchResult`; knows nothing about scoring |
| `robots_analyzer.py` | Parses robots.txt; checks AI bot allow/deny rules | Receives the base URL; returns `RobotsResult` |
| `llms_txt_checker.py` | GETs /llms.txt and /llms-full.txt; returns presence + excerpt | Returns `LlmsResult`; no HTML parsing |
| `schema_analyzer.py` | Extracts JSON-LD / microdata from raw HTML via extruct | Receives raw HTML string; returns `SchemaResult` |
| `content_analyzer.py` | NLP analysis: readability, ratio, Q&A density, entities | Receives parsed text (not raw HTML); returns `ContentResult` |
| `scorer.py` | Applies weights, computes final 0-100 score and A-F grade | Receives all `*Result` objects; returns `ScoreResult` |
| `report.py` | Generates prioritized human-readable recommendations | Receives `ScoreResult`; returns `Report` |
| `pipeline.py` | Orchestrates the whole run; single public function `run(url)` | Returns `AnalysisResult` (all sub-results + report bundled) |
| `dashboard/app.py` | Streamlit UI; calls `pipeline.run()` and renders output | Imports from `checker.pipeline`; owns no analysis logic |
| `__main__.py` | CLI entry point; calls `pipeline.run()` and renders via rich | Same — owns no analysis logic |

## Recommended Project Structure

```
checker/
├── __init__.py
├── __main__.py          # CLI: python -m checker <url>
├── models.py            # All shared dataclasses (data contracts)
├── pipeline.py          # Orchestrator: run(url) -> AnalysisResult
├── crawler.py
├── robots_analyzer.py
├── llms_txt_checker.py
├── schema_analyzer.py
├── content_analyzer.py
├── scorer.py
└── report.py
dashboard/
└── app.py               # Streamlit UI only
tests/
├── unit/
│   ├── test_crawler.py
│   ├── test_robots_analyzer.py
│   ├── test_schema_analyzer.py
│   ├── test_content_analyzer.py
│   ├── test_scorer.py
│   └── test_report.py
├── integration/
│   └── test_pipeline.py # Full run against a real/fixture URL
└── fixtures/
    ├── sample.html
    ├── robots.txt
    └── llms.txt
requirements.txt
pyproject.toml
```

### Structure Rationale

- **`models.py` as central hub:** All dataclasses live in one file so any module can import them without circular dependencies. This is the single source of truth for what data looks like between modules.
- **`pipeline.py` as orchestrator:** Neither the CLI nor Streamlit should know which modules exist or in what order to call them. The pipeline function is the only place that knows the execution order.
- **`dashboard/` separate from `checker/`:** The Streamlit app is a consumer of the library, not part of it. This separation means you can `import checker.pipeline` in any context without pulling in Streamlit.
- **`tests/fixtures/`:** Real HTML/robots.txt/llms.txt samples decouple tests from live network calls.

## Architectural Patterns

### Pattern 1: Central Data Contracts (models.py)

**What:** Each analyzer module returns a typed dataclass. All dataclasses are defined in one place — `checker/models.py`. Modules import from there; they never define their own ad-hoc dicts or tuples as outputs.

**When to use:** Any time two modules need to exchange structured data. In this project, every analyzer-to-scorer handoff is a contract.

**Trade-offs:** One extra file to maintain; pays off immediately when you add a field to `SchemaResult` and the type checker tells you everywhere that breaks.

**Example:**
```python
# checker/models.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class FetchResult:
    url: str
    html: str
    status_code: int
    final_url: str          # after redirects
    error: Optional[str] = None

@dataclass
class RobotsResult:
    score: float            # 0.0 - 1.0
    bots_blocked: list[str]
    bots_allowed: list[str]
    has_robots_txt: bool

@dataclass
class SchemaResult:
    score: float
    types_found: list[str]
    item_count: int

@dataclass
class ContentResult:
    score: float
    readability_score: float
    content_html_ratio: float
    word_count: int
    entity_count: int

@dataclass
class ScoreResult:
    final_score: float      # 0-100
    grade: str              # A-F
    robots_score: float
    llms_score: float
    schema_score: float
    content_score: float

@dataclass
class AnalysisResult:
    fetch: FetchResult
    robots: RobotsResult
    llms: 'LlmsResult'
    schema: SchemaResult
    content: ContentResult
    score: ScoreResult
    recommendations: list[str]
```

### Pattern 2: Pipeline Orchestrator Function

**What:** A single `run(url: str) -> AnalysisResult` function in `pipeline.py` calls each analyzer in order, threading results through. Both the CLI and Streamlit call this one function. No analysis logic lives in either entry point.

**When to use:** Always — this is what keeps the CLI and Streamlit in sync automatically.

**Trade-offs:** You cannot easily parallelize analyzers without more work (fine for v1 — single-URL, sequential is fast enough).

**Example:**
```python
# checker/pipeline.py
from checker.crawler import fetch
from checker.robots_analyzer import analyze_robots
from checker.llms_txt_checker import check_llms
from checker.schema_analyzer import analyze_schema
from checker.content_analyzer import analyze_content
from checker.scorer import score
from checker.report import generate_report
from checker.models import AnalysisResult

def run(url: str) -> AnalysisResult:
    fetch_result = fetch(url)
    robots_result = analyze_robots(url)
    llms_result = check_llms(url)
    schema_result = analyze_schema(fetch_result.html)
    content_result = analyze_content(fetch_result.html)
    score_result = score(robots_result, llms_result, schema_result, content_result)
    recommendations = generate_report(score_result)
    return AnalysisResult(
        fetch=fetch_result,
        robots=robots_result,
        llms=llms_result,
        schema=schema_result,
        content=content_result,
        score=score_result,
        recommendations=recommendations,
    )
```

### Pattern 3: Streamlit Calls Pipeline via st.cache_data

**What:** Wrap the `pipeline.run()` call with `@st.cache_data` so repeated analysis of the same URL within a session does not re-fetch and re-analyze. Store the returned `AnalysisResult` in `st.session_state` so the full result is available across widget interactions (e.g., expanding sections after the run).

**When to use:** Any Streamlit app that calls an expensive Python function on user input.

**Trade-offs:** `@st.cache_data` caches globally across all users (same URL = same cached result). Fine for a public demo tool — desirable, even. Use `st.session_state` for per-user state (e.g., which sections the user has expanded).

**Example:**
```python
# dashboard/app.py
import streamlit as st
from checker.pipeline import run

@st.cache_data(show_spinner=False)
def cached_run(url: str):
    return run(url)

url = st.text_input("Enter a URL")
if st.button("Analyze"):
    with st.spinner("Analyzing..."):
        result = cached_run(url)
    st.session_state["result"] = result

if "result" in st.session_state:
    r = st.session_state["result"]
    st.metric("AI Readiness Score", r.score.final_score)
    st.metric("Grade", r.score.grade)
    with st.expander("Robots.txt"):
        st.json(r.robots.__dict__)
    # ... etc
```

## Data Flow

### Full Pipeline Flow

```
User provides URL
    ↓
pipeline.run(url)
    ↓
crawler.fetch(url) ──────────────────────────→ FetchResult
    │ (base URL)                                    │
    ├──→ robots_analyzer.analyze_robots(url) → RobotsResult
    ├──→ llms_txt_checker.check_llms(url)  → LlmsResult
    ├──→ schema_analyzer.analyze_schema(html) → SchemaResult
    └──→ content_analyzer.analyze_content(html) → ContentResult
                                                    │
                           scorer.score(*results) ←─┘
                                   ↓
                             ScoreResult
                                   ↓
                     report.generate_report(score_result)
                                   ↓
                             list[str] recommendations
                                   ↓
                           AnalysisResult (everything bundled)
                                   ↓
                    ┌──────────────┴───────────────┐
                    ↓                              ↓
            CLI renders                   Streamlit renders
            (rich table)                  (gauge, sections)
```

### Key Data Flow Rules

1. `crawler.py` is the only module that makes HTTP requests to the target URL. `robots_analyzer` and `llms_txt_checker` also make HTTP requests — to `<base_url>/robots.txt` and `<base_url>/llms.txt` respectively. These are each simple GETs on known paths; no HTML passed in.
2. Raw HTML is passed as a string to `schema_analyzer` and `content_analyzer`. They do not fetch anything.
3. `scorer.py` receives only the four `*Result` objects, not raw HTML. It knows nothing about HTTP or parsing.
4. `report.py` receives only the `ScoreResult`. It does not re-read HTML or re-score.
5. Neither `dashboard/app.py` nor `__main__.py` imports any individual analyzer — only `checker.pipeline`.

## Build Order

Build in this dependency order — each step has everything it needs before you start it:

| Step | Module(s) | Why This Order |
|------|-----------|----------------|
| 1 | `models.py` | Defines all dataclasses; every other module imports from here. Build first. |
| 2 | `crawler.py` | No dependencies except `models.py`. FetchResult is needed by two other modules. |
| 3 | `robots_analyzer.py` | Only needs base URL; independent of crawler result. |
| 4 | `llms_txt_checker.py` | Only needs base URL; independent of crawler result. |
| 5 | `schema_analyzer.py` | Needs `FetchResult.html`. Crawler must be done. |
| 6 | `content_analyzer.py` | Needs `FetchResult.html`. Crawler must be done. |
| 7 | `scorer.py` | Needs all four `*Result` types. Steps 3-6 must be done. |
| 8 | `report.py` | Needs `ScoreResult`. scorer must be done. |
| 9 | `pipeline.py` | Wires everything together. All modules must be done. |
| 10 | `__main__.py` (CLI) | Calls `pipeline.run()`; needs pipeline done. |
| 11 | `dashboard/app.py` | Calls `pipeline.run()`; needs pipeline done. |
| 12 | `tests/` | Written alongside each module but run after integration is possible. |

## Testing Strategy

### Layer-by-Layer Approach

**Unit tests — pure function modules (no network):**

Each analyzer module should accept inputs (URL string or HTML string) that can be provided as fixtures. Mock `requests.get` at the module level so no network calls happen in unit tests.

```
tests/unit/test_crawler.py       → mock requests.get; test redirect handling, error cases
tests/unit/test_robots_analyzer.py → pass fixture robots.txt content; test bot rules
tests/unit/test_schema_analyzer.py → pass fixture HTML; assert types_found
tests/unit/test_content_analyzer.py → pass fixture HTML; assert score range
tests/unit/test_scorer.py        → pass hand-crafted *Result objects; assert weights apply correctly
tests/unit/test_report.py        → pass hand-crafted ScoreResult; assert recommendations generated
```

Key pattern: each analyzer should accept its primary input (html: str or url: str) as a plain argument. Do not embed `requests.get` calls deep inside class constructors — put them at the top of the function so they are easy to mock.

**Integration test — full pipeline:**

```
tests/integration/test_pipeline.py → call pipeline.run() against a local HTTP server
                                     (use pytest-httpserver or responses library)
                                     OR use a real stable URL in CI with network access
```

The integration test verifies the modules actually compose correctly and the `AnalysisResult` is fully populated.

**Streamlit UI:**

Streamlit does not have a built-in test runner. The accepted pattern is:
- Test all logic in `checker/` with pytest (above).
- For the Streamlit app itself, do a manual smoke test or use `streamlit.testing.v1` (available since Streamlit 1.28) which allows headless script simulation.

```python
from streamlit.testing.v1 import AppTest

def test_app_loads():
    at = AppTest.from_file("dashboard/app.py")
    at.run()
    assert not at.exception
```

### Fixture Strategy

Store real-world sample files in `tests/fixtures/`:
- `sample.html` — a realistic e-commerce page HTML
- `robots.txt` — one that blocks GPTBot, one that allows all
- `llms.txt` — a valid example

This decouples every unit test from the network entirely.

## Anti-Patterns

### Anti-Pattern 1: Logic in Entry Points

**What people do:** Put scoring logic or data manipulation in `dashboard/app.py` or `__main__.py` because it's fast to write there.

**Why it's wrong:** The CLI and UI then diverge. A bug fix in one doesn't apply to the other. The entry points become untestable.

**Do this instead:** Entry points call `pipeline.run()` and render. Nothing else.

### Anti-Pattern 2: Passing Raw HTML Through the Whole Chain

**What people do:** Pass the `FetchResult` object (containing raw HTML) through every module so each one can pick what it needs.

**Why it's wrong:** `scorer.py` ends up with access to raw HTML it doesn't need. Module boundaries blur. Tests become harder to set up.

**Do this instead:** Each module receives only the inputs it specifically needs. `schema_analyzer` gets `html: str`. `scorer` gets four `*Result` objects. `pipeline.py` is the only place that threads data between them.

### Anti-Pattern 3: Ad-hoc Dicts as Return Types

**What people do:** Return `{"score": 0.8, "bots_blocked": [...]}` from analyzers instead of typed dataclasses.

**Why it's wrong:** No autocomplete. No static analysis. A key rename in one module silently breaks `scorer.py` with a `KeyError` at runtime instead of a type error at write time.

**Do this instead:** Use dataclasses from `models.py`. Plain Python, no extra dependency, IDE-friendly, and easy to test.

### Anti-Pattern 4: Fetching Inside Streamlit's Script Body (Not Cached)

**What people do:** Call `pipeline.run(url)` directly in the Streamlit script body without `@st.cache_data`.

**Why it's wrong:** Every widget interaction (clicking an expander, moving a slider) causes Streamlit to rerun the entire script, re-fetching and re-analyzing the URL. Slow, wasteful, potentially rate-limited.

**Do this instead:** Wrap `pipeline.run` in a `@st.cache_data` decorated function. Store the result in `st.session_state` for UI interaction after the run completes.

## Integration Points

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `crawler` → `schema_analyzer` | `html: str` (plain string) | Not the full FetchResult — just the field needed |
| `crawler` → `content_analyzer` | `html: str` (plain string) | Same principle |
| all analyzers → `scorer` | `RobotsResult, LlmsResult, SchemaResult, ContentResult` | Typed dataclasses only |
| `scorer` → `report` | `ScoreResult` | Only the scored output, not raw analyzer results |
| `pipeline` → CLI/Streamlit | `AnalysisResult` | Entire bundle; entry points read what they need |

### External Dependencies

| Library | Used By | Notes |
|---------|---------|-------|
| `requests` | `crawler`, `robots_analyzer`, `llms_txt_checker` | Mock in all unit tests |
| `BeautifulSoup4` | `crawler` (parse), `content_analyzer` | Pin version in requirements.txt |
| `extruct` | `schema_analyzer` | Can be slow on large pages; acceptable for single URL |
| `spaCy en_core_web_sm` | `content_analyzer` | Load model once; if used in Streamlit use `@st.cache_resource` not `@st.cache_data` |
| `textstat` | `content_analyzer` | Pure Python, no network, easy to test |
| `streamlit` | `dashboard/app.py` only | Never imported in `checker/` |
| `rich` | `__main__.py` only | Never imported in `checker/` |

**Important note on spaCy in Streamlit:** The spaCy `nlp` model object is a resource (not serializable data), so use `@st.cache_resource` to load it once per app session — not `@st.cache_data`. Pass the loaded `nlp` object into `content_analyzer` or load it inside the module with a module-level singleton.

## Scaling Considerations

This is a single-URL, on-demand analysis tool. Scaling is not a v1 concern. For reference:

| Scale | Architecture Adjustment |
|-------|------------------------|
| Single user, local | Current design; sequential pipeline is fine |
| Demo app, multiple concurrent users | Streamlit shares `@st.cache_data` across sessions (good for popular URLs); spaCy model cached with `@st.cache_resource` so it loads once per process |
| v2: batch/CSV | Wrap pipeline in `concurrent.futures.ThreadPoolExecutor`; `requests` is the bottleneck, not CPU |
| v2: hosted API | Extract `checker/` as a library; add FastAPI on top; `checker/` code unchanged |

## Sources

- Streamlit caching documentation: https://docs.streamlit.io/develop/concepts/architecture/caching
- Streamlit session state: https://docs.streamlit.io/develop/api-reference/caching-and-state/st.session_state
- Streamlit testing: https://docs.streamlit.io/develop/api-reference/app-testing
- Python dataclasses vs Pydantic for pipeline contracts: https://towardsdatascience.com/pydantic-or-dataclasses-why-not-both-convert-between-them-ba382f0f9a9c/
- Modular pipeline pattern (pipe-and-filter): https://medium.com/@dkraczkowski/the-elegance-of-modular-data-processing-with-pythons-pipeline-approach-e63bec11d34f
- Integration testing Python data pipelines: https://www.startdataengineering.com/post/python-datapipeline-integration-test/
- Pytest mocking strategies: https://codilime.com/blog/testing-apis-with-pytest-mocks-in-python/

---
*Architecture research for: AI Readiness Checker (Python web analysis pipeline)*
*Researched: 2026-05-02*
