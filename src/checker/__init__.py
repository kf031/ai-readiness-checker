"""
AI Readiness Checker — scores any website's AI search engine visibility.

Phase 1: FetchResult, CrawlError (data contracts + crawler)
Phase 2: RobotsResult, BotStatus, LlmsResult, fetch_access_signals (access signals)
"""

# Phase 1 exports
from src.checker.contracts import CrawlError, FetchResult

# Phase 2 exports — data contracts
from src.checker.contracts import BotStatus, LlmsResult, RobotsResult

# Phase 2 exports — high-level API
from src.checker.access_fetcher import fetch_access_signals

__all__ = [
    "FetchResult",
    "CrawlError",
    "RobotsResult",
    "BotStatus",
    "LlmsResult",
    "fetch_access_signals",
]
