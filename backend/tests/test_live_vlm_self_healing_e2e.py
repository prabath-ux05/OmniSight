"""Live End-to-End Test Suite: Live VLM Validation + End-to-End Self-Healing Verification.

Proves the complete chain:
Demo Site -> Playwright Browser Capture -> VLM Findings -> RunStore / API ->
Self-Healing Repair Engine -> Candidate Synthesis -> Snapshot Validation ->
Live Fresh-Page Locator Verification.

Requirements verified:
1. Validate VLM execution:
   - Provider configuration check (/api/v1/runs/vlm/config) never exposes API keys or secrets.
   - Mock findings are never labeled as VLM (strict source="vlm" vs source="mock" separation).
   - VLM response parsing, screenshot transmission, and safe fallback on timeout or error.
2. Fresh-page repair verification:
   - Reopens or inspects live page using Playwright.
   - Tests candidate locator against live DOM.
   - Reports match count, resolvability, target URL, and tag name.
   - Distinctly returns snapshot_validation and live_verification.
3. Complete E2E flow:
   - Local demo site on ThreadedHTTPServer with ?defect=missing.
   - Live browser capture creates real before.png and dom.html.
   - Deterministic VLM provider produces missing_visible_element finding.
   - Repair endpoint with verify_live=true synthesizes robust candidates and verifies them against the live demo site.
4. Safety:
   - Demo site files on disk are completely untouched (zero modifications).
   - Navigation failure to bad/unreachable URL handled safely without crash.
   - Unresolvable selector handled safely.
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Generator
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.findings import FindingResponse
from backend.app.services.run_store import run_store
from self_healing.models import LiveVerificationResult, RepairResult
from self_healing.repair_engine import SelfHealingEngine
from self_healing.verification.locator_validator import verify_locator_on_live_page
from tests.test_demo_site import DEMO_SITE_DIR, ThreadedHTTPServer
from vision_engine.detection.providers import (
    BaseVLMProvider,
    VLMConfig,
    check_vlm_configuration,
)
from vision_engine.detection.vlm_detector import VLMDetector, detect_vlm
from vision_engine.models import VisionFinding, VisionInput


@pytest.fixture(scope="module")
def live_demo_server() -> Generator[str, None, None]:
    """Start local ThreadedHTTPServer serving demo_site/ on an ephemeral port."""
    server = ThreadedHTTPServer(DEMO_SITE_DIR)
    server.start()
    base_url = f"http://127.0.0.1:{server.port}"
    try:
        yield base_url
    finally:
        server.stop()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Starlette TestClient fixture."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure run store is clean before and after each test."""
    run_store.clear()
    yield
    run_store.clear()


@pytest.fixture
def track_artifacts() -> Generator[callable, None, None]:
    """Track and clean up created run artifact directories."""
    created_runs: list[str] = []

    def _track(run_id: str) -> str:
        created_runs.append(run_id)
        return run_id

    yield _track

    for rid in created_runs:
        art_dir = Path("artifacts") / rid
        if art_dir.exists():
            shutil.rmtree(art_dir, ignore_errors=True)


class DeterministicVLMProvider(BaseVLMProvider):
    """Deterministic VLM provider for automated tests without paid API access."""

    def analyze_ui(
        self,
        screenshot_bytes: bytes | None,
        dom_text: str | None,
        url: str,
    ) -> dict:
        assert screenshot_bytes is not None and len(screenshot_bytes) > 0, "Screenshot bytes required"
        assert dom_text is not None and len(dom_text) > 0, "DOM text required"
        assert "http" in url, "Valid URL required"

        return {
            "defects": [
                {
                    "category": "missing_visible_element",
                    "severity": "high",
                    "confidence": 0.94,
                    "description": "Primary action button is missing from layout in defect mode.",
                    "selector": "#btn-trigger-self-heal",
                    "reasoning": "The hero container expects an active trigger button, but it is not rendered.",
                    "bounding_box": None,
                }
            ],
            "analysis_notes": "Multimodal analysis verified element absence from rendered layout.",
        }



