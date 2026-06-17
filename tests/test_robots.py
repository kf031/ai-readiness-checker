"""Tests for robots_txt.py — covers BOT-01 and BOT-02."""

from unittest.mock import patch, Mock
import httpx

from checker.robots_txt import analyze_robots, compute_bot_score, fetch_robots_txt, BOT_TOKENS, MAX_ROBOTS_SIZE
from tests.conftest import (
    ROBOTS_TXT_ALL_ALLOWED,
    ROBOTS_TXT_ALL_BLOCKED,
    ROBOTS_TXT_MIXED,
    ROBOTS_TXT_CATCHALL,
    ROBOTS_TXT_CASE_VARIANT,
)


# ----- BOT-01: Parse robots.txt and classify each bot -----

def test_all_bots_explicitly_mentioned():
    """BOT-01: All 7 AI bots classified correctly from parsed robots.txt."""
    result = analyze_robots(ROBOTS_TXT_ALL_ALLOWED)
    assert len(result) == 7
    for i, bot in enumerate(result):
        assert bot.explicitly_mentioned is True, f"{bot.bot_name} should be explicitly mentioned"
        assert bot.status == "allowed", f"{bot.bot_name} should be allowed"
        assert bot.bot_name == BOT_TOKENS[i], f"Bot at index {i} should be {BOT_TOKENS[i]}"
    score = compute_bot_score(result)
    assert score == 0.99


def test_bot_not_mentioned():
    """BOT-01: Bot not in any User-agent line returns not_mentioned."""
    robots_text = """User-agent: GPTBot
Allow: /
User-agent: ClaudeBot
Disallow: /
"""
    result = analyze_robots(robots_text)
    # Find PerplexityBot (index 2)
    perplexity = result[2]
    assert perplexity.bot_name == "PerplexityBot"
    assert perplexity.status == "not_mentioned"
    assert perplexity.explicitly_mentioned is False
    # Find Amazonbot (index 6)
    amazon_bot = result[6]
    assert amazon_bot.bot_name == "Amazonbot"
    assert amazon_bot.status == "not_mentioned"
    assert amazon_bot.explicitly_mentioned is False


def test_catchall_applies():
    """BOT-01: * catch-all applies when no specific bot group exists."""
    result = analyze_robots(ROBOTS_TXT_CATCHALL)
    assert len(result) == 7
    for bot in result:
        assert bot.explicitly_mentioned is False, (
            f"{bot.bot_name} should be covered by * catch-all, not explicitly mentioned"
        )
        assert bot.status == "allowed", (
            f"{bot.bot_name} should be allowed (Allow: / is the last matching rule for root)"
        )
    score = compute_bot_score(result)
    assert score == 0.99


def test_google_extended_caseless():
    """BOT-01: Bot tokens matched case-insensitively."""
    result = analyze_robots(ROBOTS_TXT_CASE_VARIANT)
    # GPTBot matched via "gptbot" (lowercase)
    assert result[0].bot_name == "GPTBot"
    assert result[0].explicitly_mentioned is True
    assert result[0].status == "allowed"
    # ClaudeBot matched via "CLAUDEBOT" (uppercase)
    assert result[1].bot_name == "ClaudeBot"
    assert result[1].explicitly_mentioned is True
    assert result[1].status == "blocked"
    # All others: no catchall in CASE_VARIANT, should be not_mentioned
    for i in range(2, 7):
        assert result[i].status == "not_mentioned", (
            f"{result[i].bot_name} should be not_mentioned (no catchall)"
        )
        assert result[i].explicitly_mentioned is False


# ----- BOT-02: Compute bot access score -----

def test_score_all_allowed():
    """BOT-02: All 7 allowed = score 0.99."""
    result = analyze_robots(ROBOTS_TXT_ALL_ALLOWED)
    score = compute_bot_score(result)
    assert score == 0.99


def test_score_all_blocked():
    """BOT-02: All 7 blocked = score 0.01."""
    result = analyze_robots(ROBOTS_TXT_ALL_BLOCKED)
    score = compute_bot_score(result)
    assert score == 0.01


def test_scoring_formula():
    """BOT-02: Score calculation from BotStatus list (mixed scenario)."""
    result = analyze_robots(ROBOTS_TXT_MIXED)
    # MIXED: GPTBot blocked, ClaudeBot allowed, PerplexityBot allowed,
    # other 4 bots via * catchall (Disallow: /) = blocked
    assert result[0].bot_name == "GPTBot"
    assert result[0].status == "blocked"
    assert result[1].bot_name == "ClaudeBot"
    assert result[1].status == "allowed"
    assert result[2].bot_name == "PerplexityBot"
    assert result[2].status == "allowed"
    # CCBot, Google-Extended, Applebot-Extended, Amazonbot via * -> blocked
    for i in range(3, 7):
        assert result[i].status == "blocked", (
            f"{result[i].bot_name} should be blocked via * catchall Disallow: /"
        )
    # Score = 0.5 + (2 * 0.07) - (5 * 0.07) = 0.5 + 0.14 - 0.35 = 0.29
    score = compute_bot_score(result)
    assert score == 0.29


