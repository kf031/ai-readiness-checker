# Phase 7: Streamlit Dashboard - Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Interactive web UI for running the AI readiness analysis pipeline and exploring detailed results. Users paste a URL, click Analyze, and see the overall score with grade, per-module score bars and expandable detail sections, and prioritized recommendations. This is a data dashboard — display and exploration, not data entry.

</domain>

<decisions>
## Implementation Decisions

### File Organization
- **D-01:** Dashboard lives at `app.py` in the project root. Run with `streamlit run app.py`. All imports reference `src.checker.*` modules via absolute imports.

### Pipeline Caching
- **D-02:** Use `st.cache_data` with the URL as the cache key. The pipeline re-runs only when the URL changes. No `st.session_state` needed for the result — cache_data handles persistence across script reloads naturally.

### Module Detail Data Access
- **D-03:** Pass the full pipeline result dict (including raw `RobotsResult`, `LlmsResult`, `SchemaAnalysis`, `ContentAnalysis`) to the dashboard render functions. Do NOT expand the `ScoreReport` dataclass — it stays as-is, shared with the CLI. The dashboard accesses raw module objects directly for expander detail content.

### Error Display
- **D-04:** Show all pipeline error strings verbatim in both the error banner and results area. Match CLI behavior — no parsing or categorization of error messages.

### Claude's Discretion
- Streamlit config.toml theme values (exact hex colors from UI-SPEC palette)
- Layout column ratios within the score hero section
- Expander default state (collapsed vs first one open)
- Exact `st.columns()` breakpoints for responsive layout

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase artifacts
- `.planning/phases/07-streamlit-dashboard/07-UI-SPEC.md` — Approved UI design contract: dark theme, layout wireframe, typography (4 sizes, 2 weights + grade exception), spacing (8-pt scale), color (60/30/10 split with grade colors), copywriting (CTA labels, empty/error states). Downstream agents treat this as the visual source of truth.

### Requirements
- `.planning/ROADMAP.md` §Phase 7 — 6 requirements (DASH-01 through DASH-06), 5 success criteria, dependency on Phase 5
- `.planning/REQUIREMENTS.md` — DASH-01 through DASH-06 requirement descriptions

### Data contracts
- `src/checker/contracts.py` — ScoreReport, CrawlError, FetchResult, RobotsResult, LlmsResult, SchemaAnalysis, ContentAnalysis dataclasses
- `src/checker/orchestrator.py` — `run_pipeline(url, timeout=10.0, verbose=False) -> dict` returning `{"report": ScoreReport, "errors": list[str], "complete": bool, "stages_run": list[str]}`

### Visual consistency
- `src/checker/cli_renderer.py` — GRADE_COLORS dict, MODULE_ORDER, MODULE_DISPLAY_NAMES, `_render_score_bar()` formula. Dashboard must use identical grade colors, module order, display names, and score bar rendering.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_pipeline()` from `src/checker/orchestrator.py` — The single entry point for analysis. Dashboard calls this directly with the URL from the text input.
- `ScoreReport` dataclass — Contains `overall_score`, `grade`, `module_breakdown` (dict of module → {score, weight, weighted}), `recommendations` (list of {priority, module, message}), `url`, `timestamp`.
- `GRADE_COLORS` from `cli_renderer.py` — `{"A": "green", "B": "blue", "C": "yellow", "D": "orange3", "F": "red"}`. Dashboard uses identical mapping.
- `MODULE_ORDER` and `MODULE_DISPLAY_NAMES` from `cli_renderer.py` — Display order and human-readable names for the 4 modules.

### Established Patterns
- Pipe-and-filter architecture: crawler → access_signals → schema → content → scorer. The dashboard is a consumer at the end of the pipe, identical role to the CLI.
- Dataclass contracts in `src/checker/contracts.py` — single source of truth for data shapes.
- Module display order (robots → llms_txt → schema → content) is consistent across CLI and dashboard.

### Integration Points
- Dashboard calls `run_pipeline()` — same function the CLI calls. No new API layer needed.
- Dashboard reads `ScoreReport` directly — same dataclass the CLI renderer consumes.
- Dashboard accesses raw module objects (`RobotsResult`, `LlmsResult`, `SchemaAnalysis`, `ContentAnalysis`) from the pipeline result dict for expander detail content.
- Streamlit config via `.streamlit/config.toml` — separate from the Python package config.

</code_context>

<specifics>
## Specific Ideas

No specific references or examples discussed. Standard Streamlit dashboard patterns apply.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 07-streamlit-dashboard*
*Context gathered: 2026-05-13*
