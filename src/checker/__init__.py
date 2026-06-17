"""
AI Readiness Checker — scores any website's AI search engine visibility.

Phase 1: FetchResult, CrawlError (data contracts + crawler)
Phase 2: RobotsResult, BotStatus, LlmsResult, fetch_access_signals (access signals)
Phase 3: SchemaAnalysis, analyze_schema (schema extraction)
Phase 4: ContentAnalysis, analyze_content (content analysis)
"""

# Phase 1 exports
from checker.contracts import CrawlError, FetchResult

# Phase 2 exports — data contracts
from checker.contracts import BotStatus, LlmsResult, RobotsResult

# Phase 2 exports — high-level API
from checker.access_fetcher import fetch_access_signals

# Phase 3 exports — data contracts
from checker.contracts import SchemaAnalysis

# Phase 4 exports — data contracts
from checker.contracts import ContentAnalysis

# Phase 3 exports — high-level API
from checker.schema_analyzer import analyze_schema

# Phase 4 exports — high-level API
from checker.content_analyzer import analyze_content

# Phase 5 exports — data contracts
from checker.contracts import ScoreReport

# Phase 5 exports — high-level API
from checker.scorer import generate_report

# Phase 6 exports — pipeline orchestrator
from checker.orchestrator import run_pipeline

# V2 exports — LLM Advisor Agent
from checker.contracts import AgentOutput, SkillResult
from checker.agent import run_llm_agent, decide_skills, build_agent_report

__all__ = [
    "AgentOutput",
    "BotStatus",
    "ContentAnalysis",
    "CrawlError",
    "FetchResult",
    "LlmsResult",
    "RobotsResult",
    "SchemaAnalysis",
    "ScoreReport",
    "SkillResult",
    "analyze_content",
    "analyze_schema",
    "build_agent_report",
    "decide_skills",
    "fetch_access_signals",
    "generate_report",
    "run_llm_agent",
    "run_pipeline",
]
