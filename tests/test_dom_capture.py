from pathlib import Path

from ..navigation.navigator import BrowserNavigator


def test_dom_snapshot_creation():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url="https://example.com",
        run_id="dom_test"
    )

    assert result.status == "success"

    dom_file = Path(
        result.dom_snapshot_path
    )

    assert dom_file.exists()
    assert dom_file.is_file()