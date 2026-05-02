# Roadmap: AI Readiness Checker

## Overview

Build an open-source Python tool that scores any website's AI search engine visibility through four signal modules (robots.txt, llms.txt, schema, content), combines them into a weighted score with A-F grade, and surfaces results via CLI and Streamlit dashboard. The project follows a pipe-and-filter architecture: data contracts first, crawler as root dependency, four analysis modules in parallel, scorer/report as integration point, then thin CLI and Streamlit consumers. All 29 v1 requirements are distributed across 8 phases in dependency order.

## Phases

- [ ] **Phase 1: Foundation — Data Contracts + Crawler** - Type-safe data contracts for all inter-module communication, plus URL fetching with realistic headers and graceful error handling
- [ ] **Phase 2: Access Signals — robots.txt + llms.txt** - AI bot access analysis for 7 bots and llms.txt presence detection
- [ ] **Phase 3: Schema Extraction** - Structured data extraction and weighted scoring across 6 high-value schema types
- [ ] **Phase 4: Content Analysis** - NLP-based content quality analysis (readability, entities, headings, Q&A density)
- [ ] **Phase 5: Scorer + Report Generator** - Weighted composite scoring with A-F grade and prioritized recommendations
- [ ] **Phase 6: Pipeline Orchestrator + CLI** - Full pipeline wired into a single terminal command with rich-formatted output
- [ ] **Phase 7: Streamlit Dashboard** - Interactive web UI for URL input, score visualization, and result exploration
- [ ] **Phase 8: Test Suite** - Automated pytest coverage for robots, schema, and content analyzer modules

## Phase Details

### Phase 1: Foundation — Data Contracts + Crawler
**Goal**: Any URL can be fetched and parsed into structured HTML ready for analysis, with all downstream module input contracts defined
**Depends on**: Nothing (first phase)
**Requirements**: CRAWL-01, CRAWL-02
**Success Criteria** (what must be TRUE):
  1. Any valid URL can be passed and the system returns parsed HTML with realistic browser headers and automatic redirect following
  2. Connection errors, timeouts (10s), and HTTP errors (4xx, 5xx) return a structured error result instead of crashing
**Plans**: 2 plans in 2 waves

**Wave 1** *(no dependencies)*
- [ ] 01-01: Data Contracts + Project Setup — FetchResult/CrawlError dataclasses, pyproject.toml, package init

**Wave 2** *(blocked on Wave 1 completion)*
- [ ] 01-02: Crawler Implementation + Test Suite — fetch_url() with SSRF prevention, pytest test coverage

**Cross-cutting constraints:**
- All downstream modules (Phases 2-4) consume `FetchResult` and `CrawlError` from `src/checker/contracts.py`
- `FetchResult.soup` is non-serializable — Phase 5 scorer must use `FetchResult.html` for JSON reports

### Phase 2: Access Signals — robots.txt + llms.txt
**Goal**: AI bot access permissions and llms.txt presence are analyzed and scored for any website
**Depends on**: Nothing (URL-only analysis, no HTML dependency)
**Requirements**: BOT-01, BOT-02, LLMS-01, LLMS-02
**Success Criteria** (what must be TRUE):
  1. User can see the access status (allowed, blocked, or not_mentioned) for each of 7 AI bots from the site's robots.txt
  2. User receives a 0.0-1.0 bot access score that accounts for allowed bots (added points), blocked bots (subtracted points), and not_mentioned (neutral)
  3. User sees whether a /llms.txt file exists at the site root, with a 500-character content preview when present
  4. User receives a binary llms.txt score (1.0 when found, 0.0 when not found)
**Plans**: TBD

### Phase 3: Schema Extraction
**Goal**: Structured data is extracted from page HTML and scored across 6 high-value schema types
**Depends on**: Phase 1 (needs HTML from crawler)
**Requirements**: SCHEMA-01, SCHEMA-02, SCHEMA-03
**Success Criteria** (what must be TRUE):
  1. User can see all structured data extracted from JSON-LD, microdata, and RDFa in the page
  2. User sees which of the 6 schema types are present: Product, FAQPage, Organization/LocalBusiness, BreadcrumbList, Article/BlogPosting, Review/AggregateRating
  3. User receives a 0.0-1.0 schema score weighted by type importance (FAQPage and Product weighted highest for e-commerce)