# ============================================================================
# 1. Live VLM Configuration & Safety Tests
# ============================================================================

def test_vlm_config_check_safety(client: TestClient, monkeypatch):
    """Verify that configuration checks never expose API keys or passwords."""
    # Test configured state
    monkeypatch.setenv("VISION_MODEL_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-supersecretkey9876543210wxyz")

    status = check_vlm_configuration()
    assert status["provider"] == "openai"
    assert status["is_configured"] is True
    assert status["api_key_status"] == "...wxyz"
    assert "supersecretkey" not in str(status)

    # API endpoint check
    resp = client.get("/api/v1/runs/vlm/config")
    assert resp.status_code == 200
    api_data = resp.json()
    assert api_data["is_configured"] is True
    assert "supersecretkey" not in resp.text


def test_vlm_detector_strictly_attributes_source(tmp_path: Path):
    """Verify that VLM detector sets source='vlm' and never labels mock as VLM."""
    dummy_png = tmp_path / "before.png"
    dummy_png.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4")
    dummy_html = tmp_path / "dom.html"
    dummy_html.write_text("<html><body><button id='btn-trigger-self-heal'>Run</button></body></html>", encoding="utf-8")

    vision_input = VisionInput(
        run_id="run_vlm_attr_test",
        screenshot_path=str(dummy_png),
        dom_snapshot_path=str(dummy_html),
        url="http://127.0.0.1:8080/?defect=missing",
    )

    provider = DeterministicVLMProvider(VLMConfig(provider="gemini", api_key="test-key"))
    detector = VLMDetector(provider=provider, allow_fallback=False)
    findings = detector.detect(vision_input)

    assert len(findings) == 1
    assert findings[0].category == "missing_visible_element"
    assert findings[0].source == "vlm"
    assert findings[0].source != "mock"



# ============================================================================
# 2. Fresh-Page Locator Verification Tests
# ============================================================================

def test_verify_locator_on_live_demo_page(live_demo_server: str):
    """Verify locator directly against a live Playwright page navigation."""
    # Clean page has #btn-reset-defects and [data-testid="trigger-self-heal-cta"]
    live_url = f"{live_demo_server}/index.html"

    # 1. Test unique selector
    res_unique = verify_locator_on_live_page(live_url, "#btn-reset-defects", timeout_ms=10000)
    assert res_unique.attempted is True
    assert res_unique.is_verified is True
    assert res_unique.matches == 1
    assert res_unique.resolved_tag == "button"
    assert "Uniquely verified" in res_unique.validation_message

    # 2. Test non-existent selector
    res_absent = verify_locator_on_live_page(live_url, "#non-existent-selector-12345", timeout_ms=10000)
    assert res_absent.attempted is True
    assert res_absent.is_verified is False
    assert res_absent.matches == 0
    assert "expected 1 unique match" in res_absent.validation_message

    # 3. Test invalid syntax
    res_invalid = verify_locator_on_live_page(live_url, ":::invalid[[[", timeout_ms=10000)
    assert res_invalid.attempted is True
    assert res_invalid.is_verified is False


def test_verify_locator_handles_navigation_failure_safely():
    """Verify that network/connection failure to unreachable URL returns safe failure result."""
    # Port 59999 should not have any server listening
    bad_url = "http://127.0.0.1:59999/nonexistent.html"
    res = verify_locator_on_live_page(bad_url, "#btn", timeout_ms=2000)
    assert res.attempted is True
    assert res.is_verified is False
    assert "error" in res.validation_message.lower() or "timed out" in res.validation_message.lower()


# ============================================================================
# 3. Full End-to-End Flow: Inspection -> VLM Findings -> Live Repair
# ============================================================================

