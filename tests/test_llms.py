"""Tests for llms_txt.py — covers LLMS-01 and LLMS-02."""

import pytest


# ----- LLMS-01: Check llms.txt presence and validate format -----

def test_valid_llms_txt():
    """LLMS-01: Valid llms.txt detected as found + valid.
    STATUS: STUB — Wave 0 scaffold. Plan 02-03 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-03")


def test_content_preview():
    """LLMS-01: 500-char content preview extracted.
    STATUS: STUB — Wave 0 scaffold. Plan 02-03 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-03")


def test_malformed_no_h1():
    """LLMS-01: Malformed llms.txt (no H1) detected as invalid.
    STATUS: STUB — Wave 0 scaffold. Plan 02-03 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-03")


def test_malformed_h2_no_links():
    """LLMS-01: llms.txt with H2 but no links detected as invalid.
    STATUS: STUB — Wave 0 scaffold. Plan 02-03 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-03")


def test_llms_txt_not_found():
    """LLMS-01: 404 returns found=False.
    STATUS: STUB — Wave 0 scaffold. Plan 02-03 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-03")


# ----- LLMS-02: Compute llms.txt score -----

def test_llms_score_found():
    """LLMS-02: Found + valid = score 1.0.
    STATUS: STUB — Wave 0 scaffold. Plan 02-03 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-03")


def test_llms_score_not_found():
    """LLMS-02: Not found = score 0.0.
    STATUS: STUB — Wave 0 scaffold. Plan 02-03 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-03")


def test_llms_score_malformed():
    """LLMS-02: Found but malformed = score 0.3.
    STATUS: STUB — Wave 0 scaffold. Plan 02-03 implements."""
    pytest.skip("Wave 0 stub — implement in Plan 02-03")