**Plans**: TBD

### Phase 4: Content Analysis
**Goal**: Page content quality is analyzed via NLP across readability, entities, heading structure, and Q&A density, producing a combined content score
**Depends on**: Phase 1 (needs HTML from crawler)
**Requirements**: CONT-01, CONT-02, CONT-03, CONT-04, CONT-05, CONT-06
**Success Criteria** (what must be TRUE):
  1. User can see readability scores for page text including Flesch Reading Ease and Gunning Fog Index
  2. User sees the content-to-HTML ratio showing how much actual text content exists versus markup
  3. User can see named entities extracted from the page (organizations, products, locations, people)
  4. User sees heading structure analysis covering H1 uniqueness, H2/H3 hierarchy logic, and heading descriptiveness
  5. User sees a Q&A density score and receives a combined 0.0-1.0 content quality score from all sub-signals
**Plans**: TBD

### Phase 5: Scorer + Report Generator
**Goal**: All four module scores combine into a weighted final score with letter grade and prioritized plain-English recommendations
**Depends on**: Phase 2, Phase 3, Phase 4 (needs all module outputs)
**Requirements**: SCORE-01, SCORE-02, SCORE-03, SCORE-04
**Success Criteria** (what must be TRUE):
  1. User receives a single 0-100 overall score computed from all four modules with correct weights (robots 20%, llms.txt 15%, schema 30%, content 35%)
  2. User sees an A-F letter grade corresponding to their score range (A: 85-100, B: 70-84, C: 55-69, D: 40-54, F: 0-39)
  3. User receives prioritized plain-English recommendations specific to which checks failed (e.g., "GPTBot is blocked in your robots.txt")
  4. User receives a structured report dict containing url, overall_score, grade, per-module breakdown with weights, recommendations, and timestamp
**Plans**: TBD

### Phase 6: Pipeline Orchestrator + CLI
**Goal**: The full analysis pipeline runs from a single terminal command producing a rich-formatted score card
**Depends on**: Phase 5 (needs scorer/report)
**Requirements**: CLI-01
**Success Criteria** (what must be TRUE):
  1. User can run `python -m checker <url>` from the terminal and see a complete formatted score card
  2. CLI output includes colored grade, per-module score bars, and recommendations using rich library formatting
**Plans**: TBD

### Phase 7: Streamlit Dashboard
**Goal**: Interactive web UI for running the analysis pipeline and exploring detailed results
**Depends on**: Phase 5 (needs scorer/report)
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. User can paste a URL into the web UI and click Analyze to trigger the full analysis pipeline
  2. User sees a loading spinner while analysis is in progress
  3. User sees the overall score as a metric and grade as a color-coded badge (green/yellow/orange/red)
  4. User can view per-module score bars and expand detail sections for each of the four modules
  5. User sees the recommendations list at the bottom and can interact with the dashboard without the pipeline re-running
**Plans**: TBD
**UI hint**: yes

### Phase 8: Test Suite
**Goal**: Core analysis modules are covered by automated pytest tests using fixture HTML files
**Depends on**: Phase 2, Phase 3, Phase 4 (needs analyzer modules built)
**Requirements**: TEST-01, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):
  1. Running pytest passes all robots analyzer tests using fixture HTML files (no live network calls)
  2. Running pytest passes all schema analyzer tests using fixture HTML files
  3. Running pytest passes all content analyzer tests using fixture HTML files
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation — Data Contracts + Crawler | 2/2 | Planned | - |
| 2. Access Signals — robots.txt + llms.txt | 0/? | Not started | - |
| 3. Schema Extraction | 0/? | Not started | - |
| 4. Content Analysis | 0/? | Not started | - |
| 5. Scorer + Report Generator | 0/? | Not started | - |
| 6. Pipeline Orchestrator + CLI | 0/? | Not started | - |
| 7. Streamlit Dashboard | 0/? | Not started | - |
| 8. Test Suite | 0/? | Not started | - |
