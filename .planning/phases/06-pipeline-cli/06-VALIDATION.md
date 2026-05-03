---
phase: 6
slug: pipeline-cli
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-04
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 6-{P}-{T} | {P} | {W} | CLI-01 | — / — | N/A | integration | `pytest tests/test_cli.py -v` | ❌ W0 | ⬜ pending |
| 6-{P}-{T} | {P} | {W} | CLI-01 | — / — | N/A | unit | `pytest tests/test_orchestrator.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_orchestrator.py` — stubs for CLI-01 (pipeline orchestration)
- [ ] `tests/test_cli.py` — stubs for CLI-01 (CLI rendering/formatting)
- [ ] `tests/conftest.py` — shared fixtures (mock module results, sample ScoreReport)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Rich terminal color output renders correctly | CLI-01 | Color output is terminal-dependent | Run `python -m checker <url>` and verify colored grade, score bars, recommendations are visible |
| Non-TTY fallback (no escape codes) | CLI-01 | Requires actual terminal detection | Pipe output to file and verify no ANSI codes present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
