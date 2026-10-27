"""Orchestration service coordinating Browser Agent capture and Vision Engine analysis via the integration pipeline."""

import os
from pathlib import Path
from typing import Any, Callable, Optional, Union
from backend.app.core.logging import logger
from backend.app.schemas.findings import EvidenceReferences, FindingResponse
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

    finding_id = finding.metadata.get("finding_id") or f"defect_{run_id}_{index:03d}"

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
        detector: Optional[Callable[[Any], list[Any]]] = None,
    ) -> None:
        """Execute browser evidence capture and vision inspection for a run.

        Transitions run through lifecycle states:
          queued -> capturing -> analyzing -> completed (or failed).
        """
        logger.info("Starting orchestration for run %s (URL: %s)", run_id, url)

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
                message="Browser Agent launching Chromium and capturing evidence...",
                error=None,
            )

            if self.navigator_factory:
                navigator = self.navigator_factory()
            else:
                try:
                    from navigation.navigator import BrowserNavigator
                except ImportError:
                    from browser_agent.navigation.navigator import BrowserNavigator
                navigator = BrowserNavigator(timeout_ms=15000, headless=True)

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
                return raw_detector(vision_input)

            # ---------------------------------------------------------------------
            # Execute Inspection via Integration Pipeline
            # ---------------------------------------------------------------------
            try:
                pipeline_result = execute_inspection_flow(
                    request=url,
                    navigator=navigator,
                    detector=wrapped_detector,
                    run_id=run_id,
                )
            except Exception as exc:
                error_msg = str(exc).strip() or f"{exc.__class__.__name__}: execution failed"
                logger.exception("Run %s failed during pipeline execution: %s", run_id, error_msg)
                run_store.update_run(
                    run_id,
                    status="failed",
                    error=error_msg,
                    message=f"Vision Engine failed during evidence analysis." if "Corrupt DOM" in error_msg else f"Inspection pipeline error: {error_msg}",
                )
                return

            if not pipeline_result.success:
                raw_err = pipeline_result.metadata.get("error")
                error_msg = (str(raw_err).strip() if raw_err else "") or "Inspection pipeline failed."
                logger.warning("Pipeline reported failure for run %s: %s", run_id, error_msg)
                run_store.update_run(
                    run_id,
                    status="failed",
                    error=error_msg,
                    message=error_msg,
                )
                return

            # ---------------------------------------------------------------------
            # Stage 3: Map Findings & Complete Run
            # ---------------------------------------------------------------------
            default_evidence = EvidenceReferences(
                screenshot_path=pipeline_result.metadata.get("screenshot_path"),
                dom_snapshot_path=pipeline_result.metadata.get("dom_snapshot_path"),
            )

            try:
                mapped_findings = [
                    map_inspection_finding_to_response(
                        finding=f,
                        run_id=run_id,
                        index=idx,
                        default_evidence=default_evidence,
                    )
                    for idx, f in enumerate(pipeline_result.findings, start=1)
                ]
            except Exception as exc:
                error_msg = f"Finding mapping error: {str(exc)}"
                logger.error("Run %s failed during finding mapping: %s", run_id, error_msg)
                run_store.update_run(
                    run_id,
                    status="failed",
                    error=error_msg,
                    message="Failed to validate finding schema.",
                )
                return

            run_store.set_findings(run_id, mapped_findings)
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
        except Exception as exc:
            error_msg = str(exc).strip() or f"{exc.__class__.__name__}: orchestration failed"
            logger.exception("Run %s encountered an unexpected orchestration error: %s", run_id, error_msg)
            run_store.update_run(
                run_id,
                status="failed",
                error=error_msg,
                message=f"Orchestration error: {error_msg}",
            )

run_orchestrator = RunOrchestrator()
