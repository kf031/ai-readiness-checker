"""Tests for llms_txt.py — covers LLMS-01 and LLMS-02."""

import pytest
from unittest.mock import Mock, patch
import httpx

from src.checker.llms_txt import validate_llms_txt, fetch_llms_txt, compute_llms_score
from src.checker.contracts import LlmsResult
from tests.conftest import (
    LLMS_TXT_VALID,
    LLMS_TXT_NO_H1,
    LLMS_TXT_H1_ONLY,
    LLMS_TXT_H2_NO_LINKS,
)


# ----- LLMS-01: Check llms.txt presence and validate format -----

def test_valid_llms_txt():
    """LLMS-01: Valid llms.txt detected as found + valid."""
    is_valid, errors = validate_llms_txt(LLMS_TXT_VALID)
    assert is_valid is True
    assert errors == []

    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = LLMS_TXT_VALID
    mock_client = Mock()
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.get = Mock(return_value=mock_response)
    with patch('httpx.Client', return_value=mock_client):
        result = fetch_llms_txt("https://example.com")
        assert result.found is True
        assert result.valid is True
        assert result.validation_errors == []
        assert result.content_preview is not None
        assert result.raw_text is not None


def test_content_preview():
    """LLMS-01: 500-char content preview extracted."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.text = LLMS_TXT_VALID
    mock_client = Mock()
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.get = Mock(return_value=mock_response)
    with patch('httpx.Client', return_value=mock_client):
        result = fetch_llms_txt("https://example.com")
        assert len(result.content_preview) <= 500
        assert result.content_preview == LLMS_TXT_VALID[:500]
        assert result.raw_text == LLMS_TXT_VALID


def test_malformed_no_h1():
    """LLMS-01: Malformed llms.txt (no H1) detected as invalid."""
    is_valid, errors = validate_llms_txt(LLMS_TXT_NO_H1)
    assert is_valid is False
    assert len(errors) >= 1
    assert any("H1" in err or "h1" in err for err in errors)
    assert compute_llms_score(found=True, valid=False) == 0.3


def test_malformed_h2_no_links():
    """LLMS-01: llms.txt with H2 but no links detected as invalid."""
    is_valid, errors = validate_llms_txt(LLMS_TXT_H2_NO_LINKS)
    assert is_valid is False

    is_valid_h1_only, errors_h1_only = validate_llms_txt(LLMS_TXT_H1_ONLY)
    assert is_valid_h1_only is False
    assert any("No H2" in err for err in errors_h1_only)

    assert compute_llms_score(found=True, valid=False) == 0.3


def test_llms_txt_not_found():
    """LLMS-01: 404 returns found=False."""
    mock_response = Mock()
    mock_response.status_code = 404
    mock_response.text = ""
    mock_client = Mock()
    mock_client.__enter__ = Mock(return_value=mock_client)
    mock_client.__exit__ = Mock(return_value=False)
    mock_client.get = Mock(return_value=mock_response)
    with patch('httpx.Client', return_value=mock_client):
        result = fetch_llms_txt("https://example.com")
        assert result.found is False
        assert result.valid is None
        assert result.status_code == 404
        assert compute_llms_score(found=False, valid=None) == 0.0


# ----- LLMS-02: Compute llms.txt score -----

def test_llms_score_found():
    """LLMS-02: Found + valid = score 1.0."""
    assert compute_llms_score(found=True, valid=True) == 1.0


def test_llms_score_not_found():
    """LLMS-02: Not found = score 0.0."""
    assert compute_llms_score(found=False, valid=None) == 0.0
    assert compute_llms_score(found=False, valid=False) == 0.0


def test_llms_score_malformed():
    """LLMS-02: Found but malformed = score 0.3."""
    assert compute_llms_score(found=True, valid=False) == 0.3
    assert compute_llms_score(found=True, valid=None) == 0.3


# ----- Error handling tests -----

def test_llms_txt_connection_error():
    """LLMS-01: Connection error returns fetch_error."""
    with patch('httpx.Client') as mock_client_class:
        mock_client_class.side_effect = httpx.ConnectError("connection refused")
        result = fetch_llms_txt("https://example.com")
    assert result.found is False
    assert result.fetch_error == "connection_error"


def test_llms_txt_timeout():
    """LLMS-01: Timeout returns fetch_error='timeout'."""
    with patch('httpx.Client') as mock_client_class:
        mock_client_class.side_effect = httpx.TimeoutException("timed out")
        result = fetch_llms_txt("https://example.com")
    assert result.found is False
    assert result.fetch_error == "timeout"
