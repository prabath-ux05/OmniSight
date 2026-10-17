from navigation.navigator import BrowserNavigator


def test_navigation_success():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url="https://example.com",
        run_id="test_run"
    )

    assert result.status == "success"
    assert result.page_title != ""
    assert "example" in result.page_title.lower()


def test_invalid_url():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        url="invalid-url",
        run_id="test_run"
    )

    assert result.status == "failed"
    assert result.error is not None