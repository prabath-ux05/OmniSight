from ..navigation.navigator import BrowserNavigator


def test_metadata_capture():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url="https://example.com",
        run_id="metadata_test"
    )

    assert result.status == "success"

    assert result.page_title
    assert result.url

    assert result.captured_at

    assert "width" in result.viewport
    assert "height" in result.viewport