
from pathlib import Path

from navigation.navigator import BrowserNavigator


def test_artifacts_exist(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="artifact_test",
    )

    assert result.status == "success"
    assert Path(result.screenshot_path).is_file()
    assert Path(result.dom_snapshot_path).is_file()
