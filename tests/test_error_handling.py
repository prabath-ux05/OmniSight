from navigation.navigator import BrowserNavigator


def test_invalid_url():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        "invalid-url",
        "invalid_run"
    )

    assert result.status == "failed"
    assert result.error == "Invalid URL"


def test_console_error_structure():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        "https://example.com",
        "console_run"
    )

    assert isinstance(
        result.console_errors,
        list
    )

    assert isinstance(
        result.page_errors,
        list
    )