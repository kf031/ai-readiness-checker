---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-02
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.4.2 |
| **Config file** | pyproject.toml (needs `[tool.pytest.ini_options]` section) |
| **Quick run command** | `pytest tests/test_crawler.py -v` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_crawler.py -v`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | CRAWL-01 | — | N/A | integration | `pytest tests/test_crawler.py::test_fetch_url_success -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 1 | CRAWL-01 | — | N/A | unit | `pytest tests/test_crawler.py::test_follows_redirects -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 1 | CRAWL-02 | T-1-01 | SSRF prevention via scheme allowlist | unit | `pytest tests/test_crawler.py::test_connection_error_returns_crawlerror -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 1 | CRAWL-02 | T-1-02 | Reject responses over size limit | unit | `pytest tests/test_crawler.py::test_timeout_returns_crawlerror -x` | ❌ W0 | ⬜ pending |
| 1-01-05 | 01 | 1 | CRAWL-02 | — | N/A | unit | `pytest tests/test_crawler.py::test_http_error_returns_crawlerror -x` | ❌ W0 | ⬜ pending |
| 1-01-06 | 01 | 1 | CRAWL-02 | T-1-03 | Reject non-http/https/file schemes | unit | `pytest tests/test_crawler.py::test_invalid_url_returns_crawlerror -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_crawler.py` — covers all CRAWL-01 and CRAWL-02 behaviors
- [ ] `tests/conftest.py` — shared fixtures (mock responses, test URLs)
- [ ] `pyproject.toml` — add `[tool.pytest.ini_options]` with `testpaths = ["tests"]`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real website fetch against live URL | CRAWL-01 | Requires internet access; unit tests use mocking | Run `python -m checker <public_url>` and verify FetchResult contains parsed HTML |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
