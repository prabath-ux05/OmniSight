
from pathlib import Path

from navigation.navigator import BrowserNavigator


def test_evidence_contract(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="contract_test",
    )

    assert result.status == "success"
    assert result.run_id == "contract_test"
    assert result.url == local_url
    assert result.page_title == "OmniSight Test Page"
    assert result.captured_at

    assert "width" in result.viewport
    assert "height" in result.viewport

    assert Path(result.screenshot_path).is_file()
    assert Path(result.dom_snapshot_path).is_file()

    assert isinstance(result.console_errors, list)
    assert isinstance(result.page_errors, list)
    assert result.error is None


def test_run_id_preserved(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="my_run_123",
    )

    assert result.run_id == "my_run_123"
