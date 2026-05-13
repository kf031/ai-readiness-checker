---
phase: 07
slug: streamlit-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-13
---

# Phase 07 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | `pyproject.toml` (tool.pytest.ini_options) |
| **Quick run command** | `pytest tests/test_dashboard.py -x -v --tb=short` |
| **Full suite command** | `pytest tests/ -x -v --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_dashboard.py -x -v --tb=short`
- **After every plan wave:** Run `pytest tests/ -x -v --tb=short`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | DASH-01 | — | N/A | integration | `pytest tests/test_dashboard.py::test_analyze_on_click -x` | NO — W0 | pending |
| TBD | TBD | TBD | DASH-02 | — | N/A | integration | `pytest tests/test_dashboard.py::test_spinner_during_analysis -x` | NO — W0 | pending |
| TBD | TBD | TBD | DASH-03 | — | N/A | unit | `pytest tests/test_dashboard.py::test_grade_badge_color -x` | NO — W0 | pending |
| TBD | TBD | TBD | DASH-04 | — | N/A | unit | `pytest tests/test_dashboard.py::test_module_expanders -x` | NO — W0 | pending |
| TBD | TBD | TBD | DASH-05 | — | N/A | unit | `pytest tests/test_dashboard.py::test_recommendations_rendered -x` | NO — W0 | pending |
| TBD | TBD | TBD | DASH-06 | — | N/A | integration | `pytest tests/test_dashboard.py::test_cache_prevents_rerun -x` | NO — W0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_dashboard.py` — stubs for all DASH-01 through DASH-06
- [ ] `tests/conftest.py` — shared fixtures for mock pipeline results (ScoreReport + raw module objects)
- [ ] Verify `streamlit.testing.v1.AppTest` import availability (included in streamlit>=1.28, confirmed in 1.57.0)
- [ ] `tests/test_orchestrator.py` — update if orchestrator return dict is modified to include raw module objects

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Visual rendering correctness | DASH-03, DASH-04 | AppTest verifies element structure but cannot test actual browser CSS/layout | Run `streamlit run app.py`, verify against UI-SPEC wireframe and color contract |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
