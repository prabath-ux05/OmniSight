from pathlib import Path

from navigation.navigator import BrowserNavigator


def test_screenshot_creation():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url="https://example.com",
        run_id="test_run"
    )

    assert result.status == "success"

    screenshot_file = Path(
        result.screenshot_path
    )

    assert screenshot_file.exists()
    assert screenshot_file.is_file()