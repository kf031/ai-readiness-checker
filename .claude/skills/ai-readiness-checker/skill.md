---
name: ai-readiness-checker
description: >
  Check if a website is visible to AI search engines (ChatGPT, Perplexity, Claude,
  Google AI Overviews). Analyzes robots.txt, llms.txt, structured data, and content
  quality. Gives a 0-100 score with letter grade and actionable recommendations.
  Use when the user mentions "check my site", "SEO", "AI search", "AI-ready",
  "is my site visible to AI", "ai readiness", "site score", "check website",
  "analyze my site", "will AI find my site", "improve site for AI",
  "make my site AI friendly", or any URL they want analyzed.
  Also triggers for "vibe coding" check — when someone building a website
  wants to verify AI crawlers can see it.
---

# AI Readiness Checker

You score any website's visibility to AI search engines (ChatGPT, Perplexity, Claude, Google AI Overviews). You run the local `checker` CLI tool to do the analysis.

## When to Use

A user might say:
- "Check https://mysite.com for AI readiness"
- "Is my site visible to AI search?"
- "I just built a website — will ChatGPT see it?"
- "Score my site"
- "How do I make my site AI-friendly?"

If a URL is mentioned and the intent is analysis/fixing, use this skill.

## Workflow

### 1. Quick Check (default)

Run the CLI and present results:

```bash
python -m checker <url>
```

The output shows:
- Overall score (0-100) with letter grade (A-F)
- Per-module score bars (robots.txt, llms.txt, schema, content)
- Prioritized recommendations

Summarize the score and most important recommendation for the user.

### 2. Fix Mode (when user wants improvements)

If the user asks to fix issues, run:

```bash
python -m checker <url> --fix
```

This generates an improved version of their page. Explain what skills were invoked and what changed.

If the user has an LLM backend available:

```bash
python -m checker <url> --fix --llm-backend openai
```

(Also supports `ollama` and `anthropic`)

### 3. Batch Mode (multiple URLs)

```bash
python -m checker --batch urls.csv -o results.csv
```

### 4. Export Mode

```bash
python -m checker <url> -o report.json
```

## Understanding Results

- **Score 85-100 (A):** Excellent — AI crawlers can fully see and understand this site
- **Score 70-84 (B):** Good — mostly visible, minor issues to fix
- **Score 55-69 (C):** Okay — some significant gaps for AI crawlers
- **Score 40-54 (D):** Poor — AI crawlers are missing key information
- **Score 0-39 (F):** Critical — AI crawlers cannot effectively access this site

## Four Signals Explained

| Signal | What it checks | Weight |
|--------|---------------|--------|
| robots.txt | Are AI bots (GPTBot, ClaudeBot, PerplexityBot, etc.) allowed to crawl? | 20% |
| llms.txt | Is there a machine-readable content summary for LLMs? | 15% |
| Schema | Is there structured data (JSON-LD, microdata) for products, FAQs, articles? | 30% |
| Content | Is the text readable, well-structured, with good heading hierarchy and Q&A density? | 35% |

## Common Fixes

When recommendations come back, explain what they mean:
- "GPTBot is blocked" → AI can't see the page at all — add `User-agent: GPTBot` with `Allow: /` to robots.txt
- "No llms.txt found" → Create an llms.txt file summarizing key pages for LLMs
- "Missing FAQPage schema" → Add JSON-LD structured data for Q&A content
- "Multiple H1s" → Use exactly one `<h1>` per page for the main title
- "Low Q&A density" → Add FAQ sections — AI search engines love Q&A format

## Important

- Always run `python -m checker` from the project root directory
- The tool is already installed and configured in this project
- Results are in plain text — summarize them conversationally for the user
- If the user is vibe coding, suggest running the check after they have a deployed URL
