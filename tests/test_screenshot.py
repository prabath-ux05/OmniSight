
from pathlib import Path

from navigation.navigator import BrowserNavigator


def test_screenshot_creation(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="screenshot_test",
    )

    assert result.status == "success"

    screenshot_file = Path(result.screenshot_path)
    assert screenshot_file.exists()
    assert screenshot_file.is_file()
    assert screenshot_file.stat().st_size > 0


def test_broken_image_does_not_prevent_capture(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="broken_image_test",
    )

    assert result.status == "success"
    assert Path(result.screenshot_path).is_file()
    assert Path(result.dom_snapshot_path).is_file()
