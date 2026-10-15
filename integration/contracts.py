"""OmniSight Integration Contracts.

Shared typed contracts, enums, and data models for multimodal UI inspection,
defect classification, severity ratings, inspection requests, and findings.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Union


class InspectionState(str, Enum):
    """Supported OmniSight inspection states for demo and live target sites."""

    CLEAN = "clean"
    OVERFLOW = "overflow"
    MISSING = "missing"
    IMAGE = "image"
    ALL = "all"

    @classmethod
    def _missing_(cls, value: object) -> Optional[InspectionState]:
        if isinstance(value, str):
            cleaned = value.strip().lower()
            for member in cls:
                if member.value == cleaned:
                    return member
        return None

    @classmethod
    def from_str(cls, value: Union[str, InspectionState]) -> InspectionState:
        """Parse and normalize input into an InspectionState enum instance."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError(f"State must be a str or InspectionState, got {type(value).__name__}")
        try:
            return cls(value)
        except ValueError:
            valid_states = [s.value for s in cls]
            raise ValueError(
                f"Unsupported inspection state: '{value}'. Expected one of: {valid_states}"
            ) from None


# Backward-compatible alias for existing demo runner code
DemoInspectionState = InspectionState


class DefectCategory(str, Enum):
    """Categorization of UI defects identified during multimodal inspection."""

    OVERFLOW = "overflow"
    MISSING_ELEMENT = "missing_element"
    BROKEN_IMAGE = "broken_image"
    OTHER = "other"

    # Aliases
    MISSING = "missing_element"
    IMAGE = "broken_image"

    @classmethod
    def _missing_(cls, value: object) -> Optional[DefectCategory]:
        if isinstance(value, str):
            cleaned = value.strip().lower().replace("-", "_")
            aliases = {
                "missing": cls.MISSING_ELEMENT,
                "missing_element": cls.MISSING_ELEMENT,
                "missingelement": cls.MISSING_ELEMENT,
                "broken_image": cls.BROKEN_IMAGE,
                "brokenimage": cls.BROKEN_IMAGE,
                "broken_img": cls.BROKEN_IMAGE,
                "image": cls.BROKEN_IMAGE,
                "img": cls.BROKEN_IMAGE,
                "overflow": cls.OVERFLOW,
                "layout_overflow": cls.OVERFLOW,
                "layout": cls.OVERFLOW,
                "other": cls.OTHER,
            }
            if cleaned in aliases:
                return aliases[cleaned]
            for member in cls:
                if member.value == cleaned:
                    return member
        return None

    @classmethod
    def from_str(cls, value: Union[str, DefectCategory]) -> DefectCategory:
        """Parse and normalize input into a DefectCategory enum instance."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError(f"DefectCategory must be a str or DefectCategory, got {type(value).__name__}")
        try:
            return cls(value)
        except ValueError:
            valid_categories = list(dict.fromkeys(c.value for c in cls))
            raise ValueError(
                f"Unsupported defect category: '{value}'. Expected one of: {valid_categories}"
            ) from None


class Severity(str, Enum):
    """Defect and finding severity classifications."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def _missing_(cls, value: object) -> Optional[Severity]:
        if isinstance(value, str):
            cleaned = value.strip().lower()
            for member in cls:
                if member.value == cleaned:
                    return member
        return None

    @classmethod
    def from_str(cls, value: Union[str, Severity]) -> Severity:
        """Parse and normalize input into a Severity enum instance."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError(f"Severity must be a str or Severity, got {type(value).__name__}")
        try:
            return cls(value)
        except ValueError:
            valid_severities = [s.value for s in cls]
            raise ValueError(
                f"Unsupported severity: '{value}'. Expected one of: {valid_severities}"
            ) from None


@dataclass
class InspectionRequest:
    """Typed contract for requesting an inspection on a target URL."""

    target_url: str = ""
    state: Union[InspectionState, str] = InspectionState.CLEAN
    timeout: float = 5.0
    metadata: dict[str, Any] = field(default_factory=dict)
    url: Optional[str] = None

    def __post_init__(self) -> None:
        # Support url as an alias for target_url
        if not self.target_url and self.url:
            self.target_url = self.url
        elif not self.url and self.target_url:
            self.url = self.target_url

        if not isinstance(self.target_url, str) or not self.target_url.strip():
            raise ValueError("target_url cannot be empty")
        self.target_url = self.target_url.strip()
        self.url = self.target_url

        # Validate and normalize state
        self.state = InspectionState.from_str(self.state)

        # Validate timeout
        if not isinstance(self.timeout, (int, float)):
            raise TypeError(f"timeout must be a number, got {type(self.timeout).__name__}")
        if self.timeout <= 0:
            raise ValueError("timeout must be greater than 0")
        self.timeout = float(self.timeout)

        # Validate metadata
        if not isinstance(self.metadata, dict):
            raise TypeError(f"metadata must be a dict, got {type(self.metadata).__name__}")
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        """Convert request to a JSON-serializable dictionary."""
        return {
            "target_url": self.target_url,
            "state": self.state.value if isinstance(self.state, InspectionState) else str(self.state),
            "timeout": self.timeout,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InspectionRequest:
        """Construct an InspectionRequest instance from a dictionary."""
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        target_url = data.get("target_url") or data.get("url")
        if not target_url:
            raise ValueError("Dictionary missing 'target_url' (or 'url')")
        return cls(
            target_url=str(target_url),
            state=data.get("state", InspectionState.CLEAN),
            timeout=data.get("timeout", 5.0),
            metadata=data.get("metadata", {}),
        )

    def to_json(self, **kwargs: Any) -> str:
        """Serialize request to JSON string."""
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> InspectionRequest:
        """Deserialize request from JSON string."""
        return cls.from_dict(json.loads(json_str))


@dataclass
class InspectionFinding:
    """Typed contract representing a single visual or locator defect finding."""

    defect_category: Union[DefectCategory, str]
    severity: Union[Severity, str]
    description: str
    selector: Optional[str] = None
    confidence: Optional[float] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Validate and normalize defect_category
        self.defect_category = DefectCategory.from_str(self.defect_category)

        # Validate and normalize severity
        self.severity = Severity.from_str(self.severity)

        # Validate description
        if not isinstance(self.description, str) or not self.description.strip():
            raise ValueError("description cannot be empty")
        self.description = self.description.strip()

        # Validate selector
        if self.selector is not None:
            if not isinstance(self.selector, str):
                raise TypeError(f"selector must be a str or None, got {type(self.selector).__name__}")
            self.selector = self.selector.strip() or None

        # Validate confidence
        if self.confidence is not None:
            if not isinstance(self.confidence, (int, float)):
                raise TypeError(f"confidence must be a number or None, got {type(self.confidence).__name__}")
            if not (0.0 <= self.confidence <= 1.0):
                raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
            self.confidence = float(self.confidence)

        # Validate metadata
        if not isinstance(self.metadata, dict):
            raise TypeError(f"metadata must be a dict, got {type(self.metadata).__name__}")
        self.metadata = dict(self.metadata)

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to a JSON-serializable dictionary."""
        result: dict[str, Any] = {
            "defect_category": (
                self.defect_category.value
                if isinstance(self.defect_category, DefectCategory)
                else str(self.defect_category)
            ),
            "severity": (
                self.severity.value
                if isinstance(self.severity, Severity)
                else str(self.severity)
            ),
            "description": self.description,
            "selector": self.selector,
            "metadata": dict(self.metadata),
        }
        if self.confidence is not None:
            result["confidence"] = self.confidence
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InspectionFinding:
        """Construct an InspectionFinding instance from a dictionary."""
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        if "defect_category" not in data:
            raise ValueError("Dictionary missing 'defect_category'")
        if "severity" not in data:
            raise ValueError("Dictionary missing 'severity'")
        if "description" not in data:
            raise ValueError("Dictionary missing 'description'")

        return cls(
            defect_category=data["defect_category"],
            severity=data["severity"],
            description=data["description"],
            selector=data.get("selector"),
            confidence=data.get("confidence"),
            metadata=data.get("metadata", {}),
        )

    def to_json(self, **kwargs: Any) -> str:
        """Serialize finding to JSON string."""
        return json.dumps(self.to_dict(), **kwargs)

    @classmethod
    def from_json(cls, json_str: str) -> InspectionFinding:
        """Deserialize finding from JSON string."""
        return cls.from_dict(json.loads(json_str))


__all__ = [
    "InspectionState",
    "DemoInspectionState",
    "DefectCategory",
    "Severity",
    "InspectionRequest",
    "InspectionFinding",
]
