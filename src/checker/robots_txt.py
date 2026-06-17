"""
robots.txt analysis module — fetch, parse, classify AI bot access, and score.

Consumed by Phase 5 scorer for the robots component (20% weight).
"""

from datetime import datetime, timezone
from typing import Optional
from urllib.robotparser import RobotFileParser

import httpx

from checker.contracts import RobotsResult, BotStatus


# ---- Constants ----

BOT_TOKENS = [
    "GPTBot",
    "ClaudeBot",
    "PerplexityBot",
    "CCBot",
    "Google-Extended",
    "Applebot-Extended",
    "Amazonbot",
]

MAX_ROBOTS_SIZE = 1_048_576  # 1MB per D-07

ROBOTS_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/131.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/plain,text/html,*/*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
}

DEFAULT_TIMEOUT = 10.0


# ---- Core Analysis ----

def analyze_robots(robots_text: str) -> list[BotStatus]:
    """Parse robots.txt text and return per-bot classification for all 7 AI bots.

    Uses urllib.robotparser for parsing the robots.txt structure (entry groups,
    rule lines). Then performs custom case-insensitive exact-token matching
    against entry.useragents for each of the 7 known AI bot product tokens.

    Per D-06: The User-agent: * catch-all counts as mentioning each bot.
    If a bot has no specific group but * exists, the bot gets the * group's
    rule applied with explicitly_mentioned=False (the * covers it).

    Args:
        robots_text: Raw robots.txt content as a string.

    Returns:
        List of 7 BotStatus objects, one per AI bot token, in BOT_TOKENS order.
    """
    rp = RobotFileParser()
    rp.parse(robots_text.splitlines())

    results = []

    for token in BOT_TOKENS:
        token_lower = token.lower()
        entry = None
        explicit = False

        # Step 1: Search specific user-agent groups for exact match (case-insensitive)
        for e in rp.entries:
            for ua in e.useragents:
                if token_lower == ua.lower():
                    entry = e
                    explicit = True
                    break
            if entry is not None:
                break

        # Step 2: Fall back to default_entry (User-agent: * catch-all)
        # Per D-06: * catch-all counts as mentioning each bot
        if entry is None and rp.default_entry:
            entry = rp.default_entry
            explicit = False

        # Step 3: Evaluate Allow/Disallow rules for root path "/"
        if entry is not None:
            status = _eval_rules_for_root(entry)
            rule_line = _find_rule_line_for_root(entry)
        else:
            status = "not_mentioned"
            rule_line = None

        results.append(BotStatus(
            bot_name=token,
            status=status,
            rule_line=rule_line,
            explicitly_mentioned=explicit,
        ))

    return results


def _eval_rules_for_root(entry) -> str:
    """Evaluate Allow/Disallow rules against the root path '/'.

    Iterates rulelines in source order and returns 'allowed' or 'blocked'
    based on the rule that applies to '/'. If no rule matches, returns
    'allowed' (per RFC 9309: no matching rule = allowed).

    Since we only check the root path, longest-match is irrelevant here.
    We take the first matching rule in source order (which is effectively
    last-match-wins since we iterate all and the last match overwrites).
    """
    result = "allowed"
    for rule in entry.rulelines:
        if rule.applies_to("/"):
            result = "allowed" if rule.allowance else "blocked"
    return result


def _find_rule_line_for_root(entry) -> Optional[str]:
    """Return the Allow/Disallow directive string that governs the root path.
    Returns the last matching rule (the one that takes effect).
    """
    found = None
    for rule in entry.rulelines:
        if rule.applies_to("/"):
            prefix = "Allow" if rule.allowance else "Disallow"
            found = f"{prefix}: {rule.path}"
    return found


# ---- Scoring ----

def compute_bot_score(statuses: list[BotStatus]) -> float:
    """Compute 0.0-1.0 bot access score from per-bot status list.

    Per D-01:
    - Baseline: 0.5
    - Each allowed bot: +0.07
    - Each blocked bot: -0.07
    - Each not_mentioned: 0.0 (neutral)
    - Range: 0.01 (all 7 blocked) to 0.99 (all 7 allowed)

    Args:
        statuses: List of BotStatus from analyze_robots().

    Returns:
        Float between 0.01 and 0.99.
    """
    score = 0.5
    for bot in statuses:
        if bot.status == "allowed":
            score += 0.07
        elif bot.status == "blocked":
            score -= 0.07
        # not_mentioned: no change
    return round(max(0.0, min(1.0, score)), 2)


# ---- Fetch ----

def fetch_robots_txt(url: str, timeout: float = DEFAULT_TIMEOUT) -> RobotsResult:
    """Fetch and analyze robots.txt from a website's root.

    This function NEVER raises — it always returns a RobotsResult.

    Error handling per D-02:
    - 404: missing robots.txt -> score 0.5, exists=False
    - Connection errors / timeouts / server errors -> score 0.3, exists=False
    - Response too large (>1MB) -> score 0.3 per D-07

    Per D-07: responses exceeding MAX_ROBOTS_SIZE (1MB) are rejected.

    Args:
        url: The base URL of the site (e.g., "https://example.com").
        timeout: HTTP request timeout in seconds. Default 10.0.

    Returns:
        RobotsResult with per-bot breakdown and computed score.
    """
    robots_url = url.rstrip('/') + '/robots.txt'
    now = datetime.now(timezone.utc)

    try:
        with httpx.Client(
            timeout=timeout,
            headers=ROBOTS_HEADERS,
            follow_redirects=True,
        ) as client:
            response = client.get(robots_url)

        status_code = response.status_code

        # 404 = missing robots.txt (per D-02)
        if status_code == 404:
            return RobotsResult(
                url=url,
                exists=False,
                status_code=status_code,
                fetch_error=None,
                bots=[],
                raw_text=None,
                fetched_at=now,
            )

        # 401/403 = server blocks access, treat as missing (per RESEARCH.md error taxonomy)
        if status_code in (401, 403):
            return RobotsResult(
                url=url,
                exists=False,
                status_code=status_code,
                fetch_error=None,
                bots=[],
                raw_text=None,
                fetched_at=now,
            )

        # Other 4xx/5xx = infrastructure error (per D-02)
        if status_code >= 400:
            return RobotsResult(
                url=url,
                exists=False,
                status_code=status_code,
                fetch_error=f"http_error_{status_code}",
                bots=[],
                raw_text=None,
                fetched_at=now,
            )

        # Success: check size limit (per D-07)
        content = response.text
        if len(content.encode('utf-8')) > MAX_ROBOTS_SIZE:
            return RobotsResult(
                url=url,
                exists=False,
                status_code=status_code,
                fetch_error="response_too_large",
                bots=[],
                raw_text=None,
                fetched_at=now,
            )

        # Parse and analyze
        bot_statuses = analyze_robots(content)

        return RobotsResult(
            url=url,
            exists=True,
            status_code=status_code,
            fetch_error=None,
            bots=bot_statuses,
            raw_text=content,
            fetched_at=now,
        )

    except httpx.TimeoutException:
        return RobotsResult(
            url=url,
            exists=False,
            fetch_error="timeout",
            bots=[],
            raw_text=None,
            fetched_at=now,
        )
    except httpx.ConnectError:
        return RobotsResult(
            url=url,
            exists=False,
            fetch_error="connection_error",
            bots=[],
            raw_text=None,
            fetched_at=now,
        )
    except httpx.HTTPStatusError as e:
        return RobotsResult(
            url=url,
            exists=False,
            status_code=e.response.status_code,
            fetch_error=f"http_error_{e.response.status_code}",
            bots=[],
            raw_text=None,
            fetched_at=now,
        )
    except Exception as e:
        return RobotsResult(
            url=url,
            exists=False,
            fetch_error="request_error",
            bots=[],
            raw_text=None,
            fetched_at=now,
        )
