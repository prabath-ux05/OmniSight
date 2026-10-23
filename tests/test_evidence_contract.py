
from pathlib import Path

from navigation.navigator import BrowserNavigator


def test_evidence_contract(local_url):
    """Verify that successful navigation returns the expected evidence."""

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="contract_test",
    )

    assert result.status == "success"
    assert result.run_id == "contract_test"
    assert result.url == local_url
    assert result.page_title == "OmniSight Test Page"

    # Timestamp should be present.
    assert result.captured_at
    assert isinstance(result.captured_at, str)

    # Viewport metadata should be present.
    assert isinstance(result.viewport, dict)
    assert "width" in result.viewport
    assert "height" in result.viewport

    # Screenshot and DOM evidence should exist.
    assert result.screenshot_path is not None
    assert Path(result.screenshot_path).is_file()

    assert result.dom_snapshot_path is not None
    assert Path(result.dom_snapshot_path).is_file()

    # Error collections should always be lists.
    assert isinstance(result.console_errors, list)
    assert isinstance(result.page_errors, list)

    # Successful navigation should not report a failure.
    assert result.error is None


def test_run_id_preserved(local_url):
    """Verify that the supplied run ID is preserved."""

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="my_run_123",
    )

    assert result.run_id == "my_run_123"
    assert result.status == "success"


def test_invalid_url_returns_failed_result():
    """Verify that an invalid URL is rejected."""

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url="invalid-url",
        run_id="invalid_url_test",
    )

    assert result.status == "failed"
    assert result.error == "Invalid URL"
    assert result.run_id == "invalid_url_test"
    assert result.screenshot_path is None
    assert result.dom_snapshot_path is None

    assert isinstance(result.console_errors, list)
    assert isinstance(result.page_errors, list)


def test_empty_url_returns_failed_result():
    """Verify that an empty URL is rejected."""

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url="",
        run_id="empty_url_test",
    )

    assert result.status == "failed"
    assert result.error == "Invalid URL"


def test_missing_run_id_returns_failed_result(local_url):
    """Verify that a missing run ID is rejected."""

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="",
    )

    assert result.status == "failed"
    assert result.error == "run_id is required"
    assert result.run_id == ""
    assert result.screenshot_path is None
    assert result.dom_snapshot_path is None


def test_failed_results_have_independent_error_lists():
    """Verify that separate results do not share error lists."""

    first_result = BrowserNavigator._failed_result(
        url="invalid-url",
        run_id="run_1",
        error="Invalid URL",
    )

    second_result = BrowserNavigator._failed_result(
        url="invalid-url",
        run_id="run_2",
        error="Invalid URL",
    )

    first_result.console_errors.append("Test error")

    assert first_result.console_errors == ["Test error"]
    assert second_result.console_errors == []
