"""OmniSight Integration Pipeline Adapter.

Provides typed pipeline result handling and a lightweight integration adapter
for connecting inspection requests and visual/locator defect findings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional, Sequence, Union

from integration.contracts import (
    DefectCategory,
    InspectionFinding,
    InspectionRequest,
    InspectionState,
    Severity,
)


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


# Backward-compatible and semantic aliases
InspectionPipelineResult = PipelineResult
InspectionPipelineAdapter = IntegrationPipelineAdapter
PipelineAdapter = IntegrationPipelineAdapter

__all__ = [
    "PipelineResult",
    "InspectionPipelineResult",
    "IntegrationPipelineAdapter",
    "InspectionPipelineAdapter",
    "PipelineAdapter",
]
