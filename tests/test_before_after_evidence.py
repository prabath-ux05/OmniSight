
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from screenshots.screenshot_manager import ScreenshotManager
from evidence.dom_capture import DOMCapture


def test_before_after_evidence_capture(local_url, tmp_path):
    run_id = "day5_integration_test"
    artifact_root = str(tmp_path)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()

        try:
            page.goto(local_url)

            # Capture BEFORE evidence
            before_screenshot = ScreenshotManager.save_screenshot(
                page, run_id, artifact_root, stage="before"
            )
            before_dom = DOMCapture.save_dom_snapshot(
                page, run_id, artifact_root, stage="before"
            )

            # Simulate a webpage change
            page.evaluate("""
                document.body.innerHTML +=
                    '<h2 id="day5-change">After Repair</h2>';
            """)

            # Capture AFTER evidence
            after_screenshot = ScreenshotManager.save_screenshot(
                page, run_id, artifact_root, stage="after"
            )
            after_dom = DOMCapture.save_dom_snapshot(
                page, run_id, artifact_root, stage="after"
            )

            run_dir = Path(artifact_root) / run_id

            expected_files = [
                "before.png",
                "before_metadata.json",
                "before_dom.html",
                "before_dom_metadata.json",
                "after.png",
                "after_metadata.json",
                "after_dom.html",
                "after_dom_metadata.json",
            ]

            # Check all eight files
            for filename in expected_files:
                file_path = run_dir / filename
                assert file_path.is_file(), filename
                assert file_path.stat().st_size > 0

            # Check file paths
            assert Path(before_screenshot).name == "before.png"
            assert Path(after_screenshot).name == "after.png"
            assert Path(before_dom).name == "before_dom.html"
            assert Path(after_dom).name == "after_dom.html"

            # Check metadata
            for filename, expected_stage in [
                ("before_metadata.json", "before"),
                ("after_metadata.json", "after"),
                ("before_dom_metadata.json", "before"),
                ("after_dom_metadata.json", "after"),
            ]:
                with open(run_dir / filename, encoding="utf-8") as file:
                    metadata = json.load(file)

                assert metadata["run_id"] == run_id
                assert metadata["stage"] == expected_stage

            # Check that the DOM change appears only after
            before_html = Path(before_dom).read_text(encoding="utf-8")
            after_html = Path(after_dom).read_text(encoding="utf-8")

            assert "day5-change" not in before_html
            assert "day5-change" in after_html

        finally:
            browser.close()
