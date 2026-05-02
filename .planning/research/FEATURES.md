# Feature Research

**Domain:** AI readiness / GEO (Generative Engine Optimization) website analyzer, open-source Python tool
**Researched:** 2026-05-02
**Confidence:** HIGH for table stakes (well-established across 6+ comparable tools); MEDIUM for differentiators (limited open-source comparable tools to benchmark against)

---

## Competitive Landscape

Tools checked before writing this document:

| Tool | robots.txt | llms.txt | Schema | NLP/Content | Score | Open Source? |
|------|-----------|----------|--------|-------------|-------|--------------|
| LLM Pulse (llmpulse.ai) | Yes, 7+ bots | No | No | No | Yes (single) | No |
| Am I Citable (amicitable.com) | Yes | Yes | Yes (FAQ, structure data) | Yes (heading, meta) | Yes (0-100, A-F) | No |
| AgentSpeed (agentspeed.dev) | Yes, 16 bots | Yes | Yes | No (CAPTCHA, JS, TTFB focus) | Yes (0-100) | No |
| Glippy (glippy.dev) | Yes | Yes | Yes | Yes (entity, citability) | Yes (0-100, letter grade) | No |
| Pixelmojo (pixelmojo.io) | Yes | Yes (validator) | Yes (JSON-LD, Org/Article) | Yes | Yes (0-100, radar) | No |
| Cloudflare Agent Readiness | Yes | No | No | No (API/MCP focus) | Yes | No |
| ai-seo-auditor (github.com/ngstcf) | No | Yes | Yes (JSON-LD) | Yes (lists, FAQ, headings) | No | Yes (Python, LLM-dependent) |
| **This tool (planned)** | Yes, 7 bots | Yes | Yes (6 types) | Yes (spaCy, textstat) | Yes (A-F) | Yes (Python, no LLM needed) |

**Key gap identified:** No existing open-source Python tool runs full robots.txt + llms.txt + schema + NLP content analysis without requiring an LLM API key. This tool's main differentiator is a complete, self-contained pipeline with no paid API dependencies.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features every AI readiness tool has. Missing any of these means users will dismiss the tool as incomplete before using it.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| robots.txt parsing for AI bots | Every competitor checks this; it is the first question users ask ("am I blocking ChatGPT?") | LOW | GPTBot, ClaudeBot, PerplexityBot, CCBot, Google-Extended, Applebot-Extended, Amazonbot — all confirmed present in 3+ competing tools |
| llms.txt presence check | Became standard expectation in 2025; 5 of 7 competing tools check for it | LOW | Check root domain for `/llms.txt` and `/llms-full.txt`; preview content if present |
| Structured data detection (JSON-LD) | Schema markup is cited as the highest-signal GEO factor across all research; 6 of 7 tools check it | MEDIUM | extruct handles JSON-LD, microdata, RDFa in one pass |
| A–F letter grade or 0-100 score | All comparable tools produce a score; users need a single number to act on | LOW | Already designed: weighted final score with A-F grade |
| Per-module breakdown | Every tool breaks down the overall score into sub-scores; users need to know where to fix | LOW | Already designed as expandable sections in Streamlit |
| Actionable recommendations | All serious tools generate specific, prioritized fixes — not just "schema missing" but "add FAQPage schema" | MEDIUM | Already in spec; hardest part is good copy |
| URL input → instant results | Table stakes UX — no signup, no account, just enter URL | LOW | Already designed as Streamlit input → spinner → results |
| Graceful error handling for failed fetches | Users will enter URLs that redirect, timeout, or return 403; tool must explain what went wrong | LOW-MEDIUM | Already in spec (redirect handling, error handling) |

### Differentiators (Competitive Advantage)

Features this tool has or can have that distinguish it from existing options.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Open-source, no LLM API key required | Every comparable Python open-source tool (ai-seo-auditor) requires OpenAI or Anthropic key; this tool uses spaCy + textstat locally | LOW (already decided) | This is the primary portfolio differentiator — reproducible, auditable, free to run |
| spaCy entity clarity scoring | No competing web tool exposes named-entity analysis as a distinct score signal; AgentSpeed and Glippy mention "entity authority" but don't expose it | HIGH (NLP pipeline) | Uses en_core_web_sm — fast, no GPU; detects entity types, density, ambiguity |
| Q&A density as an explicit score signal | FAQ schema gets checked by 4 tools, but actual Q&A density in body text (not just schema) is not measured by any reviewed tool | MEDIUM | Counts interrogative sentences and co-located answers in HTML; directly maps to AI citation likelihood (FAQPage schema citation rate 3.2x per research) |
| Content-to-HTML ratio | Flagged by LLM Clicks as "token-efficient content structuring" but not quantified as a score component by any reviewed tool | LOW-MEDIUM | Ratio of extractable text to raw HTML byte size; low ratio = noise that wastes AI tokens |
| CLI-first workflow (`python -m checker <url>`) | All reviewed web tools are browser-only; none offer a programmatic CLI for developers and CI/CD pipelines | LOW (already in spec) | Strong differentiator for the technical/developer audience |
| Weighted scoring transparency | Competing tools show category scores but rarely explain the weights; this tool's 20/15/30/35 weighting is documented and adjustable | LOW | Publish the weighting rationale — credibility signal for open-source audience |
| Readable score card via `rich` terminal output | No competing tool has a terminal report; all are web UIs | LOW | Portfolio-friendly: easy to screenshot for README |
| Schema type specificity (6 types scored separately) | Competing tools confirm "schema present/absent"; none break down which of the 6 key schema types (Product, FAQPage, Org, BreadcrumbList, Article, Review) are present vs missing | MEDIUM | Directly tells e-commerce owners which schema types they're missing |

