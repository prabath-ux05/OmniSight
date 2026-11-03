import pytest

from navigation.url_validator import validate_url, validate_run_id


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://example.com",
        "https://example.com/login",
        "https://example.com/page?id=10",
        "http://127.0.0.1:8000",
        "https://example.com/page#section",
    ],
)
def test_valid_urls(url):
    is_valid, message = validate_url(url)

    assert is_valid is True
    assert message == "Valid URL"


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "example.com",
        "ftp://example.com",
        "javascript:alert(1)",
        "https://",
        "https://example.com:invalid",
        "https://user:password@example.com",
        "https://example.com with spaces",
        "https://-invalid-domain.com",
    ],
)
def test_invalid_urls(url):
    is_valid, message = validate_url(url)

    assert is_valid is False
    assert message != "Valid URL"


def test_non_string_url():
    is_valid, message = validate_url(None)

    assert is_valid is False
    assert message == "URL is required"


@pytest.mark.parametrize(
    "run_id",
    [
        "test_run",
        "run123",
        "browser-agent-01",
        "Run_2026",
    ],
)
def test_valid_run_ids(run_id):
    is_valid, message = validate_run_id(run_id)

    assert is_valid is True
    assert message == "Valid run_id"


@pytest.mark.parametrize(
    "run_id",
    [
        "",
        "   ",
        "../folder",
        "../../artifacts",
        "run/test",
        "run name",
        "run@123",
        "-invalid",
    ],
)
def test_invalid_run_ids(run_id):
    is_valid, message = validate_run_id(run_id)

    assert is_valid is False
    assert message != "Valid run_id"


def test_non_string_run_id():
    is_valid, message = validate_run_id(None)

    assert is_valid is False
    assert message == "run_id is required"