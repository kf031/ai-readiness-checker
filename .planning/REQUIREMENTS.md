# Requirements: AI Readiness Checker

**Defined:** 2026-05-02
**Core Value:** A single URL input returns a clear, scored, actionable report showing exactly why a site is or isn't being picked up by AI search engines — and what to fix.

---

## v1 Requirements

### Crawler

- [ ] **CRAWL-01**: Tool can fetch the HTML of any URL with a realistic User-Agent header and follows redirects automatically
- [ ] **CRAWL-02**: Tool handles fetch failures gracefully — connection errors, timeouts (10s), and 4xx/5xx responses return an error dict instead of raising an exception

### Bot Access

- [ ] **BOT-01**: Tool parses the site's robots.txt and reports the access status (allowed / blocked / not_mentioned) for all 7 AI bots: GPTBot, ClaudeBot, PerplexityBot, CCBot, Google-Extended, Applebot-Extended, Amazonbot
- [ ] **BOT-02**: Bot access results produce a 0.0–1.0 score: bots allowed adds points, bots blocked subtracts points, not_mentioned is neutral; missing robots.txt = 0.5

### llms.txt

- [ ] **LLMS-01**: Tool checks for a `/llms.txt` file at the site root and reports whether it was found, with a 500-character content preview if present
- [ ] **LLMS-02**: llms.txt result produces a score: valid format = 1.0, malformed = 0.3, missing = 0.0

### Schema & Structured Data

- [ ] **SCHEMA-01**: Tool extracts all structured data from the page HTML (JSON-LD, microdata, RDFa) using extruct
- [ ] **SCHEMA-02**: Tool identifies which of the 6 high-value schema types are present: Product, FAQPage, Organization/LocalBusiness, BreadcrumbList, Article/BlogPosting, Review/AggregateRating
- [ ] **SCHEMA-03**: Schema results produce a 0.0–1.0 score weighted by schema type importance (FAQPage and Product weighted highest for e-commerce)

### Content Analysis

- [ ] **CONT-01**: Tool computes readability of page text using textstat (Flesch Reading Ease + Gunning Fog Index) and scores the result
- [ ] **CONT-02**: Tool calculates content-to-HTML ratio (plain text length / total HTML length) to detect thin or boilerplate-heavy pages
- [ ] **CONT-03**: Tool uses spaCy (en_core_web_sm) to extract named entities (ORG, PRODUCT, GPE, PERSON) and scores how clearly the page identifies what it is about
- [ ] **CONT-04**: Tool analyzes heading structure: checks H1 uniqueness, H2/H3 hierarchy logic, and whether headings are descriptive (>3 words)
- [ ] **CONT-05**: Tool scores Q&A density: counts question sentences, question-style headings, and sentences that directly follow questions
- [ ] **CONT-06**: Content module produces a combined 0.0–1.0 score from all sub-signals

### Scoring & Report

- [ ] **SCORE-01**: Tool combines all four module scores into a weighted overall score (0–100): robots 20%, llms.txt 15%, schema 30%, content 35%
- [ ] **SCORE-02**: Overall score maps to a letter grade: A (85–100), B (70–84), C (55–69), D (40–54), F (0–39)
- [ ] **SCORE-03**: Tool generates a prioritized list of plain-English recommendations based on which checks failed (e.g. "GPTBot is blocked in your robots.txt")
- [ ] **SCORE-04**: Final report is a structured dict containing url, overall_score, grade, per-module breakdown with weights, recommendations, and timestamp

### CLI

- [ ] **CLI-01**: Tool can be run from the terminal as `python -m checker <url>` and displays a formatted score card using the rich library (colored grade, per-module bars, recommendations)

### Streamlit Dashboard

- [ ] **DASH-01**: User can paste a URL into the web UI and click Analyze to trigger the full analysis pipeline
- [ ] **DASH-02**: Dashboard shows a loading spinner while analysis runs
- [ ] **DASH-03**: Dashboard displays the overall score as a metric and grade as a color-coded badge (green/yellow/orange/red)
- [ ] **DASH-04**: Dashboard shows per-module score bars and expandable detail sections for each of the four modules
- [ ] **DASH-05**: Dashboard displays the recommendations list at the bottom
- [ ] **DASH-06**: Analysis results are cached so UI interactions (expanding sections, etc.) do not re-trigger the pipeline

