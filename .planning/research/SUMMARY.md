# Project Research Summary

**Project:** AI Readiness Checker
**Domain:** Python web scraping + NLP scoring pipeline with Streamlit UI
**Researched:** 2026-05-02
**Confidence:** HIGH

## Executive Summary

The AI Readiness Checker is a single-URL analysis tool that scores a website's AI/GEO (Generative Engine Optimization) readiness across four dimensions: robots.txt AI bot access, llms.txt presence, structured data (JSON-LD schema), and content quality (NLP-based). The expert approach is a modular pipe-and-filter pipeline: a central crawler feeds typed data contracts to independent analyzer modules, which feed a scorer, which feeds a report generator. Both a CLI and a Streamlit UI consume the same pipeline function. The stack is Python 3.11+, requests + BeautifulSoup4/lxml for fetching, extruct for schema extraction, spaCy + textstat for NLP, and rich/Streamlit for output. No LLM API key is required — this is the project's primary differentiator over all existing open-source alternatives.

The recommended build order follows the dependency graph: define data contracts (models.py) first, build the crawler second, then the four analysis modules in parallel, then the scorer and report generator, then wire the pipeline, and finally build the CLI and Streamlit UI as thin consumers. Testing should use fixture HTML files throughout so no live network calls are needed in unit tests. This order eliminates integration surprises and means the CLI is functional and testable before any UI work begins.

The critical risks are infrastructure-level, not domain-level: bot detection blocking crawls with default headers, extruct crashing on malformed JSON-LD from real CMS platforms, spaCy receiving raw HTML instead of cleaned text, textstat producing invalid scores on thin-content pages, and the scorer failing silently when any sub-score is None. Each of these is a predictable, well-documented failure mode with a known fix — but all must be addressed during the module build, not retrofitted afterward. A secondary risk is Streamlit's stateless re-execution model, which requires explicit caching to avoid re-running the full pipeline on every UI interaction.

## Key Findings

### Recommended Stack

The stack is fully determined. Python 3.11 is the hard minimum floor set by pandas 3.x. The core pipeline uses requests 2.33.1 (synchronous, no async needed for single-URL), BeautifulSoup4 4.14.3 with lxml backend (5-10x faster than html.parser), extruct 0.18.0 (only library that handles JSON-LD + microdata in one call), spaCy 3.8.14 with en_core_web_sm (fast NER without GPU), and textstat 0.7.13 (readability scoring). Output layers are rich 15.0.0 for CLI and Streamlit 1.57.0 for the web UI. Notably, the spaCy model requires a separate download step (`python -m spacy download en_core_web_sm`) that cannot be handled by a normal pip install — this must be an explicit step in setup instructions, CI, and Docker.

**Core technologies:**
- Python 3.11+: runtime — floor set by pandas 3.x; avoid 3.13+ until spaCy wheels ship reliably
- requests 2.33.1: HTTP fetching — synchronous is sufficient; httpx adds complexity for zero benefit
- beautifulsoup4 4.14.3 + lxml: HTML parsing — lxml backend is 5-10x faster; BS4 is more ergonomic than raw lxml
- extruct 0.18.0: structured data extraction — only library handling JSON-LD + microdata in one call; restrict syntaxes to `['json-ld', 'microdata']` (RDFa is unstable)
- spaCy 3.8.14 (en_core_web_sm): NLP pipeline — fastest production NER; sm model is sufficient for single-page entity detection
- textstat 0.7.13: readability scoring — zero-dependency, actively maintained
- rich 15.0.0: CLI output — standard for Python CLI tables and formatting
- streamlit 1.57.0: web UI — best Python-native interactive demo with no backend required
- pandas 3.0.2: score table assembly — major version with Copy-on-Write default; use `.loc[]` not chained assignment

### Expected Features

No existing open-source Python tool runs the full robots.txt + llms.txt + schema + NLP pipeline without requiring a paid LLM API key. This tool closes that gap.

**Must have (table stakes):**
- robots.txt AI bot analysis (GPTBot, ClaudeBot, PerplexityBot, CCBot, Google-Extended, Applebot-Extended, Amazonbot) — every competitor checks this; users' first question
- llms.txt presence check and content preview — standard expectation since 2025; 5 of 7 competing tools check it
- Structured data detection for 6 JSON-LD types (FAQPage, Organization, Article, Product, BreadcrumbList, Review) — highest-signal GEO factor; 6 of 7 tools check schema
- Weighted final score + A-F letter grade — all comparable tools produce a single number
- Per-module score breakdown — users need to know where to fix, not just their overall score
- Prioritized actionable recommendations — "add FAQPage schema", not just "schema missing"
- URL input with instant results, no signup — table stakes UX
- Graceful error handling for failed fetches — users will enter 403s, timeouts, redirects

