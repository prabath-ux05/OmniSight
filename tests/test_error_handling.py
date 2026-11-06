
from navigation.navigator import BrowserNavigator


def test_invalid_url():
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url="invalid-url",
        run_id="invalid_run",
    )

    assert result.status == "failed"
    assert result.error == "Invalid URL"


def test_run_id_required(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="",
    )

    assert result.status == "failed"
    assert result.error == "run_id is required"


def test_console_error_structure(local_url):
    navigator = BrowserNavigator()

    result = navigator.navigate(
        url=local_url,
        run_id="console_test",
    )

    assert result.status == "success"
    assert isinstance(result.console_errors, list)
    assert isinstance(result.page_errors, list)


def test_timeout_handling(slow_url):
    navigator = BrowserNavigator(timeout_ms=1)

    result = navigator.navigate(
        url=slow_url,
        run_id="timeout_test",
    )

    assert result.status == "failed"
    assert result.error == "Navigation timeout"
