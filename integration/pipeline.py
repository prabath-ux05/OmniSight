"""OmniSight Integration Pipeline Adapter.

Provides typed pipeline result handling and a lightweight integration adapter
for connecting inspection requests and visual/locator defect findings.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Sequence, Union

from integration.contracts import (
    DefectCategory,
    InspectionFinding,
    InspectionRequest,
    InspectionState,
    Severity,
)
from integration.demo_runner import construct_demo_url
from urllib.parse import parse_qsl, urlparse


@dataclass
class PipelineResult:
    """Typed result container for multimodal UI inspection pipeline runs.

    Encapsulates the originating InspectionRequest, any collected InspectionFinding
    objects, execution status, and serialized representation.
    """

    request: InspectionRequest
    findings: list[InspectionFinding] = field(default_factory=list)
    success: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate and normalize request
        if isinstance(self.request, str):
            self.request = InspectionRequest(target_url=self.request)
        elif isinstance(self.request, dict):
            self.request = InspectionRequest.from_dict(self.request)
        elif not isinstance(self.request, InspectionRequest):
            raise TypeError(
                f"request must be an InspectionRequest, dict, or str, got {type(self.request).__name__}"
            )

        # Validate and normalize findings collection
        if not isinstance(self.findings, list):
            raw_findings = list(self.findings)
        else:
            raw_findings = self.findings

        normalized_findings: list[InspectionFinding] = []
        for item in raw_findings:
            if isinstance(item, InspectionFinding):
                normalized_findings.append(item)
            elif isinstance(item, dict):
                normalized_findings.append(InspectionFinding.from_dict(item))
            else:
                raise TypeError(
                    f"Finding item must be an InspectionFinding or dict, got {type(item).__name__}"
                )
        self.findings = normalized_findings

        # Validate success flag
        self.success = bool(self.success)

        # Validate metadata
        if not isinstance(self.metadata, dict):
            raise TypeError(f"metadata must be a dict, got {type(self.metadata).__name__}")
        self.metadata = dict(self.metadata)

    def add_finding(self, finding: Union[InspectionFinding, dict[str, Any]]) -> InspectionFinding:
        """Collect a single inspection finding."""
        if isinstance(finding, InspectionFinding):
            normalized = finding
        elif isinstance(finding, dict):
            normalized = InspectionFinding.from_dict(finding)
        else:
            raise TypeError(
                f"finding must be an InspectionFinding or dict, got {type(finding).__name__}"
            )
        self.findings.append(normalized)
        return normalized

    def add_findings(
        self, findings: Iterable[Union[InspectionFinding, dict[str, Any]]]
    ) -> list[InspectionFinding]:
        """Collect multiple inspection findings."""
        added: list[InspectionFinding] = []
        for finding in findings:
            added.append(self.add_finding(finding))
        return added

    @property
    def has_findings(self) -> bool:
        """Return True if one or more inspection findings were detected."""
        return len(self.findings) > 0

    @property
    def findings_detected(self) -> bool:
        """Alias for has_findings indicating defect detection."""
        return self.has_findings

    @property
    def findings_count(self) -> int:
        """Return the count of collected findings."""
        return len(self.findings)

    def get_findings_by_severity(self, severity: Union[Severity, str]) -> list[InspectionFinding]:
        """Filter findings matching the specified severity."""
        norm_sev = Severity.from_str(severity)
        return [f for f in self.findings if f.severity == norm_sev]

    def get_findings_by_category(
        self, category: Union[DefectCategory, str]
    ) -> list[InspectionFinding]:
        """Filter findings matching the specified defect category."""
        norm_cat = DefectCategory.from_str(category)
        return [f for f in self.findings if f.defect_category == norm_cat]

    def to_dict(self) -> dict[str, Any]:
        """Convert pipeline result to a JSON-serializable dictionary."""
        return {
            "request": self.request.to_dict(),
            "findings": [f.to_dict() for f in self.findings],
            "has_findings": self.has_findings,
            "findings_count": len(self.findings),
            "success": self.success,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PipelineResult:
        """Construct a PipelineResult instance from a dictionary."""
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        if "request" not in data:
            raise ValueError("Dictionary missing 'request'")

        req_data = data["request"]
        if isinstance(req_data, InspectionRequest):
            req = req_data
        elif isinstance(req_data, dict):
            req = InspectionRequest.from_dict(req_data)
        elif isinstance(req_data, str):
            req = InspectionRequest(target_url=req_data)
        else:
            raise TypeError(f"Invalid request data type: {type(req_data).__name__}")

        findings_data = data.get("findings", [])
        if not isinstance(findings_data, (list, tuple)):
            raise TypeError(f"findings must be a list or tuple, got {type(findings_data).__name__}")

        findings: list[InspectionFinding] = []
        for item in findings_data:
            if isinstance(item, InspectionFinding):
                findings.append(item)
            elif isinstance(item, dict):
                findings.append(InspectionFinding.from_dict(item))
            else:
                raise TypeError(
                    f"Finding item must be an InspectionFinding or dict, got {type(item).__name__}"
                )

        return cls(
            request=req,
            findings=findings,
            success=bool(data.get("success", True)),
            metadata=dict(data.get("metadata", {})),
        )

    def to_json(self, **kwargs: Any) -> str:
        """Serialize pipeline result to JSON string."""
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> PipelineResult:
        """Deserialize pipeline result from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __len__(self) -> int:
        return len(self.findings)

    def __iter__(self):
        return iter(self.findings)

    def __getitem__(self, index: int) -> InspectionFinding:
        return self.findings[index]

    def __bool__(self) -> bool:
        return self.success


