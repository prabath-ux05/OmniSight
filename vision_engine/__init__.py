"""OmniSight Multimodal Vision Engine Module."""

from vision_engine.detection.dom_detector import detect_dom_issues
from vision_engine.detection.mock_detector import detect_mock
from vision_engine.detection.providers import (
    BaseVLMProvider,
    GeminiVLMProvider,
    OpenAIVLMProvider,
    VLMConfig,
    VLMConfigurationError,
    VLMError,
    VLMProviderError,
    check_vlm_configuration,
    create_vlm_provider,
)
from vision_engine.detection.vlm_detector import detect_vlm
from vision_engine.evidence_validator import validate_evidence
from vision_engine.models import (
    BoundingBox,
    EvidenceReferences,
    VisionFinding,
    VisionInput,
)

__all__ = [
    "detect_vlm",
    "detect_dom_issues",
    "detect_mock",
    "validate_evidence",
    "check_vlm_configuration",
    "create_vlm_provider",
    "BaseVLMProvider",
    "GeminiVLMProvider",
    "OpenAIVLMProvider",
    "VLMConfig",
    "VLMError",
    "VLMConfigurationError",
    "VLMProviderError",
    "BoundingBox",
    "EvidenceReferences",
    "VisionFinding",
    "VisionInput",
]
