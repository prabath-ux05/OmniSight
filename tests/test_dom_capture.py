
from pathlib import Path

from navigation.navigator import BrowserNavigator


def test_dom_snapshot_creation(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="dom_test",
    )

    assert result.status == "success"

    dom_file = Path(result.dom_snapshot_path)
    assert dom_file.exists()
    assert dom_file.is_file()

    content = dom_file.read_text(encoding="utf-8")
    assert "OmniSight Browser Agent Test" in content
