
from navigation.navigator import BrowserNavigator


def test_navigation_success(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="test_run",
    )

    assert result.status == "success"
    assert result.page_title == "OmniSight Test Page"
    assert result.url == local_url
    assert result.run_id == "test_run"


def test_invalid_url():
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url="invalid-url",
        run_id="invalid_run",
    )

    assert result.status == "failed"
    assert result.error == "Invalid URL"
