"""Focused test suite for OmniSight Demo Site (Controlled SUT).

Verifies file presence, HTML structure, stable selectors, CSS defect rules,
JavaScript defect harness logic, and HTTP server delivery.
"""

import http.server
import socketserver
import threading
import urllib.request
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
DEMO_SITE_DIR = REPO_ROOT / "demo_site"


def test_demo_site_files_exist():
    """Ensure all core files and assets for the demo site exist."""
    required_files = [
        DEMO_SITE_DIR / "index.html",
        DEMO_SITE_DIR / "css" / "styles.css",
        DEMO_SITE_DIR / "js" / "defects.js",
        DEMO_SITE_DIR / "js" / "app.js",
        DEMO_SITE_DIR / "assets" / "images" / "logo.svg",
        DEMO_SITE_DIR / "assets" / "images" / "system-topology.svg",
        DEMO_SITE_DIR / "assets" / "images" / "avatar.svg",
        DEMO_SITE_DIR / "README.md",
    ]
    for file_path in required_files:
        assert file_path.exists(), f"Missing required demo site file: {file_path}"
        assert file_path.stat().st_size > 0, f"File is empty: {file_path}"


def test_html_contains_critical_stable_ids():
    """Ensure index.html contains all stable IDs and selectors for automation agents."""
    html_content = (DEMO_SITE_DIR / "index.html").read_text(encoding="utf-8")

    required_ids = [
        "defect-control-dock",
        "toggle-defect-overflow",
        "toggle-defect-missing-element",
        "toggle-defect-broken-image",
        "btn-reset-defects",
        "btn-inject-all-defects",
        "header-navbar",
        "sidebar-nav",
        "main-content-panel",
        "btn-trigger-self-heal",
        "btn-export-telemetry",
        "card-active-jobs",
        "metric-active-jobs-subtext",
        "card-healing-rate",
        "card-avg-latency",
        "card-test-flakiness",
        "service-topology-card",
        "service-topology-image",
        "workflow-runs-table",
    ]

    for element_id in required_ids:
        assert f'id="{element_id}"' in html_content, f"Missing required ID #{element_id} in index.html"


def test_html_data_attributes_for_defects():
    """Ensure index.html has baseline defect state attributes on body."""
    html_content = (DEMO_SITE_DIR / "index.html").read_text(encoding="utf-8")
    assert 'data-defect-overflow="false"' in html_content
    assert 'data-defect-missing="false"' in html_content
    assert 'data-defect-broken-image="false"' in html_content


def test_css_defect_rules_defined():
    """Ensure styles.css has explicit styles for all three defect states."""
    css_content = (DEMO_SITE_DIR / "css" / "styles.css").read_text(encoding="utf-8")

    assert 'data-defect-overflow="true"' in css_content, "Missing CSS rule for layout overflow defect"
    assert 'data-defect-missing="true"' in css_content, "Missing CSS rule for missing visible element defect"
    assert 'data-defect-broken-image="true"' in css_content, "Missing CSS rule for broken image defect"


def test_defects_script_contains_deterministic_api():
    """Ensure defects.js defines the programmatic and URL parameter API."""
    js_content = (DEMO_SITE_DIR / "js" / "defects.js").read_text(encoding="utf-8")

    assert "window.OmniSightDefects" in js_content
    assert "applyDefectOverflow" in js_content
    assert "applyDefectMissingElement" in js_content
    assert "applyDefectBrokenImage" in js_content
    assert "resetAllDefects" in js_content
    assert "injectAllDefects" in js_content
    assert "parseUrlParameters" in js_content
    assert "omnisight:defect-change" in js_content


class ThreadedHTTPServer:
    """Helper to run a temporary Python HTTP server for integration testing."""
    def __init__(self, directory: Path):
        handler = lambda *args, **kwargs: http.server.SimpleHTTPRequestHandler(
            *args, directory=str(directory), **kwargs
        )
        self.server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def start(self):
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


def test_http_server_serves_demo_site():
    """Ensure the demo site can be served via standard HTTP and assets resolve."""
    test_server = ThreadedHTTPServer(DEMO_SITE_DIR)
    test_server.start()
    try:
        base_url = f"http://127.0.0.1:{test_server.port}"

        # 1. Root index.html
        with urllib.request.urlopen(f"{base_url}/") as response:
            assert response.status == 200
            content = response.read().decode("utf-8")
            assert "<!DOCTYPE html>" in content
            assert "NovaMetrics" in content

        # 2. CSS Stylesheet
        with urllib.request.urlopen(f"{base_url}/css/styles.css") as response:
            assert response.status == 200

        # 3. Defect JS script
        with urllib.request.urlopen(f"{base_url}/js/defects.js") as response:
            assert response.status == 200

        # 4. Topology SVG Image
        with urllib.request.urlopen(f"{base_url}/assets/images/system-topology.svg") as response:
            assert response.status == 200

        # 5. Broken image URL returns 404 as expected for defect testing
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(f"{base_url}/assets/images/non-existent-broken-diagram.png")
        assert exc_info.value.code == 404

    finally:
        test_server.stop()
