# Contributing

Thanks for wanting to help. Here's how.

## Setup

```bash
git clone https://github.com/kf031/ai-readiness-checker.git
cd ai-readiness-checker
pip install -e ".[dev]"
python -m spacy download en_core_web_sm
```

## Running tests

```bash
pytest                    # all 208 tests
pytest tests/test_robots.py   # specific module
pytest -x                 # stop on first failure
```

Tests use mocked HTTP calls — no network needed.

## How things fit together

```
src/checker/
├── contracts.py          # All data contracts (FetchResult, ScoreReport, etc.)
├── orchestrator.py       # run_pipeline() — wires everything together
├── crawler.py            # Fetches page HTML
├── robots_txt.py         # Parses robots.txt for 7 AI bots
├── llms_txt.py           # Validates llms.txt format
├── schema_analyzer.py    # Extracts structured data via extruct
├── content_analyzer.py   # NLP analysis via spaCy + textstat
├── scorer.py             # Weighted scoring + recommendations
├── agent.py              # V2 agent: decides which fix skills to run
├── skills/               # 7 fix skill modules
├── llm_backends.py       # Ollama, OpenAI, Anthropic backends
├── cli_renderer.py       # Rich terminal output
├── __main__.py           # CLI entry point (checker command)
├── api_server.py         # FastAPI server
└── mcp_server.py         # MCP server for Claude Code / Cursor
```

## Making changes

1. Fork the repo
2. Create a branch: `git checkout -b fix-thing`
3. Write tests for your change
4. Make the change
5. Run `pytest` — all tests must pass
6. Open a PR

## What to work on

Check the [issues](https://github.com/kf031/ai-readiness-checker/issues) or look for `TODO` comments in the code. Good first issues involve:

- Adding new bot tokens to robots.txt checking
- Improving the template-based fix skills
- Adding more schema types to TARGET_TYPES
- Better error messages for edge cases

## License

MIT. Your contributions will be under the same license.
