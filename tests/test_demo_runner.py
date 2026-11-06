"""Focused test suite for OmniSight demo integration runner.

Tests inspection state definitions, URL construction for all states (clean, overflow,
missing, image, all), structured reachability data modeling, and live reachability
against the controlled demo site.
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Generator
import pytest

from integration.demo_runner import (
    DemoInspectionReport,
    DemoInspectionState,
    DemoReachabilityResult,
    STATE_QUERY_PARAMS,
    SUPPORTED_STATES,
    construct_demo_url,
    validate_demo_reachability,
    validate_demo_site,
    validate_demo_state,
)
from tests.test_demo_site import DEMO_SITE_DIR, ThreadedHTTPServer


@pytest.fixture(scope="module")
def live_demo_server() -> Generator[str, None, None]:
    """Spin up a temporary HTTP server delivering demo_site/ for integration checks."""
    server = ThreadedHTTPServer(DEMO_SITE_DIR)
    server.start()
    base_url = f"http://127.0.0.1:{server.port}"
    try:
        yield base_url
    finally:
        server.stop()


def test_expected_inspection_states_defined():
    """Verify the 5 expected inspection states and their query parameter mappings."""
    expected_states = ["clean", "overflow", "missing", "image", "all"]
    actual_states = [s.value for s in SUPPORTED_STATES]
    assert actual_states == expected_states

    # Check each enum member
    assert DemoInspectionState.CLEAN == "clean"
    assert DemoInspectionState.OVERFLOW == "overflow"
    assert DemoInspectionState.MISSING == "missing"
    assert DemoInspectionState.IMAGE == "image"
    assert DemoInspectionState.ALL == "all"

    # Check query parameter mappings match existing demo_site logic
    assert STATE_QUERY_PARAMS[DemoInspectionState.CLEAN] == {"state": "clean"}
    assert STATE_QUERY_PARAMS[DemoInspectionState.OVERFLOW] == {"defect": "overflow"}
    assert STATE_QUERY_PARAMS[DemoInspectionState.MISSING] == {"defect": "missing"}
    assert STATE_QUERY_PARAMS[DemoInspectionState.IMAGE] == {"defect": "image"}
    assert STATE_QUERY_PARAMS[DemoInspectionState.ALL] == {"defects": "all"}


def test_construct_demo_url_for_each_state():
    """Verify demo-site URL construction for all supported inspection states."""
    base = "http://127.0.0.1:8080"

    expected_urls = {
        "clean": "http://127.0.0.1:8080/?state=clean",
        "overflow": "http://127.0.0.1:8080/?defect=overflow",
        "missing": "http://127.0.0.1:8080/?defect=missing",
        "image": "http://127.0.0.1:8080/?defect=image",
        "all": "http://127.0.0.1:8080/?defects=all",
    }

    for state_name, expected_url in expected_urls.items():
        url_from_str = construct_demo_url(base, state_name)
        url_from_enum = construct_demo_url(base, DemoInspectionState(state_name))
        assert url_from_str == expected_url
        assert url_from_enum == expected_url


def test_construct_demo_url_variations():
    """Verify URL construction handles trailing slashes, existing query params, and schemes."""
    # Trailing slash handling
    url = construct_demo_url("http://127.0.0.1:8080/", "clean")
    assert url == "http://127.0.0.1:8080/?state=clean"

    # URL without scheme defaults to http
    url_no_scheme = construct_demo_url("127.0.0.1:8080", "clean")
    assert url_no_scheme == "http://127.0.0.1:8080/?state=clean"

    # Preserves existing query params while setting defect state
    url_with_query = construct_demo_url("http://127.0.0.1:8080/?session=live", "overflow")
    assert "session=live" in url_with_query
    assert "defect=overflow" in url_with_query

    # Case-insensitive state matching
    assert construct_demo_url("http://127.0.0.1:8080", "CLEAN") == "http://127.0.0.1:8080/?state=clean"
    assert construct_demo_url("http://127.0.0.1:8080", " Overflow ") == "http://127.0.0.1:8080/?defect=overflow"


def test_construct_demo_url_validation_errors():
    """Ensure invalid states and empty base URLs raise descriptive ValueError."""
    with pytest.raises(ValueError, match="Unsupported demo inspection state"):
        construct_demo_url("http://127.0.0.1:8080", "nonexistent_defect")

    with pytest.raises(ValueError, match="base_url cannot be empty"):
        construct_demo_url("   ", "clean")

    with pytest.raises(TypeError, match="State must be a string"):
        construct_demo_url("http://127.0.0.1:8080", 123)  # type: ignore


def test_structured_data_result_and_report_structures():
    """Verify DemoReachabilityResult and DemoInspectionReport data structures and accessors."""
    res = DemoReachabilityResult(
        state="clean",
        url="http://127.0.0.1:8080/?state=clean",
        reachable=True,
        status_code=200,
        error=None,
    )

    # Attribute access
    assert res.state == "clean"
    assert res.url == "http://127.0.0.1:8080/?state=clean"
    assert res.reachable is True
    assert res.is_reachable is True
    assert res.status_code == 200
    assert res.error is None

    # Dict-like access
    assert res["state"] == "clean"
    assert res["reachable"] is True
    assert res.get("status_code") == 200
    assert "url" in res

    # to_dict conversion
    res_dict = res.to_dict()
    assert res_dict["state"] == "clean"
    assert res_dict["reachable"] is True

    # Report container
    res_overflow = DemoReachabilityResult(
        state="overflow",
        url="http://127.0.0.1:8080/?defect=overflow",
        reachable=True,
        status_code=200,
    )
    report = DemoInspectionReport([res, res_overflow])

    assert len(report) == 2
    assert report.all_reachable is True
    assert report.states == ["clean", "overflow"]
    assert report["clean"].url == res.url
    assert report.get("overflow") == res_overflow
    assert report[0] == res

    # Report to_dict
    report_dict = report.to_dict()
    assert report_dict["all_reachable"] is True
    assert "clean" in report_dict["states"]


def test_live_demo_site_reachability_all_states(live_demo_server: str):
    """Verify live demo site reaches HTTP 200 across all 5 inspection states."""
    report = validate_demo_reachability(live_demo_server)

    assert len(report) == 5
    assert report.all_reachable is True
    assert report.states == ["clean", "overflow", "missing", "image", "all"]

    for item in report:
        assert item.reachable is True, f"State '{item.state}' was not reachable"
        assert item.status_code == 200
        assert item.error is None
        assert live_demo_server in item.url

    # Check specific query params on returned items
    assert "?state=clean" in report["clean"].url
    assert "?defect=overflow" in report["overflow"].url
    assert "?defect=missing" in report["missing"].url
    assert "?defect=image" in report["image"].url
    assert "?defects=all" in report["all"].url


def test_live_demo_site_reachability_single_state(live_demo_server: str):
    """Verify validate_demo_state against live server for a single state."""
    single_res = validate_demo_state(live_demo_server, "missing")

    assert isinstance(single_res, DemoReachabilityResult)
    assert single_res.state == "missing"
    assert single_res.reachable is True
    assert single_res.status_code == 200
    assert "?defect=missing" in single_res.url


def test_alias_validate_demo_site_works_identically(live_demo_server: str):
    """Verify the validate_demo_site alias functions identically."""
    report = validate_demo_site(live_demo_server, states=["clean", "all"])
    assert len(report) == 2
    assert report.all_reachable is True
    assert report.states == ["clean", "all"]


def test_unreachable_target_reports_structured_failure():
    """Verify reachability gracefully captures failure without crashing on closed port."""
    # Find an unused port that is definitely closed
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        closed_port = s.getsockname()[1]
    # socket is now closed

    unreachable_url = f"http://127.0.0.1:{closed_port}"
    report = validate_demo_reachability(unreachable_url, states=["clean", "overflow"], timeout=1.0)

    assert len(report) == 2
    assert report.all_reachable is False

    for item in report:
        assert item.reachable is False
        assert item.status_code is None
        assert item.error is not None
        assert len(item.error) > 0
