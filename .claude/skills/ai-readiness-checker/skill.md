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

You score any website's visibility to AI search engines. You run the local `checker` CLI tool, then cross-reference every finding with complementary skills the user could use to fix the problem.

## When to Use

- "Check https://mysite.com for AI readiness"
- "Is my site visible to AI search?"
- "I just built a website — will ChatGPT see it?"
- "Score my site"
- "How do I make my site AI-friendly?"

## Workflow

### Step 1: Run the checker

```bash
python -m checker <url>
```

Parse the output. Note every recommendation, the grade, and per-module scores.

### Step 2: Present results + Meta-Skill Routing

For each failing module, map the finding to skills that can fix it. **This is the core value add — don't just report problems, route to solutions.**

Present results conversationally:

```
## AI Readiness Score: 62/100 (C)

Here's what's holding your site back and which skills fix each problem:

1. **No llms.txt found** (15% of score)
   → Your built-in `fix-llms-txt` skill handles this. Run `checker <url> --fix`.

2. **Missing FAQPage schema** (30% of score)
   → Your built-in `fix-schema` skill handles this.

3. **Low content readability** (35% of score)
   → **Cross-skill route:** The `taste` skill can rewrite your copy for clarity.
   If you don't have it: `claude plugins install taste`
   Also try: `/uiux-promax` for layout improvements that affect readability.

4. **Duplicate H1 tags, weak heading hierarchy**
   → **Cross-skill route:** The `uiux-promax` skill can audit your page structure.
   Also try: `max-ui` for heading/typography improvements.
```

Always check whether the user HAS the recommended skill. If they don't, say:

> "The `taste` skill would be perfect for fixing your readability issues, but you don't have it installed yet. Try `claude plugins install taste` or ask me to `/taste` your page copy."

### Step 3: Offer to fix in-place

If the user wants fixes NOW, use the built-in skills:

```bash
python -m checker <url> --fix                    # template-based (fast, free)
python -m checker <url> --fix --llm-backend openai  # AI-powered (smarter)
```

Then route remaining issues (design, tone, layout) to the complementary skills.

## Meta-Skill Registry

This is the mapping from checker findings to complementary skills. Update this as new skills emerge.

| Checker Finding | Primary Route | Secondary Route | What It Does |
|-----------------|---------------|-----------------|--------------|
| Low readability score | `taste` skill | `copywriter` skill | Rewrites content for clarity and grade level |
| Poor heading structure | `uiux-promax` | `max-ui` | Fixes typography, hierarchy, visual weight |
| Missing schema / structured data | Built-in `fix-schema` | — | Generates JSON-LD blocks |
| Missing llms.txt | Built-in `fix-llms-txt` | — | Generates llms.txt from page content |
| Low Q&A density | Built-in `fix-qa` | `taste` skill | Generates FAQ content, improves answer quality |
| Duplicate H1 / hierarchy violations | Built-in `fix-headings` | `uiux-promax` | Merges headings, fixes outline |
| Low text-to-HTML ratio | `max-ui` | `uiux-promax` | Reduces HTML bloat, improves content density |
| No entities detected (ORG, PRODUCT) | `taste` skill | — | Adds brand/product/org mentions naturally |
| Overall poor design | `uiux-promax` | `max-ui` | Full-page visual and structural audit |
| Thin SPA shell / JS-only | `n8n-*` skills | — | Suggests pre-rendering or SSR workflow |
| Robots.txt blocks AI crawlers | Built-in CLI explainer | — | Shows exact robots.txt fix needed |

## Skill Detection

Before recommending a skill, check if the user has it:

```bash
# Check installed skills
ls .claude/skills/ 2>/dev/null
```

If a recommended skill is missing, suggest installation. Don't force it — just say "this would help, here's how to get it."

## Discovery Phrases

When routing to other skills, use natural language:

- "The `taste` skill would nail this — it rewrites copy to match your brand voice while improving readability."
- "This page would benefit from a `uiux-promax` audit. It checks layout, heading hierarchy, and visual flow."
- "Your built-in `fix-schema` handles this. Want me to generate the missing JSON-LD right now?"

## Built-in Skills (always available)

These skills ship with the checker and require no install:

- `fix-schema` — Generates missing structured data
- `fix-headings` — Fixes heading hierarchy
- `fix-readability` — Detects/rewrites dense paragraphs
- `fix-qa` — Generates Q&A sections
- `fix-llms-txt` — Generates llms.txt

## Important

- Always run `python -m checker` from the project root
- Cross-reference EVERY failing finding with the meta-skill registry
- If a recommended skill is missing, mention how to install it **once**, then move on
- Results are plain text — summarize conversationally
