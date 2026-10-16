from browser_agent.navigation.navigator import BrowserNavigator


def test_navigation_success():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        "https://example.com"
    )

    assert result.status == "success"
    assert result.page_title != ""
    assert "example" in result.page_title.lower()


def test_invalid_url():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        "invalid-url"
    )

    assert result.status == "failed"
    assert result.error is not None