def test_missing_robots_txt():
    """BOT-02: 404 returns exists=False, empty bots, score 0.5."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = ""

    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        result = fetch_robots_txt("https://example.com")

    assert result.exists is False
    assert result.status_code == 404
    assert result.fetch_error is None
    assert result.bots == []
    # Empty bots list -> compute_bot_score returns 0.5
    score = compute_bot_score(result.bots)
    assert score == 0.5


def test_robots_connection_error():
    """BOT-02: Connection error returns exists=False, fetch_error='connection_error'."""
    with patch('httpx.Client') as mock_client:
        mock_client.side_effect = httpx.ConnectError("connection refused")
        result = fetch_robots_txt("https://example.com")

    assert result.exists is False
    assert result.fetch_error == "connection_error"
    assert result.bots == []
    # Connection error score is 0.3 (enforced by caller, not inside compute_bot_score)
    score = compute_bot_score(result.bots)
    assert score == 0.5  # compute_bot_score on empty list = baseline 0.5


# ----- fetch_robots_txt error path tests -----

def test_fetch_robots_txt_401():
    """401 response returns exists=False, status_code=401, fetch_error=None."""
    mock_response = Mock()
    mock_response.status_code = 401
    mock_response.text = ""

    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        result = fetch_robots_txt("https://example.com")

    assert result.exists is False
    assert result.status_code == 401
    assert result.fetch_error is None
    assert result.bots == []
    assert result.raw_text is None


def test_fetch_robots_txt_403():
    """403 response returns exists=False, status_code=403, fetch_error=None."""
    mock_response = Mock()
    mock_response.status_code = 403
    mock_response.text = ""

    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        result = fetch_robots_txt("https://example.com")

    assert result.exists is False
    assert result.status_code == 403
    assert result.fetch_error is None
    assert result.bots == []
    assert result.raw_text is None


def test_fetch_robots_txt_500():
    """500 response returns exists=False, fetch_error='http_error_500'."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = ""

    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        result = fetch_robots_txt("https://example.com")

    assert result.exists is False
    assert result.status_code == 500
    assert result.fetch_error == "http_error_500"
    assert result.bots == []
    assert result.raw_text is None


def test_fetch_robots_txt_too_large():
    """Response exceeding MAX_ROBOTS_SIZE returns fetch_error='response_too_large'."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = "x" * (MAX_ROBOTS_SIZE + 1)

    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        result = fetch_robots_txt("https://example.com")

    assert result.exists is False
    assert result.fetch_error == "response_too_large"
    assert result.bots == []
    assert result.raw_text is None


def test_fetch_robots_txt_timeout():
    """TimeoutException returns exists=False, fetch_error='timeout'."""
    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = httpx.TimeoutException("timeout")
        result = fetch_robots_txt("https://example.com")

    assert result.exists is False
    assert result.fetch_error == "timeout"
    assert result.bots == []
    assert result.raw_text is None


def test_fetch_robots_txt_http_status_error():
    """HTTPStatusError returns exists=False, fetch_error='http_error_{code}'."""
    mock_resp = Mock()
    mock_resp.status_code = 502
    error = httpx.HTTPStatusError("Bad Gateway", request=Mock(), response=mock_resp)
    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = error
        result = fetch_robots_txt("https://example.com")

    assert result.exists is False
    assert result.status_code == 502
    assert result.fetch_error == "http_error_502"
    assert result.bots == []
    assert result.raw_text is None


def test_fetch_robots_txt_general_exception():
    """General Exception returns exists=False, fetch_error='request_error'."""
    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.side_effect = RuntimeError("unexpected")
        result = fetch_robots_txt("https://example.com")

    assert result.exists is False
    assert result.fetch_error == "request_error"
    assert result.bots == []
    assert result.raw_text is None


def test_fetch_robots_txt_success():
    """200 OK with valid robots text returns exists=True, bots populated."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = ROBOTS_TXT_ALL_ALLOWED

    with patch('httpx.Client') as mock_client:
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response
        result = fetch_robots_txt("https://example.com")

    assert result.exists is True
    assert result.fetch_error is None
    assert len(result.bots) == 7
    assert result.raw_text == ROBOTS_TXT_ALL_ALLOWED
    assert result.status_code == 200
    assert result.bots[0].status == "allowed"
