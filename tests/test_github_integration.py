"""Unit tests for GitHub Integration, Safe Patch Generation, and PR Workflow.

Requirements verified:
- Structured proposal generation with original selector, proposed locator, validation evidence, and confidence.
- Safe patch generation: minimal diffs, path validation, path traversal prevention, and OmniSight internal file protection.
- Original selector check: refuses to corrupt file if selector is absent.
- Read-only safety: patch generation never modifies target files on disk.
- Approval gate: remote PR submission strictly requires user_approved=True.
- Masked credentials: tokens are never exposed in configuration or responses.
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from github_integration.branches.branch_manager import (
    BranchManagementError,
    create_github_branch,
    sanitize_branch_name,
)
from github_integration.commits.patch_generator import (
    PatchSecurityError,
    generate_locator_patch,
    validate_target_path,
)
from github_integration.pull_requests.pr_manager import (
    ApprovalRequiredError,
    PullRequestError,
    build_pr_markdown_body,
    create_repair_pull_request,
)
from github_integration.service import GitHubIntegrationService
from self_healing.models import (
    LiveVerificationResult,
    ProposalStatus,
    RepairProposal,
    RepairResult,
    RepairStrategy,
    RepairValidationResult,
)


@pytest.fixture
def target_repo_workspace(tmp_path: Path):
    """Create a simulated target test repository workspace."""
    workspace = tmp_path / "test_project"
    workspace.mkdir(parents=True, exist_ok=True)

    tests_dir = workspace / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)

    test_file = tests_dir / "test_login.py"
    test_file.write_text(
        'def test_user_login(page):\n'
        '    page.goto("http://example.com/login")\n'
        '    page.locator("#old-broken-login-btn").click()\n'
        '    assert page.is_visible("#welcome-header")\n',
        encoding="utf-8",
    )

    return {
        "root": str(workspace),
        "test_file_rel": "tests/test_login.py",
        "test_file_abs": str(test_file),
    }


# =============================================================================
# 1. Path Security & Traversal Protection Tests
# =============================================================================

def test_validate_target_path_rejects_empty():
    with pytest.raises(PatchSecurityError, match="empty or whitespace"):
        validate_target_path("")


def test_validate_target_path_rejects_traversal(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    with pytest.raises(PatchSecurityError, match="Path traversal"):
        validate_target_path("../../etc/passwd", workspace_root=str(workspace))


def test_validate_target_path_rejects_outside_boundary(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("print('outside')", encoding="utf-8")

    with pytest.raises(PatchSecurityError, match="resolves outside the allowed workspace"):
        validate_target_path(str(outside_file), workspace_root=str(workspace))


def test_validate_target_path_rejects_omnisight_internals(tmp_path: Path):
    # Simulate OmniSight repo structure
    workspace = tmp_path / "omnisight_root"
    workspace.mkdir()
    (workspace / "backend").mkdir()
    target = workspace / "backend" / "app" / "main.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# backend code", encoding="utf-8")

    with pytest.raises(PatchSecurityError, match="Refusing to generate patch targeting OmniSight internal module"):
        validate_target_path("backend/app/main.py", workspace_root=str(workspace), allow_internal=False)


def test_validate_target_path_accepts_valid_file(target_repo_workspace):
    resolved = validate_target_path(
        target_repo_workspace["test_file_rel"],
        workspace_root=target_repo_workspace["root"],
    )
    assert resolved.exists()
    assert resolved.is_file()


# =============================================================================
# 2. Safe Patch Generation Tests
# =============================================================================

def test_generate_locator_patch_success(target_repo_workspace):
    """Verify minimal unified diff generation for known target file."""
    test_file = target_repo_workspace["test_file_abs"]
    mtime_before = Path(test_file).stat().st_mtime
    content_before = Path(test_file).read_text(encoding="utf-8")

    patch_res = generate_locator_patch(
        original_selector="#old-broken-login-btn",
        proposed_locator='[data-testid="login-submit-btn"]',
        target_file=target_repo_workspace["test_file_rel"],
        workspace_root=target_repo_workspace["root"],
    )

    assert patch_res.success is True
    assert patch_res.replaced_count == 1
    assert patch_res.diff is not None
    assert "-    page.locator(\"#old-broken-login-btn\").click()" in patch_res.diff
    assert '+    page.locator("[data-testid="login-submit-btn"]").click()' in patch_res.diff


    # Non-destructive guarantee: Target file on disk MUST NOT have been modified!
    assert Path(test_file).stat().st_mtime == mtime_before
    assert Path(test_file).read_text(encoding="utf-8") == content_before


def test_generate_locator_patch_refuses_when_selector_not_in_file(target_repo_workspace):
    """Verify safe failure when original selector does not exist in target file."""
    patch_res = generate_locator_patch(
        original_selector="#completely-unrelated-alien-selector",
        proposed_locator='[data-testid="button"]',
        target_file=target_repo_workspace["test_file_rel"],
        workspace_root=target_repo_workspace["root"],
    )

    assert patch_res.success is False
    assert patch_res.diff is None
    assert "was not found in target file" in patch_res.error


def test_generate_locator_patch_rejects_nonexistent_file(target_repo_workspace):
    patch_res = generate_locator_patch(
        original_selector="#btn",
        proposed_locator="#new-btn",
        target_file="tests/does_not_exist.py",
        workspace_root=target_repo_workspace["root"],
    )
    assert patch_res.success is False
    assert "does not exist" in patch_res.error


# =============================================================================
# 3. Branch & Proposal Generation Tests
# =============================================================================

def test_sanitize_branch_name():
    b1 = sanitize_branch_name("f_missing_01", suffix="12345678")
    assert b1 == "omnisight/heal-f-missing-01-12345678"

    b2 = sanitize_branch_name("Finding #99! Special", suffix="abcd")
    assert "omnisight/heal-finding--99--special-abcd" in b2


def test_create_proposal_locally_validated(target_repo_workspace):
    service = GitHubIntegrationService(token="dummy", owner="owner", repo="repo")
    repair = RepairResult(
        finding_id="f_01",
        original_selector="#old-btn",
        repaired=True,
        best_locator='[data-testid="new-btn"]',
        confidence=0.95,
        strategy=RepairStrategy.DATA_ATTRIBUTE,
        snapshot_validation=RepairValidationResult(is_valid=True, matches=1, validation_message="Unique"),
        live_verification=LiveVerificationResult(
            attempted=True, is_verified=True, matches=1, target_url="http://127.0.0.1:8080"
        ),
        reason="Resolved via data_testid attribute.",
    )

    proposal = service.create_proposal(
        repair_result=repair,
        run_id="run_100",
        target_file=target_repo_workspace["test_file_rel"],
        workspace_root=target_repo_workspace["root"],
    )

    assert proposal.proposal_id == "prop_run_100_f_01"
    assert proposal.status == ProposalStatus.LOCALLY_VALIDATED
    assert proposal.proposed_locator == '[data-testid="new-btn"]'
    assert proposal.live_verification.is_verified is True


def test_create_proposal_without_target_file_is_advisory():
    service = GitHubIntegrationService()
    repair = RepairResult(
        finding_id="f_02",
        original_selector="#btn",
        repaired=True,
        best_locator="#fixed-btn",
        confidence=0.90,
        strategy=RepairStrategy.STABLE_ID,
        snapshot_validation=RepairValidationResult(is_valid=True, matches=1, validation_message="Unique"),
        reason="Stable ID found.",
    )

    # When target_file is omitted, proposal must NOT guess or invent code
    proposal = service.create_proposal(repair_result=repair, run_id="run_200", target_file=None)
    assert proposal.target_file is None
    assert proposal.patch is None
    assert proposal.status == ProposalStatus.PROPOSED


# =============================================================================
# 4. Approval Gate & Pull Request Tests
# =============================================================================

def test_pr_creation_strictly_requires_user_approval():
    """Verify that user_approved=False strictly prevents remote write / PR creation."""
    proposal = RepairProposal(
        proposal_id="prop_test_01",
        run_id="run_1",
        finding_id="f_1",
        original_selector="#old",
        proposed_locator="#new",
        confidence=0.95,
        rationale="Heuristic match",
        created_at="2026-10-26T00:00:00Z",
    )

    with pytest.raises(ApprovalRequiredError, match="requires explicit user approval"):
        create_repair_pull_request(
            proposal=proposal,
            token="ghp_test_token",
            owner="my-org",
            repo="my-app",
            user_approved=False,
        )

    # Even in simulation mode, user_approved=False MUST still be blocked
    with pytest.raises(ApprovalRequiredError, match="requires explicit user approval"):
        create_repair_pull_request(
            proposal=proposal,
            token="simulated-token",
            owner="my-org",
            repo="my-app",
            user_approved=False,
            simulate=True,
        )


def test_pr_creation_simulated_mode():
    """Verify simulated PR creation with user_approved=True."""
    proposal = RepairProposal(
        proposal_id="prop_sim_01",
        run_id="run_1",
        finding_id="f_1",
        original_selector="#old",
        proposed_locator="#new",
        confidence=0.95,
        rationale="Heuristic match",
        created_at="2026-10-26T00:00:00Z",
    )

    res = create_repair_pull_request(
        proposal=proposal,
        token="simulated-token",
        owner="my-org",
        repo="my-app",
        user_approved=True,
        simulate=True,
    )

    assert res.status == "simulated"
    assert res.simulated is True
    assert res.success is True
    assert res.pr_number is None
    assert res.pr_url is None
    assert "fix(locator):" in res.title
    assert "OmniSight Autonomous Locator Repair Proposal" in res.body
    assert "Dry-run simulation" in res.message


def test_build_pr_markdown_body():
    proposal = RepairProposal(
        proposal_id="prop_md_01",
        run_id="run_md",
        finding_id="f_md",
        original_selector="#missing-btn",
        proposed_locator='[data-testid="login-btn"]',
        strategy=RepairStrategy.DATA_ATTRIBUTE,
        confidence=0.98,
        rationale="Attribute is uniquely present in snapshot.",
        snapshot_validation=RepairValidationResult(is_valid=True, matches=1, validation_message="Resolved"),
        live_verification=LiveVerificationResult(
            attempted=True, is_verified=True, matches=1, target_url="http://localhost:8080", validation_message="Passed"
        ),
        created_at="2026-10-26T00:00:00Z",
    )

    body = build_pr_markdown_body(proposal)
    assert "#missing-btn" in body
    assert '[data-testid="login-btn"]' in body
    assert "data_attribute" in body
    assert "98%" in body
    assert "PASS" in body
    assert "Safety & Governance Notice" in body


def test_github_config_masks_token(monkeypatch):
    monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "ghp_1234567890abcdefghijk")
    monkeypatch.setenv("GITHUB_REPO_OWNER", "test-org")
    monkeypatch.setenv("GITHUB_REPO_NAME", "test-repo")

    service = GitHubIntegrationService.from_env()
    status = service.get_configuration_status()

    assert status["is_configured"] is True
    assert status["owner"] == "test-org"
    assert status["repo"] == "test-repo"
    assert status["token_status"] == "...hijk"
    assert "1234567890" not in str(status)
