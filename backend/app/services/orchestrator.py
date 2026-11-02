"""Orchestration service coordinating Browser Agent capture and Vision Engine analysis."""

from pathlib import Path
from backend.app.core.logging import logger
from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from backend.app.services.run_store import run_store


class RunOrchestrator:
    """Manages the full automated lifecycle of an OmniSight inspection run."""

    def execute_run(self, run_id: str, url: str) -> None:
        """Execute browser evidence capture and vision inspection for a run.

        Transitions run through lifecycle states:
          queued -> capturing -> analyzing -> completed (or failed).
        """
        logger.info("Starting orchestration for run %s (URL: %s)", run_id, url)

        # Pre-flight check: verify run exists in storage
        existing_run = run_store.get(run_id)
        if not existing_run:
            logger.error("Orchestrator cannot execute: run '%s' not found in store.", run_id)
            return

        # Pre-flight URL sanity check
        clean_url = (url or "").strip()
        if not clean_url.startswith(("http://", "https://")):
            logger.warning("Orchestrator rejected invalid URL for run %s: %r", run_id, url)
            run_store.update_run(
                run_id,
                status="failed",
                error=f"Invalid URL: '{url}'. Must begin with http:// or https://",
                message="Inspection failed: invalid target URL scheme.",
            )
            return

        # ---------------------------------------------------------------------
        # Stage 1: Browser Navigation & Evidence Capture (Janvi's module)
        # ---------------------------------------------------------------------
        run_store.update_run(
            run_id,
            status="capturing",
            message="Browser Agent launching Chromium and capturing evidence...",
            error=None,
        )

        try:
            from navigation.navigator import BrowserNavigator

            navigator = BrowserNavigator(timeout_ms=15000, headless=True)
            nav_result = navigator.navigate(url=clean_url, run_id=run_id)
        except Exception as exc:
            error_msg = f"Browser Agent failure: {str(exc)}"
            logger.error("Run %s failed during browser capture: %s", run_id, error_msg)
            run_store.update_run(
                run_id,
                status="failed",
                error=error_msg,
                message="Browser Agent encountered an unexpected error.",
            )
            return

        if nav_result.status != "success":
            logger.warning("Browser navigation failed for run %s: %s", run_id, nav_result.error)
            run_store.update_run(
                run_id,
                status="failed",
                error=nav_result.error or "Browser navigation failed.",
                message="Browser Agent failed to navigate to the target URL.",
            )
            return

        # Record generated evidence artifacts in database
        if nav_result.screenshot_path and Path(nav_result.screenshot_path).is_file():
            try:
                run_store.record_artifact(
                    run_id=run_id,
                    artifact_type="screenshot",
                    storage_path=nav_result.screenshot_path,
                    content_type="image/png",
                )
            except Exception as art_err:
                logger.warning("Could not persist screenshot artifact record: %s", str(art_err))

        if nav_result.dom_snapshot_path and Path(nav_result.dom_snapshot_path).is_file():
            try:
                run_store.record_artifact(
                    run_id=run_id,
                    artifact_type="dom_snapshot",
                    storage_path=nav_result.dom_snapshot_path,
                    content_type="text/html",
                )
            except Exception as art_err:
                logger.warning("Could not persist DOM snapshot artifact record: %s", str(art_err))

        # ---------------------------------------------------------------------
        # Stage 2: Vision & Intelligence Analysis (Jay's module)
        # ---------------------------------------------------------------------
        run_store.update_run(
            run_id,
            status="analyzing",
            message="Vision Engine analyzing captured visual and DOM evidence...",
            error=None,
        )

        try:
            from vision_engine.detection.dom_detector import detect_dom_issues
            from vision_engine.models import VisionInput

            # Normalize paths for Vision Engine input
            screenshot_path = (
                str(Path(nav_result.screenshot_path).as_posix())
                if nav_result.screenshot_path
                else None
            )
            dom_snapshot_path = (
                str(Path(nav_result.dom_snapshot_path).as_posix())
                if nav_result.dom_snapshot_path
                else None
            )

            # At least one evidence file must exist for Vision Engine
            if not screenshot_path and not dom_snapshot_path:
                logger.warning("Run %s produced no screenshot or DOM evidence.", run_id)
                run_store.update_run(
                    run_id,
                    status="failed",
                    error="No evidence files were generated by the Browser Agent.",
                    message="Vision analysis aborted: missing evidence files.",
                )
                return

            vision_input = VisionInput(
                run_id=run_id,
                url=clean_url,
                screenshot_path=screenshot_path,
                dom_snapshot_path=dom_snapshot_path,
            )

            # Analyze real DOM snapshot if captured by Browser Agent
            if dom_snapshot_path and Path(dom_snapshot_path).is_file():
                vision_findings = detect_dom_issues(vision_input)
            else:
                logger.info("No DOM snapshot file on disk for run %s; skipping DOM heuristic.", run_id)
                vision_findings = []

            # Map Vision Engine findings to backend FindingResponse contract
            mapped_findings = [
                FindingResponse(
                    finding_id=f.finding_id,
                    category=f.category,
                    severity=f.severity,
                    confidence=f.confidence,
                    description=f.description,
                    selector=f.selector,
                    evidence=EvidenceReferences(
                        screenshot_path=f.evidence.screenshot_path,
                        dom_snapshot_path=f.evidence.dom_snapshot_path,
                    ),
                    source=f.source,
                )
                for f in vision_findings
            ]

            run_store.set_findings(run_id, mapped_findings)

        except Exception as exc:
            error_msg = f"Vision Engine analysis error: {str(exc)}"
            logger.error("Run %s failed during vision analysis: %s", run_id, error_msg)
            run_store.update_run(
                run_id,
                status="failed",
                error=error_msg,
                message="Vision Engine failed during evidence analysis.",
            )
            return

        # ---------------------------------------------------------------------
        # Stage 3: Completion
        # ---------------------------------------------------------------------
        logger.info(
            "Run %s completed successfully with %d finding(s).",
            run_id,
            len(mapped_findings),
        )
        run_store.update_run(
            run_id,
            status="completed",
            message=f"Inspection complete. {len(mapped_findings)} finding(s) detected.",
            error=None,
        )


run_orchestrator = RunOrchestrator()
