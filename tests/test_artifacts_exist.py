from pathlib import Path

from navigation.navigator import BrowserNavigator


def test_artifacts_exist():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        "https://example.com",
        "artifact_run"
    )

    assert Path(
        result.screenshot_path
    ).exists()

    assert Path(
        result.dom_snapshot_path
    ).exists()