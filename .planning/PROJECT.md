# AI Readiness Checker

## What This Is

An open-source Python tool that crawls any website and produces an **AI Readiness Score** — telling website owners how visible and citable their site is to AI search engines like ChatGPT, Perplexity, Claude, and Google AI Overviews. Targeted at e-commerce stores and AI-related businesses. Distributed as an open-source GitHub repo with a Streamlit demo app anyone can run.

## Core Value

A single URL input returns a clear, scored, actionable report showing exactly why a site is or isn't being picked up by AI search engines — and what to fix.

## Current Milestone: v1.0 Initial Release

**Goal:** Ship an open-source Python tool that scores any website's AI search engine visibility with both CLI and Streamlit UI.

**Target features:**
- URL crawler with realistic headers and graceful error handling
- robots.txt AI bot access analysis (7 bots)
- llms.txt detection with content preview
- Structured data extraction and scoring (6 schema types)
- NLP content quality analysis (readability, entities, headings, Q&A density)
- Weighted composite scoring (0-100) with A-F grade
- Prioritized plain-English recommendations
- CLI entry point (`python -m checker`) with rich output
- Streamlit dashboard with interactive results
- pytest test suite

## Requirements

### Validated

- [x] Fetch page HTML with realistic headers, redirect handling, and graceful error handling (Phase 1)
- [x] Analyze robots.txt for AI bot access (GPTBot, ClaudeBot, PerplexityBot, CCBot, Google-Extended, Applebot-Extended, Amazonbot) (Phase 2)
- [x] Check for llms.txt and llms-full.txt files with content preview (Phase 2)
- [x] Extract and score structured data (JSON-LD, microdata, schema.org types: Product, FAQPage, Organization, BreadcrumbList, Article, Review) (Phase 3)
- [x] Analyze content quality via NLP: readability (textstat), content-to-HTML ratio, Q&A density, entity clarity (spaCy), word count, heading structure (Phase 4)
- [x] Combine all module scores into a weighted final score (robots 20%, llms.txt 15%, schema 30%, content 35%) with A–F grade (Phase 5)
- [x] Generate prioritized, human-readable recommendations for each failing area (Phase 5)

### Active

- [x] CLI entry point: `python -m checker <url>` with rich-formatted score card (Phase 6)
- [x] Streamlit dashboard: URL input → spinner → overall score gauge → grade badge → per-module expandable sections → recommendations list (Phase 7)
- [x] LLM Advisor Agent: 7 fix skills (schema, headings, readability, QA, llms.txt, preview, explain) with `--fix` CLI flag and "Improve My Site" button in Streamlit (v2)
- [x] MCP Server: `checker_analyze` and `checker_fix` tools for MCP-compatible LLMs via `--mcp` flag (v2)
- [ ] Standalone LLM backends: Ollama (Llama 3.2 3B), Anthropic API, OpenAI API — abstracted behind LLMBackend interface (v3)
- [ ] JSON export: `--output report.json` flag for machine-readable output (v3)
- [ ] Batch CSV analysis: `python -m checker --batch urls.csv` (v3)

### Out of Scope

- Browser extension — future v3
- Weekly monitoring / email alerts — future v3
- Dataset publishing on HuggingFace — future v3
- Authentication or user accounts — not needed for open-source tool

## Context

- The user has a detailed module-by-module implementation plan already written (CLAUDE.md in the project documents folder)
- Build order from the plan: crawler → robots → llms.txt → schema → content → scorer/report → CLI → Streamlit → tests → notebook
- Python 3.10+ project using: requests, BeautifulSoup4, spaCy (en_core_web_sm), textstat, extruct, streamlit, pandas, rich, pytest
- The project is exploratory — user wants to build it fully first, then decide on deployment and next steps
- No strict deadline; goal is to ship a working v1 that can be shown as a portfolio piece or grown further
- **v2 direction**: LLM Advisor Agent — a skill-calling agent that invokes modular fix skills (schema, headings, readability, Q&A) to generate improved HTML + visual before/after preview. Initial backend is Claude Code skills, standalone LLM backends in v3.
- **v3 direction**: Distribution & scale — JSON export, batch CSV, FastAPI, browser extension, monitoring, standalone LLM backends (Ollama, Anthropic, OpenAI)

## Constraints

- **Tech Stack**: Python 3.10+, libraries as specified in requirements.txt — no substitutions for v1
- **Scope**: v1 is exactly the 9 modules listed in the plan; no new features until v1 is complete
- **NLP Model**: spaCy en_core_web_sm (small model) — fast enough for single-URL analysis, no GPU required

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| spaCy en_core_web_sm (not md/lg) | Lightweight, no GPU needed, sufficient for entity detection on single pages | — Pending |
| extruct for structured data extraction | Handles JSON-LD, microdata, and RDFa in one pass | — Pending |
| Streamlit for demo UI | Easiest Python-native way to ship a shareable web demo with no backend work | — Pending |
| Weighted scoring (content 35%, schema 30%) | Content quality and structured data are highest signal for AI citability | — Pending |
| LLM Agent in v2, distribution in v3 | Lead with standout feature (AI-generated fixes + visual preview) before building infrastructure. Claude Code skills as first backend avoids LLM SDK deps in v2. | v2 complete — 7 fix skills, agent loop, MCP server, Streamlit integration. v3 standalone backends pending. |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-17 — V2 complete (LLM Advisor Agent + MCP server + Streamlit integration), 188 tests passing*
