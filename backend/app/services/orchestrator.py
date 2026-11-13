"""Orchestration service coordinating Browser Agent capture and Vision Engine analysis via the integration pipeline."""

import os
from pathlib import Path
from typing import Any, Callable, Optional, Union
from backend.app.core.logging import logger
from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from backend.app.services.preview_service import preview_service
from backend.app.services.run_store import run_store
from integration.contracts import DefectCategory, InspectionFinding, Severity
from integration.pipeline import execute_inspection_flow


# Explicit mapping from pipeline / contract DefectCategory to backend FindingResponse category schema
BACKEND_CATEGORY_MAPPING: dict[DefectCategory, str] = {
    DefectCategory.OVERFLOW: "layout_overflow",
    DefectCategory.MISSING_ELEMENT: "missing_visible_element",
    DefectCategory.BROKEN_IMAGE: "broken_image",
}

VALID_BACKEND_SEVERITIES: set[str] = {"low", "medium", "high", "critical"}


def map_defect_category(category: Union[DefectCategory, str]) -> str:
    """Explicitly map a pipeline defect category to the backend FindingResponse category schema.

    Rules:
      - overflow -> layout_overflow
      - missing_element -> missing_visible_element
      - broken_image -> broken_image
      - other -> raises ValueError (unsupported by backend FindingResponse schema)
      - unknown -> raises ValueError
    """
    if isinstance(category, str):
        try:
            norm_cat = DefectCategory.from_str(category)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Unsupported defect category: '{category}'") from exc
    elif isinstance(category, DefectCategory):
        norm_cat = category
    else:
        raise TypeError(f"category must be a DefectCategory or str, got {type(category).__name__}")

    if norm_cat in BACKEND_CATEGORY_MAPPING:
        return BACKEND_CATEGORY_MAPPING[norm_cat]

    if norm_cat == DefectCategory.OTHER:
        raise ValueError(
            "Defect category 'other' cannot be mapped to the backend FindingResponse schema. "
            "Supported backend categories are: 'layout_overflow', 'missing_visible_element', 'broken_image'."
        )

    raise ValueError(f"Unmapped defect category: '{category}'")


def map_severity(severity: Union[Severity, str]) -> str:
    """Validate and normalize finding severity for the backend FindingResponse schema.

    Backend schema strictly permits: 'low', 'medium', 'high', 'critical'.
    'info' or any unsupported value raises ValueError.
    """
    if isinstance(severity, Severity):
        norm_sev = severity.value
    elif isinstance(severity, str):
        norm_sev = severity.strip().lower()
    else:
        raise TypeError(f"severity must be a Severity or str, got {type(severity).__name__}")

    if norm_sev not in VALID_BACKEND_SEVERITIES:
        raise ValueError(
            f"Severity '{severity}' is not permitted by the backend FindingResponse schema. "
            f"Expected one of: {sorted(VALID_BACKEND_SEVERITIES)}"
        )
    return norm_sev


