from navigation.navigator import BrowserNavigator


def test_evidence_contract():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        "https://example.com",
        "contract_run"
    )

    assert result.run_id == "contract_run"

    assert result.url
    assert result.page_title

    assert result.screenshot_path
    assert result.dom_snapshot_path

    assert result.status == "success"

    assert isinstance(
        result.console_errors,
        list
    )

    assert isinstance(
        result.page_errors,
        list
    )


def test_run_id_preserved():

    navigator = BrowserNavigator()

    result = navigator.navigate(
        "https://example.com",
        "my_run_123"
    )

    assert result.run_id == "my_run_123"