**Should have (competitive differentiators):**
- spaCy entity clarity as an explicit score signal — no competing tool exposes NER analysis as a distinct score component
- Q&A density in body text (not just schema presence) — no reviewed tool measures interrogative sentences + co-located answers
- Content-to-HTML ratio — "token-efficient content" mentioned in research but not quantified anywhere
- CLI entry point (`python -m checker <url>`) — all reviewed tools are browser-only; strong differentiator for developer audience
- Schema type specificity (which of the 6 types are present vs. missing) — competing tools report schema present/absent but not which types
- Transparent, documented score weights (20/15/30/35) — credibility signal for open-source audience

**Defer (v2+):**
- Batch / CSV URL upload — adds state management and storage complexity; wait for evidence users want it
- FastAPI wrapper — wait until Streamlit demo proves demand for programmatic access
- Real-time monitoring / alerts — requires backend scheduler and email/webhook infrastructure
- Browser extension — distribution channel; only after Streamlit validates demand
- Competitor comparison — multi-URL analysis doubles crawl complexity

### Architecture Approach

The architecture is a classical pipe-and-filter pipeline with a single public entry point (`pipeline.run(url) -> AnalysisResult`). All inter-module communication uses typed dataclasses defined in a central `models.py` — never ad-hoc dicts. The pipeline orchestrator is the only module that knows execution order; neither the CLI nor Streamlit imports any individual analyzer. This means CLI and Streamlit are guaranteed to stay in sync, both modules are independently testable against fixture files, and v2 additions (batch mode, FastAPI) can wrap the same `checker/` library without touching any analysis logic.

**Major components:**
1. `models.py` — central data contracts (all dataclasses); imported by every module; built first
2. `crawler.py` — HTTP fetch with realistic headers, redirect handling, encoding-safe BS4 parsing; root dependency
3. `robots_analyzer.py` — robots.txt fetch + per-bot allow/deny parsing (line-by-line, not urllib.robotparser)
4. `llms_txt_checker.py` — GET /llms.txt and /llms-full.txt; returns presence + excerpt
5. `schema_analyzer.py` — extruct-based JSON-LD/microdata extraction; wrapped in broad try/except
6. `content_analyzer.py` — BeautifulSoup text extraction then spaCy NER + textstat readability; text cleaned before NLP
7. `scorer.py` — weighted aggregation with dynamic re-weighting around None sub-scores; clamped 0-100
8. `report.py` — prioritized human-readable recommendations from ScoreResult
9. `pipeline.py` — single `run(url)` function; wires all modules; consumed by both entry points
10. `__main__.py` / `dashboard/app.py` — thin CLI and Streamlit consumers; own no analysis logic

### Critical Pitfalls

1. **Default requests User-Agent blocked by CDNs** — set a full realistic browser User-Agent + Accept headers in `crawler.py` from the start; a 200 response with a block page body is the failure mode (check `len(response.text) > 2000`)
2. **extruct crashes on malformed JSON-LD** — Shopify/WooCommerce CMS platforms regularly produce trailing semicolons and unclosed braces; wrap `extruct.extract()` in a broad `except Exception` that returns empty dicts per syntax
3. **spaCy receives raw HTML or oversized text** — strip `<script>`, `<style>`, `<noscript>` tags with BeautifulSoup before calling `nlp()`; truncate to 50,000 characters; disable unused pipeline components (`disable=["parser"]`)
4. **textstat ZeroDivisionError / garbage scores on thin content** — guard every textstat call with a `lexicon_count()` check; return `None` (not `0`) if word count < 50; clamp all scores to 0-100
5. **Scorer NaN/TypeError when any sub-score is None** — implement dynamic re-weighting: filter out None sub-scores, recalculate weights over available scores only; clamp final result
6. **urllib.robotparser does not implement RFC 9309** — `can_fetch()` silently misfires on wildcard rules and Allow/Disallow ordering; parse the raw robots.txt text line-by-line for specific bot agent names instead
7. **Streamlit re-runs full pipeline on every UI interaction** — wrap `pipeline.run()` in `@st.cache_data(ttl=300)`; load spaCy model with `@st.cache_resource` (model is a resource, not serializable data)

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation — Data Contracts + Crawler
**Rationale:** The crawler is the root dependency for all four analysis modules. Nothing downstream can be built or tested without it. models.py must exist before the crawler so there is something to return.
**Delivers:** A working `FetchResult` from any URL, with realistic headers, redirect handling, error handling, and encoding-safe HTML parsing. All downstream modules have their input contract.
**Addresses:** robots.txt fetch, llms.txt fetch, schema extraction input, content analysis input
**Avoids:** Default User-Agent blocking (Pitfall 1), BeautifulSoup encoding mojibake (Pitfall 8); both must be addressed here before any downstream module is built on a broken foundation