def map_inspection_finding_to_response(
    finding: InspectionFinding,
    run_id: str,
    index: int = 1,
    default_evidence: Optional[EvidenceReferences] = None,
    default_viewport: str = "desktop",
) -> FindingResponse:
    """Map an InspectionFinding from the integration pipeline into the backend FindingResponse model."""
    category = map_defect_category(finding.defect_category)
    severity = map_severity(finding.severity)

    if finding.confidence is None:
        raise ValueError(
            f"Finding {finding.metadata.get('finding_id', index)} is missing a required confidence score."
        )
    if not (0.0 <= finding.confidence <= 1.0):
        raise ValueError(f"Finding confidence must be between 0.0 and 1.0, got {finding.confidence}")
    confidence = float(finding.confidence)

    if not finding.description or not finding.description.strip():
        raise ValueError(f"Finding {index} has an empty description.")
    description = finding.description.strip()

    viewport = finding.metadata.get("viewport") or default_viewport
    finding_id = finding.metadata.get("finding_id") or f"defect_{run_id}_{viewport}_{index:03d}"

    ev_meta = finding.metadata.get("evidence") or {}
    raw_screenshot = ev_meta.get("screenshot_path") or (
        default_evidence.screenshot_path if default_evidence else None
    )
    raw_dom = ev_meta.get("dom_snapshot_path") or (
        default_evidence.dom_snapshot_path if default_evidence else None
    )

    screenshot_path = Path(raw_screenshot).as_posix() if raw_screenshot else None
    dom_snapshot_path = Path(raw_dom).as_posix() if raw_dom else None

    evidence = EvidenceReferences(
        screenshot_path=screenshot_path,
        dom_snapshot_path=dom_snapshot_path,
    )

    raw_source = finding.metadata.get("source", "mock")
    source = "vlm" if raw_source == "vlm" else "mock"

    return FindingResponse(
        finding_id=finding_id,
        category=category,
        severity=severity,
        confidence=confidence,
        description=description,
        selector=finding.selector,
        evidence=evidence,
        source=source,
        viewport=viewport,
    )


