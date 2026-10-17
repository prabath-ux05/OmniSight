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
from backend.app.schemas.runs import RunCreateRequest, RunResponse


class RunStore:
    """In-memory repository managing inspection runs."""

    def __init__(self) -> None:
        self._runs: dict[str, RunResponse] = {}

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
        return run

    def get(self, run_id: str) -> RunResponse | None:
        """Retrieve a run by its unique identifier."""
        return self._runs.get(run_id)

    def list_all(self) -> list[RunResponse]:
        """List all stored runs."""
        return list(self._runs.values())

    def clear(self) -> None:
        """Clear all stored runs (used for test isolation)."""
        self._runs.clear()


# Global in-memory singleton
run_store = RunStore()