### Anti-Features (Deliberately Not in v1)

| Feature | Why Requested | Why Problematic in v1 | Alternative |
|---------|---------------|-----------------------|-------------|
| LLM-powered content scoring | Users expect AI tools to use AI internally; ai-seo-auditor, sethblack/python-seo-analyzer both added LLM calls | Requires paid API key, kills reproducibility, adds latency, breaks offline use — and is unnecessary when textstat + spaCy cover the same signals without it | spaCy + textstat give objective, deterministic NLP scores without API cost |
| Batch / CSV URL upload | Obvious v2 feature users will immediately request | Adds state management, progress tracking, and report storage complexity that derails v1 | Explicitly documented as v2 in PROJECT.md; reply to requests with the roadmap |
| Real-time monitoring / alerts | "Tell me when my score changes" — every monitoring SaaS offers this | Requires persistent storage, scheduler, email/webhook infra — weeks of backend work | V2 feature; v1 is a single-shot analyzer |
| Competitor comparison | "How does my site compare to example.com?" — Glippy and Semrush offer this | Multi-URL analysis doubles crawl complexity; comparison framing dilutes the core value of "fix your site" | Add post-v1 once single-URL report is solid |
| Browser extension | High-visibility distribution channel | Requires Chrome/Firefox packaging, CSP handling, and update cadence unrelated to the core tool | V2 after validating demand via Streamlit demo |
| API / FastAPI wrapper | Developers want to integrate this into pipelines | Needs auth, rate limiting, hosting, versioning — full backend project | Already in PROJECT.md as v2; Streamlit demo is sufficient proof of concept |
| PageSpeed / Core Web Vitals | Expected in "complete" site audits | Requires Lighthouse or PageSpeed Insights API; out of the AI readiness scope; competing tools that include it (Dashform, AgentSpeed) end up unfocused | Out of scope — this tool is specifically AI citability, not general web performance |
| Sitemap.xml analysis | AgentSpeed and Cloudflare check this | Adds crawling scope creep; sitemap health does not directly map to AI citability signals | Can be added as a single LOW-effort check in v1.1 if users ask |

---

## Feature Dependencies

```
robots.txt analysis
    └──requires──> HTML fetch / crawler module

llms.txt check
    └──requires──> HTML fetch / crawler module (domain-level fetch)

Schema detection (extruct)
    └──requires──> HTML fetch / crawler module
    └──enhances──> Structured data score module

Content NLP (spaCy + textstat)
    └──requires──> HTML fetch / crawler module
    └──requires──> BeautifulSoup4 (clean text extraction)
    └──enhances──> Content quality score module

Score aggregation (A-F grade)
    └──requires──> robots module score
    └──requires──> llms.txt module score
    └──requires──> schema module score
    └──requires──> content module score

CLI report (rich)
    └──requires──> score aggregation

Streamlit dashboard
    └──requires──> score aggregation
    └──enhances──> CLI report (same data, different presentation)

Recommendations engine
    └──requires──> per-module scores
    └──enhances──> CLI report + Streamlit dashboard
```

### Dependency Notes

- **Crawler is the root dependency:** All four analysis modules require a working HTTP fetch with redirect handling. This must be built and tested first.
- **Score aggregation requires all four modules:** The final grade is meaningless until robots, llms.txt, schema, and content modules all produce numeric sub-scores.
- **CLI and Streamlit share the same data layer:** Both consume the score aggregation output. CLI should be built first — it is simpler and enables testing without a UI.

---

## MVP Definition

### Launch With (v1)

- [x] Crawler with realistic headers, redirect handling, error handling — all downstream modules depend on it
- [x] robots.txt AI bot analysis (7 bots) — table stakes; most visible feature
- [x] llms.txt presence and preview — rapidly becoming table stakes; differentiates from robots-only tools
- [x] Schema detection and scoring (6 JSON-LD types) — highest-weight signal (30%) and clearest action item for e-commerce users
- [x] Content NLP scoring (readability, Q&A density, entity clarity, content-to-HTML ratio, heading structure) — highest-weight signal (35%); only open-source tool to do this without an LLM API
- [x] Weighted final score + A-F grade — required for users to understand overall state
- [x] Prioritized recommendations per module — without this, the score is just a number
- [x] CLI entry point (`python -m checker <url>`) — developer credibility; enables README screenshots
- [x] Streamlit dashboard — shareable demo; validates tool with non-technical users

