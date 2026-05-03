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

- [x] **SCHEMA-01**: Tool extracts all structured data from the page HTML (JSON-LD, microdata, RDFa) using extruct
- [x] **SCHEMA-02**: Tool identifies which of the 6 high-value schema types are present: Product, FAQPage, Organization/LocalBusiness, BreadcrumbList, Article/BlogPosting, Review/AggregateRating
- [x] **SCHEMA-03**: Schema results produce a 0.0–1.0 score weighted by schema type importance (FAQPage and Product weighted highest for e-commerce)

### Content Analysis

- [x] **CONT-01**: Tool computes readability of page text using textstat (Flesch Reading Ease + Gunning Fog Index) and scores the result
- [x] **CONT-02**: Tool calculates content-to-HTML ratio (plain text length / total HTML length) to detect thin or boilerplate-heavy pages
- [x] **CONT-03**: Tool uses spaCy (en_core_web_sm) to extract named entities (ORG, PRODUCT, GPE, PERSON) and scores how clearly the page identifies what it is about
- [x] **CONT-04**: Tool analyzes heading structure: checks H1 uniqueness, H2/H3 hierarchy logic, and whether headings are descriptive (>3 words)
- [x] **CONT-05**: Tool scores Q&A density: counts question sentences, question-style headings, and sentences that directly follow questions
- [x] **CONT-06**: Content module produces a combined 0.0–1.0 score from all sub-signals

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

## v2 Requirements — LLM Advisor Agent

### Skill-Calling Agent

- **AGENT-01**: Agent receives the v1 score report + original HTML and decides which fix skills to invoke based on failing modules (schema < 0.5, headings < 0.5, etc.)
- **AGENT-02**: Agent merges all skill outputs into a single improved HTML page and invokes render + explanation skills for final output
- **AGENT-03**: Agent loop is model-agnostic — initially powered by Claude Code skills, later by standalone LLM backends (Ollama, Anthropic, OpenAI)

### Fix Skills (Modular)

- **FIX-01**: fix-schema — generates missing JSON-LD blocks for schema types flagged as absent in the report
- **FIX-02**: fix-headings — restructures H1/H2/H3 hierarchy, merges duplicate H1s, makes headings descriptive
- **FIX-03**: fix-readability — rewrites dense paragraphs for lower reading grade level
- **FIX-04**: fix-qa — adds Q&A sections derived from existing content where Q&A density is low
- **FIX-05**: fix-llms-txt — generates a valid llms.txt file based on page content

### Output Skills

- **OUT-01**: render-preview — takes original + improved HTML and produces a visual before/after comparison
- **OUT-02**: explain-changes — produces a plain-English summary of every change made and why

### Skill Ecosystem

- **ECO-01**: Skills follow a standard contract (report + HTML in, changed HTML + changes list out) so third parties can add custom skills
- **ECO-02**: Skills are self-contained files in a `skills/` directory, discoverable by the agent at runtime

### LLM Backend

- **LLM-01**: Default backend is Claude Code skills (zero additional deps for Claude Code users)
- **LLM-02**: Standalone backends (Ollama local, Anthropic API, OpenAI API) added in v3
- **LLM-03**: v1 deterministic pipeline runs unchanged; LLM phase is optional (`--fix` flag / "Improve My Site" button)

---
## v3 Requirements — Distribution & Scale

### Output

- **OUT-03**: Tool can save full report as a JSON file for programmatic use
- **OUT-04**: Batch URL analysis via CSV upload

### Crawler

- **CRAWL-03**: Return response metadata (final URL after redirects, status code, headers) alongside HTML

### Bot Access

- **BOT-03**: Display per-bot status breakdown in CLI and dashboard output

### llms.txt

- **LLMS-03**: Also check for `/llms-full.txt` and include in score

### Standalone LLM Backend

- **LLM-04**: Ollama integration with a recommended small model (e.g., Llama 3.2 3B) for fully offline use
- **LLM-05**: Optional API provider support (Anthropic, OpenAI) via env vars or config file

### Deployment & Distribution

- **DIST-01**: FastAPI wrapper to expose tool as an API endpoint
- **DIST-02**: Browser extension version
- **DIST-03**: Weekly monitoring with email alerts
- **DIST-04**: Streamlit Cloud deployment with live demo badge

---

## Out of Scope

| Feature | Reason |
|---------|--------|
| User accounts / authentication | Not needed for open-source tool |
| Database / persistence layer | No state needed; each run is stateless |
| JavaScript rendering (Selenium/Playwright) | Adds complexity; handle in v3 if JS-only sites are a pain point |
| Multi-page crawling | v1 analyzes one URL; site-wide crawl is a v3 feature |
| HuggingFace dataset publishing | Post-launch activity |
| Train a citation classifier | Research project; far beyond v1 scope |

---

## Traceability

*Updated: 2026-05-03 — v2/v3 plan restructured: LLM Advisor Agent moved to v2, distribution & scale deferred to v3.*

| Requirement | Phase | Status |
|-------------|-------|--------|
| CRAWL-01 | Phase 1 — Foundation | Verified |
| CRAWL-02 | Phase 1 — Foundation | Verified |
| BOT-01 | Phase 2 — Access Signals | Verified |
| BOT-02 | Phase 2 — Access Signals | Verified |
| LLMS-01 | Phase 2 — Access Signals | Verified |
| LLMS-02 | Phase 2 — Access Signals | Verified |
| SCHEMA-01 | Phase 3 — Schema Extraction | Verified |
| SCHEMA-02 | Phase 3 — Schema Extraction | Verified |
| SCHEMA-03 | Phase 3 — Schema Extraction | Verified |
| CONT-01 | Phase 4 — Content Analysis | Verified |
| CONT-02 | Phase 4 — Content Analysis | Verified |
| CONT-03 | Phase 4 — Content Analysis | Verified |
| CONT-04 | Phase 4 — Content Analysis | Verified |
| CONT-05 | Phase 4 — Content Analysis | Verified |
| CONT-06 | Phase 4 — Content Analysis | Verified |
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
| AGENT-01 | v2 — LLM Advisor Agent | Planned |
| AGENT-02 | v2 — LLM Advisor Agent | Planned |
| AGENT-03 | v2 — LLM Advisor Agent | Planned |
| FIX-01 | v2 — Fix Skills | Planned |
| FIX-02 | v2 — Fix Skills | Planned |
| FIX-03 | v2 — Fix Skills | Planned |
| FIX-04 | v2 — Fix Skills | Planned |
| FIX-05 | v2 — Fix Skills | Planned |
| OUT-01 | v2 — Output Skills | Planned |
| OUT-02 | v2 — Output Skills | Planned |
| ECO-01 | v2 — Skill Ecosystem | Planned |
| ECO-02 | v2 — Skill Ecosystem | Planned |
| LLM-01 | v2 — LLM Backend | Planned |
| LLM-02 | v2 — LLM Backend | Planned |
| LLM-03 | v2 — LLM Backend | Planned |
| OUT-03 | v3 — Output | Planned |
| OUT-04 | v3 — Output | Planned |
| CRAWL-03 | v3 — Crawler | Planned |
| BOT-03 | v3 — Bot Access | Planned |
| LLMS-03 | v3 — llms.txt | Planned |
| LLM-04 | v3 — Standalone LLM | Planned |
| LLM-05 | v3 — Standalone LLM | Planned |
| DIST-01 | v3 — Deployment | Planned |
| DIST-02 | v3 — Deployment | Planned |
| DIST-03 | v3 — Deployment | Planned |
| DIST-04 | v3 — Deployment | Planned |
