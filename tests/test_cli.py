"""Integration tests for the CLI entry point — argparse, help output, and pipeline delegation."""

from unittest.mock import patch

import pytest


def test_cli_help_output(capsys):
    """Verify --help prints usage, exits 0, and contains expected text."""
    from checker.__main__ import main

    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "AI Readiness Checker" in captured.out
    assert "--timeout" in captured.out
    assert "--verbose" in captured.out


@patch("checker.__main__.display_score_card")
@patch("checker.__main__.run_pipeline")
def test_cli_url_argument_parsed(mock_run, mock_display):
    """Verify URL positional argument is parsed and forwarded to run_pipeline."""
    mock_run.return_value = {
        "report": None,
        "errors": [],
        "complete": True,
        "stages_run": ["crawl"],
    }
    from checker.__main__ import main

    result = main(["https://example.com"])
    assert result == 0
    mock_run.assert_called_once_with("https://example.com", timeout=10.0, verbose=False)
    mock_display.assert_called_once()


@patch("checker.__main__.display_score_card")
@patch("checker.__main__.run_pipeline")
def test_cli_default_timeout(mock_run, mock_display):
    """Verify default timeout is 10.0 when no --timeout flag is given."""
    mock_run.return_value = {"report": None, "errors": [], "complete": True, "stages_run": []}
    from checker.__main__ import main

    main(["https://example.com"])
    assert mock_run.call_args[1]["timeout"] == 10.0


@patch("checker.__main__.display_score_card")
@patch("checker.__main__.run_pipeline")
def test_cli_custom_timeout(mock_run, mock_display):
    """Verify --timeout flag passes the custom value through to run_pipeline."""
    mock_run.return_value = {"report": None, "errors": [], "complete": True, "stages_run": []}
    from checker.__main__ import main

    main(["https://example.com", "--timeout", "5.0"])
    assert mock_run.call_args[1]["timeout"] == 5.0


@patch("checker.__main__.display_score_card")
@patch("checker.__main__.run_pipeline")
def test_cli_verbose_flag(mock_run, mock_display):
    """Verify --verbose flag sets verbose=True in the pipeline call."""
    mock_run.return_value = {"report": None, "errors": [], "complete": True, "stages_run": []}
    from checker.__main__ import main

    main(["https://example.com", "--verbose"])
    assert mock_run.call_args[1]["verbose"] is True


@patch("checker.__main__.display_score_card")
@patch("checker.__main__.run_pipeline")
def test_cli_verbose_short_flag(mock_run, mock_display):
    """Verify -v short flag also sets verbose=True."""
    mock_run.return_value = {"report": None, "errors": [], "complete": True, "stages_run": []}
    from checker.__main__ import main

    main(["https://example.com", "-v"])
    assert mock_run.call_args[1]["verbose"] is True


def test_cli_missing_url_exits(capsys):
    """Verify missing URL argument triggers argparse error and non-zero exit."""
    from checker.__main__ import main

    with pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code != 0  # argparse exits with 2 on error
    captured = capsys.readouterr()
    assert "the following arguments are required" in captured.err.lower() or "error" in captured.err.lower()
