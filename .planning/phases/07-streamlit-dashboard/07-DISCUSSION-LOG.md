# Phase 7: Streamlit Dashboard - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-13
**Phase:** 07-streamlit-dashboard
**Areas discussed:** File organization, Pipeline caching, Module detail data access, Error display

---

## File Organization

| Option | Description | Selected |
|--------|-------------|----------|
| app.py at root | Standard Streamlit convention — `streamlit run app.py`. Keeps dashboard entry point visible at project root. | ✓ |
| src/checker/dashboard.py | Keeps all source code under src/checker/. Run with `streamlit run src/checker/dashboard.py` | |
| streamlit_app.py at root | Explicitly named, avoids ambiguity with other potential app.py files | |

**User's choice:** app.py at root
**Notes:** Standard Streamlit convention chosen.

---

## Pipeline Caching

| Option | Description | Selected |
|--------|-------------|----------|
| st.cache_data | Caches result by URL — re-runs only when URL changes. Survives script reloads. | ✓ |
| st.session_state only | Manual control — store result in session state. Clears on Streamlit script reload. | |
| Both cache_data + session_state | st.cache_data for the pipeline call, st.session_state for display/UI state | |

**User's choice:** st.cache_data
**Notes:** Simplest approach — cache key is the URL, pipeline re-runs automatically when URL changes.

---

## Module Detail Data Access

| Option | Description | Selected |
|--------|-------------|----------|
| Pass full result dict | run_pipeline() already returns the dict with raw module objects. No dataclass changes. | ✓ |
| Expand ScoreReport | Add detail fields to ScoreReport for a single-object API. Changes shared contract used by CLI too. | |

**User's choice:** Pass full result dict
**Notes:** ScoreReport stays clean. Dashboard accesses raw RobotsResult/LlmsResult/SchemaAnalysis/ContentAnalysis from the pipeline output dict.

---

## Error Display

| Option | Description | Selected |
|--------|-------------|----------|
| Show all verbatim | Display every error string in callout and results area, matching CLI behavior | ✓ |
| Categorize and label | Parse errors to label by module (crawl, robots, schema, content) | |
| Summary + expand | Show error count in banner, expandable list in results area | |

**User's choice:** Show all verbatim
**Notes:** Matches CLI behavior — no error parsing logic needed.

---

## Claude's Discretion

- Streamlit config.toml theme hex values (from UI-SPEC palette)
- Layout column ratios within the score hero section
- Expander default state (collapsed vs first one open)
- Exact `st.columns()` breakpoints for responsive layout

## Deferred Ideas

None — discussion stayed within phase scope.
