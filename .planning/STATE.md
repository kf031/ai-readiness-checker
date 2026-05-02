# Project State

**Project:** AI Readiness Checker
**Milestone:** v1.0 Initial Release
**Core Value:** A single URL input returns a clear, scored, actionable report showing exactly why a site is or isn't being picked up by AI search engines — and what to fix.

## Current Position

- **Milestone:** v1.0 Initial Release
- **Phase:** Not started (defining roadmap)
- **Plan:** —
- **Status:** Defining roadmap
- **Last activity:** 2026-05-02 — Milestone v1.0 started

## Progress

```
Research   [██████████] Done
Reqs       [██████████] Done
Roadmap    [░░░░░░░░░░] In progress
Phases     [░░░░░░░░░░] Not started
Implement  [░░░░░░░░░░] Not started
```

## Recent Decisions

| Decision | Outcome |
|----------|---------|
| Python 3.11+ floor (pandas 3.x requirement) | Confirmed |
| spaCy en_core_web_sm (not md/lg) | Confirmed — fast enough, no GPU needed |
| extruct for structured data extraction | Confirmed |
| Synchronous requests (no httpx/async) | Confirmed — single URL, no concurrency needed |
| Build order: contracts → crawler → modules → scorer → CLI → Streamlit → tests | Confirmed from research |

## Pending Todos

None yet.

## Blockers / Concerns

None yet.

## Session Continuity

Last session: 2026-05-02
Stopped at: Milestone v1.0 started, roadmap creation in progress
Next: Roadmap creation
