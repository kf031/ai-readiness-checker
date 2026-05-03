---
phase: 5
slug: scorer-report
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-03
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `python3 -m pytest tests/test_scorer.py -x` |
| **Full suite command** | `python3 -m pytest tests/test_scorer.py -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python3 -m pytest tests/test_scorer.py -x`
- **After every plan wave:** Run `python3 -m pytest tests/test_scorer.py -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | SCORE-01, SCORE-02, SCORE-04 | T-05-01 / N/A | ScoreReport dataclass, compute_overall_score, letter_grade, generate_report | unit | `pytest tests/test_scorer.py -x` | ❌ W0 | ⬜ pending |
| 05-02-01 | 02 | 2 | SCORE-03 | T-05-02 / N/A | Recommendation generators, priority sorting | unit | `pytest tests/test_scorer.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_scorer.py` — 20 test cases covering SCORE-01 through SCORE-04 plus edge cases
- [ ] `src/checker/scorer.py` — new module with compute_overall_score, letter_grade, generate_recommendations, generate_report
- [ ] `src/checker/contracts.py` — ScoreReport dataclass addition
- [ ] `src/checker/__init__.py` — ScoreReport and generate_report exports

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Recommendation text readability | SCORE-03 | Subjective quality assessment | Read generated recommendations for 3 test URLs; confirm they are specific and actionable |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