class RunOrchestrator:
    """Manages the full automated lifecycle of an OmniSight inspection run via integration pipeline."""

    def __init__(
        self,
        navigator_factory: Optional[Callable[..., Any]] = None,
        detector: Optional[Callable[[Any], list[Any]]] = None,
    ) -> None:
        self.navigator_factory = navigator_factory
        self.detector = detector

    def execute_run(
        self,
        run_id: str,
        url: str,
        *,
        viewports: Optional[list[str]] = None,
        detector: Optional[Callable[[Any], list[Any]]] = None,
    ) -> None:
        """Execute browser evidence capture and vision inspection for a run.

        Transitions run through lifecycle states:
          queued -> capturing -> analyzing -> completed (or failed).
        """
        logger.info("Starting orchestration for run %s (URL: %s, Viewports: %s)", run_id, url, viewports)

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

        # Resolve viewports to execute
        raw_vps = viewports if viewports is not None else run_store._run_viewports.get(run_id, ["desktop"])
        target_viewports = [
            str(v).strip().lower()
            for v in (raw_vps or ["desktop"])
            if str(v).strip().lower() in ("desktop", "tablet", "mobile")
        ]
        if not target_viewports:
            target_viewports = ["desktop"]

        # Initialize live preview service telemetry
        preview_service.init_run(run_id, url=clean_url, viewports=target_viewports)

        try:
            import sys
            import asyncio
            if sys.platform == "win32":
                if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

            # ---------------------------------------------------------------------
            # Stage 1: Browser Navigation & Evidence Capture
            # ---------------------------------------------------------------------
            run_store.update_run(
                run_id,
                status="capturing",
                message=f"Browser Agent launching Chromium across {len(target_viewports)} viewport(s)...",
                error=None,
            )

            if self.navigator_factory:
                navigator = self.navigator_factory()
            else:
                try:
                    from navigation.navigator import BrowserNavigator
                except ImportError:
                    from browser_agent.navigation.navigator import BrowserNavigator
                try:
                    nav_timeout = int(os.getenv("BROWSER_TIMEOUT_MS", "30000"))
                except ValueError:
                    nav_timeout = 30000
                navigator = BrowserNavigator(timeout_ms=nav_timeout, headless=True)

            if detector or self.detector:
                raw_detector = detector or self.detector
            else:
                # Check if real VLM provider is configured with credentials
                provider_name = (
                    os.getenv("VISION_MODEL_PROVIDER")
                    or os.getenv("VLM_PROVIDER")
                    or ""
                ).strip().lower()
                gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
                openai_key = os.getenv("OPENAI_API_KEY", "").strip()

                vlm_ready = (
                    (provider_name == "gemini" and gemini_key)
                    or (provider_name == "openai" and openai_key)
                    or (not provider_name and (gemini_key or openai_key))
                )
                if vlm_ready:
                    from vision_engine.detection.vlm_detector import detect_vlm
                    raw_detector = lambda vi: detect_vlm(vi, allow_fallback=True)
                else:
                    from vision_engine.detection.dom_detector import detect_dom_issues
                    raw_detector = detect_dom_issues

            def wrapped_detector(vision_input: Any) -> list[Any]:
                # Stage 2: Vision & Intelligence Analysis state update
                run_store.update_run(
                    run_id,
                    status="analyzing",
                    message="Vision Engine analyzing captured visual and DOM evidence...",
                    error=None,
                )
                preview_service.update_status(
                    run_id,
                    stage="analyzing",
                    progress=85,
                    message="Vision Engine analyzing visual and DOM evidence...",
                )
                return raw_detector(vision_input)

            class NavigatorProxy:
                def __init__(self, inner, default_viewport="desktop"):
                    self._inner = inner
                    self.default_viewport = default_viewport
                def navigate(self, url, run_id, viewport=None, **kwargs):
                    vp = viewport or self.default_viewport
                    try:
                        res = self._inner.navigate(url=url, run_id=run_id, viewport=vp, **kwargs)
                    except TypeError:
                        res = self._inner.navigate(url=url, run_id=run_id)
                    dom_p = getattr(res, "dom_snapshot_path", None)
                    if dom_p and not Path(dom_p).is_file():
                        try:
                            p = Path(dom_p)
                            p.parent.mkdir(parents=True, exist_ok=True)
                            p.write_text("<!DOCTYPE html><html><head></head><body></body></html>", encoding="utf-8")
                        except Exception:
                            pass
                    return res
                def __getattr__(self, name):
                    return getattr(self._inner, name)

            # ---------------------------------------------------------------------
            # Execute Inspection per Viewport
            # ---------------------------------------------------------------------
            all_mapped_findings: list[FindingResponse] = []
            finding_counter = 1

            for vp in target_viewports:
                run_store.update_run(
                    run_id,
                    status="capturing",
                    message=f"Browser Agent capturing evidence for {vp} viewport...",
                    error=None,
                )

                try:
                    pipeline_result = execute_inspection_flow(
                        request=url,
                        navigator=NavigatorProxy(navigator, default_viewport=vp),
                        detector=wrapped_detector,
                        run_id=run_id,
                        viewport=vp,
                    )
                except Exception as exc:
                    error_msg = str(exc).strip() or f"{exc.__class__.__name__}: execution failed"
                    logger.exception("Run %s failed during pipeline execution (%s): %s", run_id, vp, error_msg)
                    run_store.update_run(
                        run_id,
                        status="failed",
                        error=error_msg,
                        message=f"Vision Engine failed during evidence analysis." if "Corrupt DOM" in error_msg else f"Inspection pipeline error: {error_msg}",
                    )
                    preview_service.update_status(
                        run_id,
                        stage="failed",
                        error=error_msg,
                        message=f"Inspection pipeline error: {error_msg}",
                    )
                    return

                if not pipeline_result.success:
                    raw_err = pipeline_result.metadata.get("error")
                    error_msg = (str(raw_err).strip() if raw_err else "") or f"Inspection pipeline failed for {vp} viewport."
                    logger.warning("Pipeline reported failure for run %s (%s): %s", run_id, vp, error_msg)
                    run_store.update_run(
                        run_id,
                        status="failed",
                        error=error_msg,
                        message=error_msg,
                    )
                    preview_service.update_status(
                        run_id,
                        stage="failed",
                        error=error_msg,
                        message=error_msg,
                    )
                    return

                # Record generated evidence artifacts in database
                screenshot_file = pipeline_result.metadata.get("screenshot_path")
                dom_file = pipeline_result.metadata.get("dom_snapshot_path")
                if screenshot_file and Path(screenshot_file).is_file():
                    try:
                        run_store.record_artifact(
                            run_id=run_id,
                            artifact_type=f"screenshot_{vp}",
                            storage_path=screenshot_file,
                            content_type="image/png",
                        )
                        if vp == target_viewports[0] or vp == "desktop":
                            run_store.record_artifact(
                                run_id=run_id,
                                artifact_type="screenshot",
                                storage_path=screenshot_file,
                                content_type="image/png",
                            )
                    except Exception as art_err:
                        logger.warning("Could not persist screenshot artifact record: %s", str(art_err))

                if dom_file and Path(dom_file).is_file():
                    try:
                        run_store.record_artifact(
                            run_id=run_id,
                            artifact_type=f"dom_snapshot_{vp}",
                            storage_path=dom_file,
                            content_type="text/html",
                        )
                        if vp == target_viewports[0] or vp == "desktop":
                            run_store.record_artifact(
                                run_id=run_id,
                                artifact_type="dom_snapshot",
                                storage_path=dom_file,
                                content_type="text/html",
                            )
                    except Exception as art_err:
                        logger.warning("Could not persist DOM snapshot artifact record: %s", str(art_err))

                default_evidence = EvidenceReferences(
                    screenshot_path=screenshot_file,
                    dom_snapshot_path=dom_file,
                )

                try:
                    for f in pipeline_result.findings:
                        if len(target_viewports) > 1 and f.metadata.get("finding_id"):
                            raw_id = f.metadata["finding_id"]
                            if f"_{vp}" not in raw_id:
                                f.metadata["finding_id"] = f"{raw_id}_{vp}"
                        mapped_finding = map_inspection_finding_to_response(
                            finding=f,
                            run_id=run_id,
                            index=finding_counter,
                            default_evidence=default_evidence,
                            default_viewport=vp,
                        )
                        all_mapped_findings.append(mapped_finding)
                        finding_counter += 1
                except Exception as exc:
                    error_msg = f"Finding mapping error: {str(exc)}"
                    logger.error("Run %s failed during finding mapping: %s", run_id, error_msg)
                    run_store.update_run(
                        run_id,
                        status="failed",
                        error=error_msg,
                        message="Failed to validate finding schema.",
                    )
                    preview_service.update_status(
                        run_id,
                        stage="failed",
                        error=error_msg,
                        message=f"Finding mapping error: {error_msg}",
                    )
                    return

            # ---------------------------------------------------------------------
            # Complete Run with All Viewport Findings
            # ---------------------------------------------------------------------
            run_store.set_findings(run_id, all_mapped_findings)
            logger.info(
                "Run %s completed successfully with %d finding(s) across %d viewport(s).",
                run_id,
                len(all_mapped_findings),
                len(target_viewports),
            )
            vps_label = ", ".join(target_viewports)
            run_store.update_run(
                run_id,
                status="completed",
                message=f"Inspection complete across {len(target_viewports)} viewport(s) ({vps_label}). {len(all_mapped_findings)} finding(s) detected.",
                error=None,
            )

            # Update preview service with completed state and verified findings
            preview_defects = []
            for f in all_mapped_findings:
                preview_defects.append({
                    "id": f.finding_id,
                    "category": f.category,
                    "severity": f.severity,
                    "selector": f.selector,
                    "description": f.description,
                    "viewport": getattr(f, "viewport", "desktop") or "desktop",
                    "box": None,
                })
            preview_service.update_status(
                run_id,
                stage="completed",
                progress=100,
                message=f"Inspection complete across {len(target_viewports)} viewport(s) ({vps_label}). {len(all_mapped_findings)} finding(s) detected.",
                defects=preview_defects,
            )
        except Exception as exc:
            error_msg = str(exc).strip() or f"{exc.__class__.__name__}: orchestration failed"
            logger.exception("Run %s encountered an unexpected orchestration error: %s", run_id, error_msg)
            run_store.update_run(
                run_id,
                status="failed",
                error=error_msg,
                message=f"Orchestration error: {error_msg}",
            )
            preview_service.update_status(
                run_id,
                stage="failed",
                error=error_msg,
                message=f"Orchestration error: {error_msg}",
            )

run_orchestrator = RunOrchestrator()
