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
            nav_result = navigator.navigate(url=url, run_id=run_id)
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

            vision_input = VisionInput(
                run_id=run_id,
                url=url,
                screenshot_path=screenshot_path,
                dom_snapshot_path=dom_snapshot_path,
            )

            # Analyze real DOM snapshot captured by Browser Agent
            vision_findings = detect_dom_issues(vision_input)

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