### Add After Validation (v1.x)

- [ ] Sitemap.xml presence check — low effort, frequently requested, minor signal; add if users ask
- [ ] Additional schema types (HowTo, VideoObject, SpeakableSpecification) — extend schema module once 6 core types are solid
- [ ] robots.txt snippet export ("copy-paste fix") — high-value recommendation upgrade; add once recommendation format is validated

### Future Consideration (v2+)

- [ ] Batch / CSV URL upload — wait for evidence that users want this at scale
- [ ] FastAPI wrapper — wait until Streamlit demo proves demand for programmatic access
- [ ] Weekly monitoring / email alerts — requires backend; only worth building if retention metrics show users returning
- [ ] Browser extension — only after Streamlit demo shows strong organic discovery
- [ ] HuggingFace dataset export — publish scored URL dataset; value depends on volume

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| robots.txt AI bot analysis | HIGH | LOW | P1 |
| llms.txt check + preview | HIGH | LOW | P1 |
| Schema detection (6 types) | HIGH | MEDIUM | P1 |
| Content NLP (spaCy + textstat) | HIGH | HIGH | P1 |
| Weighted score + A-F grade | HIGH | LOW | P1 |
| Actionable recommendations | HIGH | MEDIUM | P1 |
| CLI report (rich) | MEDIUM | LOW | P1 |
| Streamlit dashboard | HIGH | MEDIUM | P1 |
| Sitemap.xml check | LOW | LOW | P2 |
| Additional schema types | MEDIUM | LOW | P2 |
| robots.txt fix snippets | MEDIUM | LOW | P2 |
| Batch URL upload | MEDIUM | HIGH | P3 |
| FastAPI wrapper | MEDIUM | HIGH | P3 |
| Monitoring / alerts | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Add after v1 is validated
- P3: Defer to v2+

---

## Competitor Feature Analysis

| Feature | Am I Citable | AgentSpeed | Glippy | Pixelmojo | This Tool |
|---------|-------------|------------|--------|-----------|-----------|
| robots.txt (AI bots) | Yes | Yes (16 bots) | Yes | Yes | Yes (7 bots) |
| llms.txt check | Yes | Yes | Yes | Yes (+ validator) | Yes (+ preview) |
| Schema / structured data | Yes (FAQ, OpenGraph) | Yes (quality check) | Yes (240+ checks) | Yes (JSON-LD types) | Yes (6 specific JSON-LD types) |
| NLP content quality | Partial (headings, meta) | No | Yes (entity, citability) | Partial | Yes (spaCy, textstat, Q&A density) |
| A-F grade | Yes | No (0-100 + color) | Yes | Yes | Yes |
| Per-module breakdown | Yes | Yes (2 tiers) | Yes (16 categories) | Yes (radar chart) | Yes (4 modules, expandable) |
| Actionable recommendations | Yes | Yes (agent prompts) | Yes | Yes | Yes (prioritized) |
| CLI / programmatic access | No | No | No | No | Yes (`python -m checker`) |
| Open source | No | No | No | No | Yes |
| No LLM API key required | Yes | Yes | Yes | Yes | Yes |
| Q&A density (body text) | No | No | No | No | Yes |
| Content-to-HTML ratio | No | No | No | No | Yes |
| spaCy entity clarity | No | No | No | No | Yes |

---

## Sources

- [LLM Pulse AI Crawlability Checker](https://llmpulse.ai/robots-txt-checker) — robots.txt bot coverage
- [Am I Citable — AI Search Readiness Scanner](https://amicitable.com/) — scoring categories and weights
- [AgentSpeed Blog — How We Calculate Your Score](https://agentspeed.dev/blog/how-we-calculate-your-score) — tier structure, agent killers concept
- [Glippy AI Readiness Checker](https://www.glippy.dev/tools/ai-readiness-checker) — 240+ checks, 16 GEO categories
- [Pixelmojo AI Readiness Score](https://www.pixelmojo.io/tools/ai-readiness-score) — radar visualization, 5-category scoring
- [Cloudflare Agent Readiness](https://blog.cloudflare.com/agent-readiness/) — API/MCP-focused checks, agentic commerce
- [GitHub: ngstcf/ai-seo-auditor](https://github.com/ngstcf/ai-seo-auditor) — Python open-source LLM-dependent competitor
- [GoVisible: Role of Schema Markup in GEO](https://govisible.ai/blog/the-role-of-schema-markup-in-generative-engine-optimization/) — FAQPage citation rate (3.2x), GPT-4 performance with structured data
- [Frase: FAQ Schema for AI Search](https://www.frase.io/blog/faq-schema-ai-search-geo-aeo) — FAQ schema citation research
- [Rankability: Best AI SEO Content Optimization Tools](https://www.rankability.com/blog/best-seo-content-optimization-tools/) — content optimization tool landscape

---
*Feature research for: AI readiness checker (open-source Python)*
*Researched: 2026-05-02*
