"""OmniSight Self-Healing Engine Module.

Provides autonomous locator repair and failure analysis for UI automation
test suites and RPA workflows.
"""

from self_healing.models import (
    CandidateLocator,
    LiveVerificationResult,
    PatchResult,
    ProposalStatus,
    RepairProposal,
    RepairResult,
    RepairStrategy,
    RepairValidationResult,
)
from self_healing.repair_engine import (
    SelfHealingEngine,
    repair_locator,
    self_healing_engine,
)
from self_healing.verification.locator_validator import (
    validate_locator_in_dom,
    verify_locator_on_live_page,
)

__all__ = [
    "CandidateLocator",
    "LiveVerificationResult",
    "PatchResult",
    "ProposalStatus",
    "RepairProposal",
    "RepairResult",
    "RepairStrategy",
    "RepairValidationResult",
    "SelfHealingEngine",
    "repair_locator",
    "self_healing_engine",
    "validate_locator_in_dom",
    "verify_locator_on_live_page",
]
