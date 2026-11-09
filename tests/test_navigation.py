
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
    assert result.error is not None
    assert result.error != "Valid URL"


def test_http_404_response(local_server):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=f"{local_server}/missing-page",
        run_id="http_error_test",
    )

    assert result.status == "failed"
    assert result.response_status == 404
    assert "404" in result.error
