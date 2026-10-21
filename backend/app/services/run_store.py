"""In-memory storage service for OmniSight inspection runs.

ARCHITECTURE NOTE:
Persistent database storage (such as SQLite or PostgreSQL) has not yet been
introduced to the repository. This module implements a clean in-memory storage
pattern to support run creation and tracking during early milestone development.

LIMITATIONS OF THIS IN-MEMORY APPROACH:
1. Volatility: All run data is stored in RAM. Restarting or stopping the server process
   clears all existing runs.
2. Process Isolation: Run data is not shared between multiple Uvicorn worker processes
   or distributed servers.
3. Scalability: Memory footprint grows with the number of runs created.
A persistent database backend with ORM/migrations should replace this store in a future milestone.
"""

from datetime import datetime, timezone
import uuid
from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from backend.app.schemas.runs import RunCreateRequest, RunResponse


class RunStore:
    """In-memory repository managing inspection runs and defect findings."""

    def __init__(self) -> None:
        self._runs: dict[str, RunResponse] = {}
        self._findings: dict[str, list[FindingResponse]] = {}

    def create(self, request: RunCreateRequest) -> RunResponse:
        """Create and record a new run in the initial 'queued' status.

        Generates a unique run_id and captures the UTC creation timestamp.
        Does NOT initiate browser capture or vision analysis.
        """
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()

        run = RunResponse(
            run_id=run_id,
            url=str(request.url),
            status="queued",
            created_at=created_at,
            message="Run created successfully and queued for inspection.",
        )
        self._runs[run_id] = run
        self._findings[run_id] = []
        return run

    def get(self, run_id: str) -> RunResponse | None:
        """Retrieve a run by its unique identifier."""
        return self._runs.get(run_id)

    def list_all(self) -> list[RunResponse]:
        """List all stored runs."""
        return list(self._runs.values())

    def get_findings(self, run_id: str) -> list[FindingResponse] | None:
        """Retrieve findings associated with a run. Returns None if run does not exist."""
        if run_id not in self._runs:
            return None
        return self._findings.get(run_id, [])

    def set_findings(self, run_id: str, findings: list[FindingResponse]) -> None:
        """Set findings for a run."""
        self._findings[run_id] = findings

    def clear(self) -> None:
        """Clear all stored runs and findings (used for test isolation)."""
        self._runs.clear()
        self._findings.clear()


# Global in-memory singleton
run_store = RunStore()


def create_mock_findings(run_id: str) -> list[FindingResponse]:
    """Generate clearly labelled mock defect findings for early milestone development."""
    return [
        FindingResponse(
            finding_id=f"defect_{run_id}_001",
            category="layout_overflow",
            severity="medium",
            confidence=0.92,
            description="[MOCK] Content panel text extends beyond container boundary.",
            selector="#main-content-panel",
            evidence=EvidenceReferences(
                screenshot_path=f"artifacts/{run_id}/before.png",
                dom_snapshot_path=f"artifacts/{run_id}/dom.html",
            ),
            source="mock",
        ),
        FindingResponse(
            finding_id=f"defect_{run_id}_002",
            category="broken_image",
            severity="high",
            confidence=0.88,
            description="[MOCK] Service topology image fails to display.",
            selector="#service-topology-image",
            evidence=EvidenceReferences(
                screenshot_path=f"artifacts/{run_id}/before.png",
            ),
            source="mock",
        ),
    ]

