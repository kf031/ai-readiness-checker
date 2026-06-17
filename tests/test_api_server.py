"""Tests for FastAPI API server."""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient

from src.checker.api_server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_get_endpoint():
    with patch("src.checker.api_server.run_pipeline") as mock_run:
        mock_report = Mock()
        mock_report.url = "https://example.com"
        mock_report.overall_score = 62.5
        mock_report.grade = "C"
        mock_report.module_breakdown = {"robots": {"score": 0.8, "weight": 0.2, "weighted": 16.0}}
        mock_report.recommendations = []

        mock_run.return_value = {
            "report": mock_report,
            "errors": [],
            "complete": True,
            "stages_run": ["crawl", "access_signals", "schema", "content", "score"],
        }

        response = client.get("/analyze?url=https://example.com")
        assert response.status_code == 200
        data = response.json()
        assert data["url"] == "https://example.com"
        assert data["overall_score"] == 62.5
        assert data["grade"] == "C"
        assert data["complete"] is True


def test_analyze_post_endpoint():
    with patch("src.checker.api_server.run_pipeline") as mock_run:
        mock_report = Mock()
        mock_report.url = "https://test.com"
        mock_report.overall_score = 85.0
        mock_report.grade = "A"
        mock_report.module_breakdown = {}
        mock_report.recommendations = []

        mock_run.return_value = {
            "report": mock_report,
            "errors": [],
            "complete": True,
            "stages_run": [],
        }

        response = client.post("/analyze", json={"url": "https://test.com"})
        assert response.status_code == 200
        data = response.json()
        assert data["grade"] == "A"


def test_analyze_missing_url():
    response = client.get("/analyze")
    assert response.status_code == 422  # FastAPI validation error


def test_fix_endpoint():
    from src.checker.contracts import FetchResult
    from bs4 import BeautifulSoup

    with patch("src.checker.api_server.run_pipeline") as mock_run, \
         patch("src.checker.api_server.run_llm_agent") as mock_agent:
        html = "<html><head></head><body><h1>Test</h1></body></html>"
        fetch_result = Mock(spec=FetchResult)
        fetch_result.html = html

        mock_report = Mock()
        mock_report.url = "https://example.com"
        mock_report.overall_score = 55.0
        mock_report.grade = "C"

        mock_run.return_value = {
            "report": mock_report,
            "fetch_result": fetch_result,
        }

        mock_agent.return_value = Mock(
            skills_called=["fix-schema", "fix-headings"],
            changes=["Added schema", "Fixed H1"],
            explanation="# Changes made",
            improved_html=html,
            diff_html="<html>diff</html>",
        )

        response = client.post("/fix", json={"url": "https://example.com"})
        assert response.status_code == 200
        data = response.json()
        assert "fix-schema" in data["skills_called"]
        assert len(data["changes"]) == 2


def test_fix_endpoint_fetch_failed():
    from src.checker.contracts import CrawlError

    with patch("src.checker.api_server.run_pipeline") as mock_run:
        mock_run.return_value = {
            "fetch_result": CrawlError(url="https://example.com", error_type="connection_error", message="failed"),
            "report": None,
        }

        response = client.post("/fix", json={"url": "https://example.com"})
        assert response.status_code == 502
