"""Tests for robots_txt.py — covers BOT-01 and BOT-02."""

import pytest


# ----- BOT-01: Parse robots.txt and classify each bot -----

def test_all_bots_explicitly_mentioned():
    """BOT-01: All 7 AI bots classified correctly from parsed robots.txt.
    STATUS: STUB — Wave 0 scaffold. Plan 02-02 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-02")


def test_bot_not_mentioned():
    """BOT-01: Bot not in any User-agent line returns not_mentioned.
    STATUS: STUB — Wave 0 scaffold. Plan 02-02 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-02")


def test_catchall_applies():
    """BOT-01: * catch-all applies when no specific bot group exists.
    STATUS: STUB — Wave 0 scaffold. Plan 02-02 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-02")


def test_google_extended_caseless():
    """BOT-01: Google-Extended token matched case-insensitively.
    STATUS: STUB — Wave 0 scaffold. Plan 02-02 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-02")


# ----- BOT-02: Compute bot access score -----

def test_score_all_allowed():
    """BOT-02: All 7 allowed = score 0.99.
    STATUS: STUB — Wave 0 scaffold. Plan 02-02 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-02")


def test_score_all_blocked():
    """BOT-02: All 7 blocked = score 0.01.
    STATUS: STUB — Wave 0 scaffold. Plan 02-02 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-02")


def test_scoring_formula():
    """BOT-02: Score calculation from BotStatus list.
    STATUS: STUB — Wave 0 scaffold. Plan 02-02 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-02")


def test_missing_robots_txt():
    """BOT-02: 404 returns score 0.5.
    STATUS: STUB — Wave 0 scaffold. Plan 02-02 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-02")


def test_robots_connection_error():
    """BOT-02: Connection error returns score 0.3.
    STATUS: STUB — Wave 0 scaffold. Plan 02-02 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-02")
