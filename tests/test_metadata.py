
from navigation.navigator import BrowserNavigator


def test_metadata_capture(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="metadata_test",
    )

    assert result.status == "success"
    assert result.page_title == "OmniSight Test Page"
    assert result.url == local_url
    assert result.captured_at

    assert isinstance(result.viewport, dict)
    assert "width" in result.viewport
    assert "height" in result.viewport