### Phase 2: Access Signal Modules — robots.txt + llms.txt
**Rationale:** These two modules depend only on the base URL (not the fetched HTML) and have LOW implementation complexity. They produce the two lowest-weight but most visible signals. Building them early validates the data contract pattern before tackling the harder NLP work.
**Delivers:** `RobotsResult` (7 AI bot allow/deny statuses) and `LlmsResult` (presence + excerpt). These are the features users will demo first.
**Uses:** Line-by-line robots.txt parsing (RFC 9309 compliance)
**Implements:** robots_analyzer.py, llms_txt_checker.py
**Avoids:** urllib.robotparser RFC mismatch (Pitfall 7)

### Phase 3: Schema Extraction Module
**Rationale:** Schema is the highest single-category weight (30%) and the most common action item for e-commerce users. It depends on the crawler's HTML output. extruct is the most failure-prone external dependency and must be hardened before integration.
**Delivers:** `SchemaResult` with 6 JSON-LD type detections and an item count. The try/except wrapper established here sets the standard for all external library calls.
**Uses:** extruct 0.18.0 with `syntaxes=['json-ld', 'microdata']`
**Avoids:** extruct malformed JSON-LD crash (Pitfall 2); must be hardened before any real-world URL is tested

### Phase 4: Content Analysis Module
**Rationale:** The highest-weight module (35%) and most complex to implement. Depends on crawler HTML. Both spaCy and textstat have well-documented failure modes that must be addressed in this phase. spaCy model download is a setup dependency that must be documented.
**Delivers:** `ContentResult` with readability score, entity count, Q&A density, content-to-HTML ratio, word count. This is the primary differentiator over all existing open-source tools.
**Uses:** spaCy 3.8.14 + en_core_web_sm, textstat 0.7.13, BeautifulSoup4 text extraction
**Avoids:** spaCy max_length crash and HTML noise (Pitfall 3), textstat thin-content failures (Pitfall 4)

### Phase 5: Scorer + Report Generator
**Rationale:** Scorer is the integration point for all four module outputs. Report generator produces the human-readable recommendations. Both require all four *Result types to exist before they can be built or tested meaningfully. None-handling must be a first-class requirement.
**Delivers:** `ScoreResult` (0-100 score, A-F grade, per-module breakdown) and prioritized recommendations list. This is the first time a complete end-to-end result exists.
**Implements:** scorer.py with dynamic re-weighting, report.py with per-module recommendation logic
**Avoids:** Scorer NaN/TypeError from None sub-scores (Pitfall 5)

### Phase 6: Pipeline Orchestrator + CLI
**Rationale:** pipeline.py wires all modules together into a single `run(url)` function. The CLI (`__main__.py`) is then a thin consumer of that function. Building CLI before Streamlit validates the full pipeline without UI complexity and produces a demonstrable, testable artifact.
**Delivers:** `python -m checker <url>` produces a complete rich-formatted CLI report. The pipeline is integration-tested. This is the primary portfolio demo artifact.
**Uses:** rich 15.0.0 for formatted terminal output
**Implements:** pipeline.py, __main__.py

### Phase 7: Streamlit Dashboard
**Rationale:** Streamlit consumes the same `pipeline.run()` function as the CLI. Built last because all analysis logic is already complete and tested. Caching must be implemented from the start, not retrofitted.
**Delivers:** Interactive web UI at `streamlit run dashboard/app.py` with score gauge, per-module expandable sections, and recommendations. Shareable demo URL for portfolio/social.
**Avoids:** Streamlit pipeline rerun on every interaction (Pitfall 6); `@st.cache_data` and `@st.cache_resource` must be in place from the first working UI commit

### Phase Ordering Rationale

