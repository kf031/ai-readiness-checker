"""MCP server exposing checker tools for any MCP-compatible LLM.

Start with: python -m checker --mcp
Or directly: python -m src.checker.mcp_server

Exposes two tools:
    - checker_analyze: Run full AI readiness analysis on a URL
    - checker_fix: Analyze + generate AI-improved HTML with fix skills
"""

import json

from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationCapabilities
from mcp.server.stdio import stdio_server
import mcp.types as types

from src.checker.orchestrator import run_pipeline
from src.checker.contracts import CrawlError
from src.checker.agent import build_agent_report, run_llm_agent

server = Server("checker")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="checker_analyze",
            description=(
                "Analyze any website URL for AI search engine readiness. "
                "Returns a scored report (0-100) with per-module breakdowns "
                "for robots.txt, llms.txt, structured data, and content quality."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The website URL to analyze (e.g., https://example.com)",
                    }
                },
                "required": ["url"],
            },
        ),
        types.Tool(
            name="checker_fix",
            description=(
                "Analyze a URL AND generate an AI-improved version of the page "
                "with better headings, structured data, readability, and Q&A sections. "
                "Returns improved HTML, a before/after visual diff, and plain-English "
                "explanation of all changes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The website URL to analyze and fix (e.g., https://example.com)",
                    }
                },
                "required": ["url"],
            },
        ),
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    url = arguments["url"]
    try:
        if name == "checker_analyze":
            pipeline_result = run_pipeline(url)
            report = build_agent_report(pipeline_result)
            result = {
                "url": report["url"],
                "overall_score": report["overall_score"],
                "grade": report["grade"],
                "modules": {
                    k: {"score": v["score"]} for k, v in report["modules"].items()
                },
                "errors": pipeline_result.get("errors", []),
                "complete": pipeline_result.get("complete", False),
            }
        elif name == "checker_fix":
            pipeline_result = run_pipeline(url)
            report = build_agent_report(pipeline_result)

            fetch_result = pipeline_result.get("fetch_result")
            if fetch_result is None or isinstance(fetch_result, CrawlError):
                html = "<html><body></body></html>"
            else:
                html = getattr(fetch_result, "html", "<html><body></body></html>")

            output = run_llm_agent(report, html)
            result = {
                "url": url,
                "skills_called": output.skills_called,
                "changes": output.changes,
                "explanation": output.explanation,
            }
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    except Exception as e:
        return [
            types.TextContent(
                type="text",
                text=json.dumps({"error": str(e)}, indent=2),
            )
        ]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationCapabilities(
                sampling={},
                experimental={},
                notifications=NotificationOptions(),
            ),
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