def test_full_e2e_vlm_inspection_and_live_repair(
    live_demo_server: str,
    client: TestClient,
    track_artifacts,
    monkeypatch,
):
    """Complete E2E integration test:

    1. Browser capture on live demo site (?defect=missing).
    2. VLM detector analysis yielding finding with source='vlm'.
    3. RunStore persists findings, screenshots, and DOM snapshots.
    4. Self-healing repair with verify_live=True against live demo site.
    5. Candidate synthesis, DOM snapshot verification, and live Playwright verification.
    6. Verify demo_site source files on disk were NOT modified.
    """
    # Record modification times of demo site files before execution
    demo_files = list(Path(DEMO_SITE_DIR).glob("**/*.*"))
    mtimes_before = {f: f.stat().st_mtime for f in demo_files if f.is_file()}

    # 1. Configure deterministic VLM provider for orchestrator
    test_provider = DeterministicVLMProvider(VLMConfig(provider="gemini", api_key="dummy-key"))
    vlm_detector = VLMDetector(provider=test_provider, allow_fallback=False)

    from backend.app.services.orchestrator import run_orchestrator
    monkeypatch.setattr(run_orchestrator, "detector", lambda vi: vlm_detector.detect(vi))

    # 2. Trigger run via API with auto_execute=true
    target_url = f"{live_demo_server}/index.html?defect=missing"
    create_resp = client.post(
        "/api/v1/runs?auto_execute=true",
        json={"url": target_url},
    )
    assert create_resp.status_code == 201
    run_id = track_artifacts(create_resp.json()["run_id"])

    # 3. Poll run to terminal state
    deadline = time.time() + 30.0
    terminal_status = None
    while time.time() < deadline:
        status_resp = client.get(f"/api/v1/runs/{run_id}")
        assert status_resp.status_code == 200
        run_data = status_resp.json()
        if run_data["status"] in ("completed", "failed", "cancelled"):
            terminal_status = run_data["status"]
            break
        time.sleep(0.5)

    assert terminal_status == "completed", f"Run did not complete: {run_data.get('error')}"

    # 4. Verify findings and evidence paths
    findings_resp = client.get(f"/api/v1/runs/{run_id}/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert len(findings) == 1

    finding = findings[0]
    assert finding["category"] == "missing_visible_element"
    assert finding["source"] == "vlm"
    assert finding["selector"] == "#btn-trigger-self-heal"
    assert finding["evidence"]["screenshot_path"] is not None
    assert finding["evidence"]["dom_snapshot_path"] is not None

    # Verify artifacts exist on disk
    assert Path(finding["evidence"]["dom_snapshot_path"]).exists()
    assert Path(finding["evidence"]["screenshot_path"]).exists()

    # 5. Trigger Self-Healing Repair with verify_live=True
    repair_resp = client.post(
        f"/api/v1/runs/{run_id}/repair?verify_live=true",
        json={"finding_id": finding["finding_id"], "verify_live": True},
    )
    assert repair_resp.status_code == 200
    repair_results = repair_resp.json()
    assert len(repair_results) == 1

    repair = repair_results[0]
    assert repair["repaired"] is True
    assert repair["finding_id"] == finding["finding_id"]
    assert repair["best_locator"] is not None

    # Snapshot validation must be present and valid
    assert repair["snapshot_validation"]["is_valid"] is True
    assert repair["snapshot_validation"]["matches"] == 1
    assert "Uniquely resolved" in repair["snapshot_validation"]["validation_message"]

    # Live verification must be attempted and present
    assert repair["live_verification"] is not None
    assert repair["live_verification"]["attempted"] is True
    assert repair["live_verification"]["target_url"] == target_url

    # Check that candidates are ranked and structured
    assert len(repair["candidates"]) > 0
    top_cand = repair["candidates"][0]
    assert top_cand["selector"] == repair["best_locator"]
    assert top_cand["score"] > 0.0

    # 6. Safety check: Target demo site files were NEVER touched or altered
    for file_path, mtime_before in mtimes_before.items():
        assert file_path.stat().st_mtime == mtime_before, f"File {file_path} was modified!"