- Crawler first because it is the literal root dependency — FEATURES.md explicitly calls it out as such and ARCHITECTURE.md's build order table lists it as Step 2 (after models.py)
- robots + llms before schema + content because they have LOW complexity and no shared dependencies with the harder modules; early wins that validate the data contract pattern
- Schema before content because extruct failures are more catastrophic (pipeline crash) than textstat failures (bad number); hardening the crash-prone module first reduces integration risk
- Scorer after all four modules because it literally cannot be tested meaningfully until all inputs exist
- CLI before Streamlit because CLI has zero UI state complexity; validates the full pipeline before adding Streamlit's caching and re-execution model

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Content Analysis):** The Q&A density algorithm (counting interrogative sentences + co-located answers in HTML) is novel — no reference implementation exists in the research. Needs design work during planning.
- **Phase 5 (Scorer):** The exact weight thresholds for A-F grade cutoffs are not empirically validated — the 20/15/30/35 weights come from the project spec, not benchmarked data. Should be explicitly called out as adjustable.

Phases with standard patterns (skip research-phase):
- **Phase 1 (Crawler):** requests + BS4 + lxml is fully documented; pitfalls are known and fixes are specified
- **Phase 2 (robots + llms):** GET request + line parsing; no novel logic
- **Phase 3 (Schema):** extruct API is documented; the try/except pattern is the entire architecture
- **Phase 6 (Pipeline + CLI):** pure wiring + rich formatting; well-documented patterns
- **Phase 7 (Streamlit):** `@st.cache_data` pattern is directly documented in Streamlit official docs

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI; release dates confirmed; compatibility matrix checked |
| Features | HIGH for table stakes, MEDIUM for differentiators | Table stakes verified across 6+ comparable tools; differentiator value is inferred from competitor gaps, not user research |
| Architecture | HIGH | Patterns verified against Streamlit docs, Python pipeline literature, and official library docs |
| Pitfalls | HIGH | Each pitfall traced to specific GitHub issues in the relevant library repos |

**Overall confidence:** HIGH

### Gaps to Address

- **Q&A density algorithm:** No reference implementation found. The concept (interrogative sentence + co-located answer in HTML) is research-backed but the scoring formula needs to be designed during Phase 4 planning.
- **A-F grade thresholds:** The 0-100 score breakpoints for letter grades are not in the research. These need to be set with explicit rationale during Phase 5 planning and flagged as tunable post-launch.
- **spaCy entity clarity scoring formula:** FEATURES.md describes this as a differentiator but the specific algorithm (entity density, type diversity, ambiguity) is not defined. Needs design during Phase 4.
- **Real-world accuracy validation:** The tool's correctness (does it actually predict AI citation likelihood?) cannot be validated until post-launch user feedback. Frame v1 as a best-practices signal, not a guarantee.

## Sources

### Primary (HIGH confidence)
- PyPI: extruct 0.18.0, spaCy 3.8.14, textstat 0.7.13, streamlit 1.57.0, pandas 3.0.2, requests 2.33.1, beautifulsoup4 4.14.3, rich 15.0.0, pytest 9.0.3 — version and compatibility verification
- spaCy docs (spacy.io/usage) — model download requirement, version pinning, pipeline component disabling
- Streamlit docs — caching architecture, st.cache_data vs st.cache_resource, AppTest testing API
- pandas whatsnew v3.0.0 — Copy-on-Write default, Python 3.11 minimum
- extruct GitHub issues #45, #87, #109, #112 — JSON-LD malformed input failure modes
- spaCy GitHub issues #2508, #2817 — max_length ValueError
- CPython Issue #116740 — urllib.robotparser RFC 9309 non-compliance

### Secondary (MEDIUM confidence)
- LLM Pulse, Am I Citable, AgentSpeed, Glippy, Pixelmojo, Cloudflare Agent Readiness — competitor feature analysis
- GoVisible: Role of Schema Markup in GEO — FAQPage citation rate (3.2x figure)
- Frase: FAQ Schema for AI Search — FAQ schema citation research
- ScrapeOps: Web Scraping Part 5 — User-Agent and header best practices
- datawookie: Accelerating BeautifulSoup Encoding Detection — cchardet recommendation

### Tertiary (LOW confidence)
- Rankability: Best AI SEO Content Optimization Tools — landscape overview; used for competitive positioning only

---
*Research completed: 2026-05-02*
*Ready for roadmap: yes*
