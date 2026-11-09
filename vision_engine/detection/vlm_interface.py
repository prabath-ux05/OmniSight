"""Interface contract for future Vision-Language Model detectors."""

from typing import Protocol, runtime_checkable

from vision_engine.models import VisionFinding, VisionInput


@runtime_checkable
class VLMDetector(Protocol):
    """Contract that a future VLM detector must implement."""

    def detect(self, input_data: VisionInput) -> list[VisionFinding]:
        """Analyze supplied evidence and return structured findings."""
        ...
