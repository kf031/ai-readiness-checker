"""
Data contracts for the AI Readiness Checker.

This module is the single source of truth for all inter-module communication shapes.
Every downstream module imports its input/output contracts from here.

Phase 1: FetchResult, CrawlError
Phase 2: RobotsResult, BotStatus, LlmsResult
Phase 3: SchemaAnalysis
Phase 4: ContentAnalysis
Phase 5: (future) ScoreReport
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from bs4 import BeautifulSoup


@dataclass
class CrawlError:
    """Structured error result when a crawl fails.

    Downstream modules receive this instead of catching exceptions.
    """

    url: str
    error_type: str
    # Valid error_type values:
    #   'invalid_url'        — URL malformed or non-http(s) scheme
    #   'ssrf_blocked'        — URL targets localhost/private/internal network
    #   'connection_error'    — DNS failure, connection refused, network unreachable
    #   'timeout'             — Request exceeded timeout (default 10s)
    #   'http_error'          — Server returned 4xx or 5xx status
    #   'too_many_redirects'  — Redirect chain exceeded requests' limit (30)
    #   'request_error'       — Catch-all for other requests exceptions
    #   'response_too_large'  — Response body exceeded MAX_RESPONSE_SIZE
    status_code: Optional[int] = None
    message: str = ""
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class FetchResult:
    """Successful crawl result with parsed HTML.

    This is the root input contract for all four analysis modules
    (robots.txt, llms.txt, schema, content).
    """

    url: str  # Original requested URL
    final_url: str  # URL after all redirects resolved
    status_code: int  # HTTP status code (should be 2xx)
    html: str  # Raw HTML text (for serialization, report generation)
    soup: BeautifulSoup  # Pre-parsed BS4 tree (lxml parser) — cached to avoid re-parsing
    fetched_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

@dataclass
class BotStatus:
    """Per-bot access status extracted from robots.txt."""

    bot_name: str  # e.g., "GPTBot"
    status: str  # "allowed" | "blocked" | "not_mentioned"
    rule_line: Optional[str] = None  # The Allow/Disallow line that determined status
    explicitly_mentioned: bool = False  # True if bot token appeared in a User-agent line


@dataclass
class RobotsResult:
    """Complete robots.txt analysis result.

    Consumed by Phase 5 scorer for the robots component (20% weight).
    """

    url: str  # The URL whose robots.txt was analyzed
    exists: bool  # robots.txt was fetched successfully (200 OK)
    status_code: Optional[int] = None  # HTTP status from fetch
    fetch_error: Optional[str] = None  # Error type if fetch failed (None if success)
    bots: list[BotStatus] = field(default_factory=list)  # Per-bot breakdown (always 7 items)
    raw_text: Optional[str] = None  # Raw robots.txt content (None if fetch failed)
    fetched_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class LlmsResult:
    """Complete llms.txt analysis result.

    Consumed by Phase 5 scorer for the llms.txt component (15% weight).
    """

    url: str  # The URL whose llms.txt was analyzed
    found: bool  # llms.txt returned 200 OK
    status_code: Optional[int] = None  # HTTP status from fetch
    fetch_error: Optional[str] = None  # Error type if fetch failed (None if success)
    valid: Optional[bool] = None  # Format validity per spec (None if not found)
    validation_errors: list[str] = field(default_factory=list)  # Format violations
    content_preview: Optional[str] = None  # First 500 chars if found (None if not)
    raw_text: Optional[str] = None  # Full llms.txt content (None if not found)
    fetched_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class SchemaAnalysis:
    """Complete schema extraction analysis result.

    Consumed by Phase 5 scorer for the schema component (30% weight).

    Fields:
        url: The URL whose HTML was analyzed
        raw: Format-name keys to lists of extracted structured data items.
             Keys: "json-ld", "microdata", "opengraph", "rdfa"
        detected_types: Set of concrete schema.org type names found
            (e.g., {"Product", "FAQPage", "Organization", "BreadcrumbList"})
        type_details: Per-detected-type metadata mapping type name to dict
            with "count" (int) and "formats" (list of format name strings
            where the type was found)
        score: Weighted schema score in 0.0-1.0 range
        fetched_at: Timestamp of analysis
    """

    url: str
    raw: dict[str, list] = field(default_factory=dict)
    detected_types: set[str] = field(default_factory=set)
    type_details: dict[str, dict] = field(default_factory=dict)
    score: float = 0.0
    fetched_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class ContentAnalysis:
    """Complete content quality analysis result.

    Consumed by Phase 5 scorer for the content component (35% weight).

    Fields:
        url: The URL whose content was analyzed
        readability_score: Combined readability sub-score 0.0-1.0 (avg of Flesch + Fog)
        text_ratio: Content-to-HTML ratio 0.0-1.0 (actual text vs markup)
        entity_score: Named entity presence/diversity score 0.0-1.0
        heading_score: Heading structure quality score 0.0-1.0
        qa_density_score: Q&A density score 0.0-1.0
        flesch_raw: Raw Flesch Reading Ease score (0-100+ scale, clamped to >=0)
        fog_raw: Raw Gunning Fog Index grade level
        raw_text_ratio: Raw plain_text_length / html_length ratio
        entities: Dict mapping entity type (ORG/PRODUCT/GPE/PERSON) to list of text values
        heading_analysis: Dict with heading counts, H1 uniqueness, hierarchy violations, descriptiveness
        qa_analysis: Dict with question_count, answer_count, total_sentences
        combined_score: Weighted combined score 0.0-1.0 (equal weight sub-signals per planner discretion)
        fetched_at: Timestamp of analysis
    """

    url: str
    readability_score: float = 0.0
    text_ratio: float = 0.0
    entity_score: float = 0.0
    heading_score: float = 0.0
    qa_density_score: float = 0.0
    flesch_raw: float = 0.0
    fog_raw: float = 0.0
    raw_text_ratio: float = 0.0
    entities: dict[str, list[str]] = field(default_factory=dict)
    heading_analysis: dict = field(default_factory=dict)
    qa_analysis: dict = field(default_factory=dict)
    combined_score: float = 0.0
    fetched_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# TODO: v2 — CRAWL-03: add response.headers dict to FetchResult