class IntegrationPipelineAdapter:
    """Minimal integration pipeline adapter for coordinating inspection requests and findings."""

    def __init__(
        self,
        name: str = "default_integration_pipeline",
        default_timeout: float = 5.0,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.name = name
        self.default_timeout = default_timeout
        self.metadata = dict(metadata or {})

    def run(
        self,
        request: Union[InspectionRequest, dict[str, Any], str],
        findings: Optional[Iterable[Union[InspectionFinding, dict[str, Any]]]] = None,
        collector: Optional[
            Callable[[InspectionRequest], Optional[Iterable[Union[InspectionFinding, dict[str, Any]]]]]
        ] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> PipelineResult:
        """Execute an inspection pass using the provided request and optional finding collector.

        Args:
            request: Target inspection request, dict, or URL string.
            findings: Pre-collected findings to include in the pipeline result.
            collector: Optional callable hook that returns findings for the given request.
            metadata: Additional metadata to merge into the pipeline result.

        Returns:
            PipelineResult containing the request and collected findings.
        """
        if isinstance(request, str):
            req = InspectionRequest(target_url=request, timeout=self.default_timeout)
        elif isinstance(request, dict):
            req = InspectionRequest.from_dict(request)
        elif isinstance(request, InspectionRequest):
            req = request
        else:
            raise TypeError(
                f"request must be an InspectionRequest, dict, or str, got {type(request).__name__}"
            )

        merged_metadata = dict(self.metadata)
        if metadata:
            merged_metadata.update(metadata)

        result = PipelineResult(request=req, metadata=merged_metadata)

        if findings is not None:
            result.add_findings(findings)

        if collector is not None:
            if not callable(collector):
                raise TypeError(f"collector must be callable, got {type(collector).__name__}")
            collected = collector(req)
            if collected is not None:
                result.add_findings(collected)

        return result

    # Aliases
    execute = run
    create_result = run

    def execute_inspection(
        self,
        request: Union[InspectionRequest, dict[str, Any], str],
        *,
        navigator: Optional[Any] = None,
        detector: Optional[Callable[[Any], list[Any]]] = None,
        run_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> PipelineResult:
        """Execute the full Demo Site -> Browser Agent -> Vision Engine inspection flow."""
        merged_meta = dict(self.metadata)
        if metadata:
            merged_meta.update(metadata)
        return execute_inspection_flow(
            request=request,
            navigator=navigator,
            detector=detector,
            run_id=run_id,
            metadata=merged_meta,
        )


def vision_finding_to_inspection_finding(finding: Any) -> InspectionFinding:
    """Convert a Vision Engine VisionFinding into a shared InspectionFinding."""
    if isinstance(finding, InspectionFinding):
        return finding

    # Handle VisionFinding (Pydantic model) or dict-like object
    if hasattr(finding, "category"):
        raw_category = finding.category
    elif isinstance(finding, dict):
        raw_category = finding.get("category") or finding.get("defect_category")
    else:
        raise TypeError(f"Unsupported finding type: {type(finding).__name__}")

    category_mapping = {
        "layout_overflow": DefectCategory.OVERFLOW,
        "missing_visible_element": DefectCategory.MISSING_ELEMENT,
        "broken_image": DefectCategory.BROKEN_IMAGE,
    }
    norm_cat = category_mapping.get(
        str(raw_category), DefectCategory.from_str(str(raw_category))
    )

    raw_sev = getattr(finding, "severity", None) or (
        finding.get("severity") if isinstance(finding, dict) else "info"
    )
    norm_sev = Severity.from_str(str(raw_sev))

    description = getattr(finding, "description", None) or (
        finding.get("description") if isinstance(finding, dict) else ""
    )
    selector = getattr(finding, "selector", None) or (
        finding.get("selector") if isinstance(finding, dict) else None
    )
    confidence = getattr(finding, "confidence", None)
    if confidence is None and isinstance(finding, dict):
        confidence = finding.get("confidence")

    meta: dict[str, Any] = {}
    if hasattr(finding, "finding_id"):
        meta["finding_id"] = finding.finding_id
    elif isinstance(finding, dict) and "finding_id" in finding:
        meta["finding_id"] = finding["finding_id"]

    if hasattr(finding, "source"):
        meta["source"] = finding.source
    elif isinstance(finding, dict) and "source" in finding:
        meta["source"] = finding["source"]

    if hasattr(finding, "bounding_box") and finding.bounding_box:
        meta["bounding_box"] = (
            finding.bounding_box.model_dump()
            if hasattr(finding.bounding_box, "model_dump")
            else dict(finding.bounding_box)
        )
    elif isinstance(finding, dict) and "bounding_box" in finding:
        meta["bounding_box"] = finding["bounding_box"]

    if hasattr(finding, "evidence") and finding.evidence:
        meta["evidence"] = (
            finding.evidence.model_dump()
            if hasattr(finding.evidence, "model_dump")
            else dict(finding.evidence)
        )
    elif isinstance(finding, dict) and "evidence" in finding:
        meta["evidence"] = finding["evidence"]

    return InspectionFinding(
        defect_category=norm_cat,
        severity=norm_sev,
        description=description,
        selector=selector,
        confidence=confidence,
        metadata=meta,
    )


def execute_inspection_flow(
    request: Union[InspectionRequest, dict[str, Any], str],
    *,
    navigator: Optional[Any] = None,
    detector: Optional[Callable[[Any], list[Any]]] = None,
    run_id: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> PipelineResult:
    """Execute the end-to-end multimodal inspection flow.

    Flow: Demo Site -> Browser Agent (navigation & evidence capture)
          -> Vision Engine (evidence validation & defect detection)
          -> Structured Findings (PipelineResult with InspectionFindings).

    Args:
        request: Target inspection request, dict, or URL string.
        navigator: Optional browser navigator instance (defaults to BrowserNavigator).
        detector: Optional vision detector callable (defaults to detect_mock).
        run_id: Optional identifier for the run.
        metadata: Optional additional metadata.

    Returns:
        PipelineResult containing the request, collected findings, and runtime metadata.
    """
    if isinstance(request, str):
        req = InspectionRequest(target_url=request)
    elif isinstance(request, dict):
        req = InspectionRequest.from_dict(request)
    elif isinstance(request, InspectionRequest):
        req = request
    else:
        raise TypeError(
            f"request must be an InspectionRequest, dict, or str, got {type(request).__name__}"
        )

    # Resolve target URL with query params for state if applicable
    parsed_req_url = urlparse(req.target_url)
    req_query = dict(parse_qsl(parsed_req_url.query))
    has_defect_param = any(
        k in req_query
        for k in (
            "defect",
            "defects",
            "state",
            "baseline",
            "defect_overflow",
            "defect_missing",
            "defect_broken_image",
        )
    )

    if has_defect_param and req.state == InspectionState.CLEAN:
        target_url = req.target_url
    else:
        target_url = construct_demo_url(req.target_url, req.state)

    actual_run_id = run_id or f"run_{uuid.uuid4().hex[:10]}"

    # Step 1: Browser Agent navigation & evidence capture
    if navigator is None:
        try:
            from browser_agent.navigation.navigator import BrowserNavigator
        except ImportError:
            from navigation.navigator import BrowserNavigator
        navigator = BrowserNavigator(timeout_ms=int(req.timeout * 1000))

    try:
        nav_result = navigator.navigate(url=target_url, run_id=actual_run_id)
    except Exception as exc:
        failed_meta = dict(metadata or {})
        err_msg = str(exc).strip() or f"{exc.__class__.__name__}: browser navigation failed"
        failed_meta.update({"error": err_msg, "run_id": actual_run_id, "url": target_url})
        return PipelineResult(request=req, success=False, metadata=failed_meta)

    if getattr(nav_result, "status", "failed") != "success":
        failed_meta = dict(metadata or {})
        nav_err = (getattr(nav_result, "error", None) or "").strip()
        failed_meta.update({
            "error": nav_err or "Navigation failed",
            "run_id": actual_run_id,
            "url": target_url,
            "status": getattr(nav_result, "status", "failed"),
            "console_errors": getattr(nav_result, "console_errors", []),
            "page_errors": getattr(nav_result, "page_errors", []),
        })
        return PipelineResult(request=req, success=False, metadata=failed_meta)

    # Step 2: Validate evidence and construct VisionInput
    from vision_engine.evidence_validator import validate_evidence
    from vision_engine.models import VisionInput

    screenshot_path = getattr(nav_result, "screenshot_path", None)
    dom_snapshot_path = getattr(nav_result, "dom_snapshot_path", None)

    vision_input = VisionInput(
        run_id=actual_run_id,
        url=getattr(nav_result, "url", target_url),
        screenshot_path=screenshot_path,
        dom_snapshot_path=dom_snapshot_path,
    )

    validation_errors = validate_evidence(vision_input)
    if validation_errors:
        failed_meta = dict(metadata or {})
        failed_meta.update({
            "error": "Evidence validation failed: " + "; ".join(validation_errors),
            "run_id": actual_run_id,
            "validation_errors": validation_errors,
        })
        return PipelineResult(request=req, success=False, metadata=failed_meta)

    # Step 3: Vision Engine detection
    try:
        if detector is not None:
            raw_vision_findings = detector(vision_input)
        else:
            from vision_engine.detection.mock_detector import detect_mock

            scenario = "clean" if req.state == InspectionState.CLEAN else "defect"
            raw_vision_findings = detect_mock(vision_input, scenario=scenario)

        # Step 4: Map Vision Engine findings to structured shared InspectionFindings
        findings = [vision_finding_to_inspection_finding(vf) for vf in raw_vision_findings]
    except Exception as exc:
        failed_meta = dict(metadata or {})
        err_msg = str(exc).strip() or f"{exc.__class__.__name__}: vision detection failed"
        failed_meta.update({"error": err_msg, "run_id": actual_run_id, "url": target_url})
        return PipelineResult(request=req, success=False, metadata=failed_meta)

    run_meta = {
        "run_id": actual_run_id,
        "page_title": getattr(nav_result, "page_title", ""),
        "captured_at": getattr(nav_result, "captured_at", ""),
        "viewport": getattr(nav_result, "viewport", {}),
        "screenshot_path": screenshot_path,
        "dom_snapshot_path": dom_snapshot_path,
        "console_errors": getattr(nav_result, "console_errors", []) or [],
        "page_errors": getattr(nav_result, "page_errors", []) or [],
        "vision_findings_count": len(findings),
    }
    if metadata:
        run_meta.update(metadata)

    return PipelineResult(
        request=req,
        findings=findings,
        success=True,
        metadata=run_meta,
    )


# Backward-compatible and semantic aliases
execute_inspection = execute_inspection_flow
run_inspection = execute_inspection_flow
InspectionPipelineResult = PipelineResult
InspectionPipelineAdapter = IntegrationPipelineAdapter
PipelineAdapter = IntegrationPipelineAdapter

__all__ = [
    "PipelineResult",
    "InspectionPipelineResult",
    "IntegrationPipelineAdapter",
    "InspectionPipelineAdapter",
    "PipelineAdapter",
    "execute_inspection_flow",
    "execute_inspection",
    "run_inspection",
    "vision_finding_to_inspection_finding",
]