### Tests

- [ ] **TEST-01**: pytest tests cover the robots analyzer module (test_robots.py)
- [ ] **TEST-02**: pytest tests cover the schema analyzer module (test_schema.py)
- [ ] **TEST-03**: pytest tests cover the content analyzer module (test_content.py)

---

## v2 Requirements

### Output

- **OUT-01**: Tool can save full report as a JSON file for programmatic use
- **OUT-02**: Batch URL analysis via CSV upload

### Crawler

- **CRAWL-03**: Return response metadata (final URL after redirects, status code, headers) alongside HTML

### Bot Access

- **BOT-03**: Display per-bot status breakdown in CLI and dashboard output

### llms.txt

- **LLMS-03**: Also check for `/llms-full.txt` and include in score

### Deployment & Distribution

- **DIST-01**: FastAPI wrapper to expose tool as an API endpoint
- **DIST-02**: Browser extension version
- **DIST-03**: Weekly monitoring with email alerts
- **DIST-04**: Streamlit Cloud deployment with live demo badge

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| LLM API calls (OpenAI, Anthropic, etc.) | Key differentiator is LLM-free; keeps tool free and reproducible |
| User accounts / authentication | Not needed for open-source single-URL tool |
| Database / persistence layer | No state needed in v1; each run is stateless |
| JavaScript rendering (Selenium/Playwright) | Adds complexity; handle in v2 if JS-only sites are a pain point |
| Multi-page crawling | v1 analyzes one URL; site-wide crawl is a v2 feature |
| HuggingFace dataset publishing | Post-launch activity |
| Train a citation classifier | Research project; far beyond v1 scope |

---

## Traceability

*Updated: 2026-05-02 during roadmap creation.*

| Requirement | Phase | Status |
|-------------|-------|--------|
| CRAWL-01 | Phase 1 — Foundation | Verified |
| CRAWL-02 | Phase 1 — Foundation | Verified |
| BOT-01 | Phase 2 — Access Signals | Verified |
| BOT-02 | Phase 2 — Access Signals | Verified |
| LLMS-01 | Phase 2 — Access Signals | Verified |
| LLMS-02 | Phase 2 — Access Signals | Verified |
| SCHEMA-01 | Phase 3 — Schema Extraction | Pending |
| SCHEMA-02 | Phase 3 — Schema Extraction | Pending |
| SCHEMA-03 | Phase 3 — Schema Extraction | Pending |
| CONT-01 | Phase 4 — Content Analysis | Pending |
| CONT-02 | Phase 4 — Content Analysis | Pending |
| CONT-03 | Phase 4 — Content Analysis | Pending |
| CONT-04 | Phase 4 — Content Analysis | Pending |
| CONT-05 | Phase 4 — Content Analysis | Pending |
| CONT-06 | Phase 4 — Content Analysis | Pending |
| SCORE-01 | Phase 5 — Scorer + Report | Pending |
| SCORE-02 | Phase 5 — Scorer + Report | Pending |
| SCORE-03 | Phase 5 — Scorer + Report | Pending |
| SCORE-04 | Phase 5 — Scorer + Report | Pending |
| CLI-01 | Phase 6 — Pipeline + CLI | Pending |
| DASH-01 | Phase 7 — Streamlit Dashboard | Pending |
| DASH-02 | Phase 7 — Streamlit Dashboard | Pending |
| DASH-03 | Phase 7 — Streamlit Dashboard | Pending |
| DASH-04 | Phase 7 — Streamlit Dashboard | Pending |
| DASH-05 | Phase 7 — Streamlit Dashboard | Pending |
| DASH-06 | Phase 7 — Streamlit Dashboard | Pending |
| TEST-01 | Phase 8 — Test Suite | Pending |
| TEST-02 | Phase 8 — Test Suite | Pending |
| TEST-03 | Phase 8 — Test Suite | Pending |
