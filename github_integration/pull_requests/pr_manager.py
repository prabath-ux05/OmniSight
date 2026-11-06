"""GitHub Pull Request workflow manager with explicit user approval gating."""

from __future__ import annotations

import base64
from typing import Any, Optional
import httpx
from pydantic import BaseModel, Field

from self_healing.models import RepairProposal


class ApprovalRequiredError(PermissionError):
    """Raised when an operation requires explicit user approval before execution."""


class PullRequestError(Exception):
    """Raised when GitHub Pull Request creation or commit fails."""


class PullRequestResult(BaseModel):
    """Structured result of a GitHub Pull Request preparation or creation."""

    status: str = Field(..., description="Status: 'created', 'simulated', 'approval_required', or 'failed'")
    success: bool = Field(default=True, description="Whether the pull request workflow succeeded (created or simulated)")
    simulated: bool = Field(default=False, description="Whether this pull request was simulated in dry-run mode")
    pr_number: Optional[int] = Field(default=None, description="GitHub PR number")
    pr_url: Optional[str] = Field(default=None, description="Direct web URL to the GitHub Pull Request")
    branch_name: str = Field(..., description="Head branch containing the patch")
    base_branch: str = Field(..., description="Target base branch (e.g. main)")
    title: str = Field(..., description="Pull request title")
    body: str = Field(..., description="Pull request description body in Markdown")
    diff_preview: Optional[str] = Field(default=None, description="Unified diff preview")
    target_file: Optional[str] = Field(default=None, description="Target file modified")
    message: Optional[str] = Field(default=None, description="Status or simulation message")
    error: Optional[str] = Field(default=None, description="Error message if failed")


def build_pr_markdown_body(proposal: RepairProposal) -> str:
    """Format structured, human-reviewable Markdown body for a repair Pull Request."""
    snapshot_msg = (
        proposal.snapshot_validation.validation_message
        if proposal.snapshot_validation
        else "Not recorded"
    )
    live_msg = (
        proposal.live_verification.validation_message
        if proposal.live_verification and proposal.live_verification.attempted
        else "Live verification was not executed for this run"
    )

    diff_section = (
        f"```diff\n{proposal.patch.diff}\n```"
        if proposal.patch and proposal.patch.diff
        else "_No patch file diff generated. Locator proposal is advisory for test engineers._"
    )

    return f"""## ⚡ OmniSight Autonomous Locator Repair Proposal

### 📋 Overview
- **Finding ID:** `{proposal.finding_id}`
- **Run ID:** `{proposal.run_id}`
- **Original Selector:** `{proposal.original_selector}`
- **Recommended Locator:** `{proposal.proposed_locator}`
- **Strategy:** `{proposal.strategy.value if proposal.strategy else 'Heuristic'}`
- **Confidence:** `{round(proposal.confidence * 100)}%`
- **Target File:** `{proposal.target_file or 'Advisory (unspecified)'}`

---

### 🔍 Verification Evidence
| Verification Stage | Status | Match Count | Notes |
|---|---|---|---|
| **Snapshot DOM** | `{'PASS' if (proposal.snapshot_validation and proposal.snapshot_validation.is_valid) else 'UNRESOLVED'}` | `{proposal.snapshot_validation.matches if proposal.snapshot_validation else 0}` | {snapshot_msg} |
| **Live Fresh-Page** | `{'PASS' if (proposal.live_verification and proposal.live_verification.is_verified) else 'SKIPPED/FAIL'}` | `{proposal.live_verification.matches if proposal.live_verification else 0}` | {live_msg} |

---

### 💡 Engine Rationale & Decision Notes
{proposal.rationale}

---

### 📝 Proposed Changes
{diff_section}

---
> 🛡️ **Safety & Governance Notice:** This change proposal was generated autonomously by OmniSight's Self-Healing Engine and explicitly reviewed and approved by an authorized engineer prior to pull request submission.
"""


def create_repair_pull_request(
    proposal: RepairProposal,
    token: str,
    owner: str,
    repo: str,
    base_branch: str = "main",
    branch_name: Optional[str] = None,
    user_approved: bool = False,
    patched_file_content: Optional[str] = None,
    client: Optional[httpx.Client] = None,
    simulate: bool = False,
) -> PullRequestResult:
    """Prepare and create a GitHub Pull Request for an approved repair proposal.

    Args:
        proposal: The validated RepairProposal.
        token: GitHub API access token.
        owner: GitHub repository owner.
        repo: GitHub repository name.
        base_branch: Target base branch (default: main).
        branch_name: Optional custom branch name.
        user_approved: Explicit human approval gate. Must be True to proceed.
        patched_file_content: Optional full content of the patched file to commit.
        client: Optional httpx.Client for testing.
        simulate: If True, simulates creation without network writes.

    Returns:
        PullRequestResult with PR details and reviewable markdown.

    Raises:
        ApprovalRequiredError: If user_approved is False.
        PullRequestError: If token/repo configuration is invalid or GitHub API rejects.
    """
    head_branch = branch_name or proposal.branch_name or f"omnisight/heal-{proposal.finding_id}"
    pr_title = f"fix(locator): self-heal broken locator '{proposal.original_selector}'"
    pr_body = build_pr_markdown_body(proposal)
    diff_preview = proposal.patch.diff if proposal.patch else None
    target_file = proposal.target_file

    # 1. Approval Gate Check: Strict human-in-the-loop requirement
    if not user_approved:
        raise ApprovalRequiredError(
            "Pull request submission requires explicit user approval. "
            "Please review the locator candidate and diff preview before confirming."
        )

    # 2. Simulation mode (for offline tests or dry-run)
    if simulate or not token or token == "simulated-token":
        return PullRequestResult(
            status="simulated",
            success=True,
            simulated=True,
            pr_number=None,
            pr_url=None,
            branch_name=head_branch,
            base_branch=base_branch,
            title=pr_title,
            body=pr_body,
            diff_preview=diff_preview,
            target_file=target_file,
            message="Dry-run simulation: PR was prepared and validated, but no remote branch or PR was created on GitHub.",
        )

    if not owner or not repo:
        raise PullRequestError("Repository owner and repository name are required.")

    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    base_url = "https://api.github.com"

    def _execute(c: httpx.Client) -> PullRequestResult:
        # A. If target_file and content are provided, commit the file to head_branch
        if target_file and patched_file_content:
            file_url = f"{base_url}/repos/{owner}/{repo}/contents/{target_file}"
            # Check if file exists on branch to obtain SHA
            get_res = c.get(f"{file_url}?ref={head_branch}", headers=headers)
            file_sha = None
            if get_res.status_code == 200:
                file_sha = get_res.json().get("sha")

            encoded_bytes = base64.b64encode(patched_file_content.encode("utf-8")).decode("utf-8")
            commit_payload = {
                "message": f"fix(locator): heal {proposal.original_selector} -> {proposal.proposed_locator}",
                "content": encoded_bytes,
                "branch": head_branch,
            }
            if file_sha:
                commit_payload["sha"] = file_sha

            put_res = c.put(file_url, headers=headers, json=commit_payload)
            if put_res.status_code not in (200, 201):
                raise PullRequestError(
                    f"Failed to commit patched file to branch '{head_branch}': HTTP {put_res.status_code}"
                )

        # B. Create Pull Request
        pr_url = f"{base_url}/repos/{owner}/{repo}/pulls"
        pr_payload = {
            "title": pr_title,
            "body": pr_body,
            "head": head_branch,
            "base": base_branch,
        }
        res = c.post(pr_url, headers=headers, json=pr_payload)
        if res.status_code not in (200, 201):
            raise PullRequestError(
                f"GitHub API rejected Pull Request creation: HTTP {res.status_code} - {res.text[:250]}"
            )

        data = res.json()
        return PullRequestResult(
            status="created",
            success=True,
            simulated=False,
            pr_number=data.get("number"),
            pr_url=data.get("html_url"),
            branch_name=head_branch,
            base_branch=base_branch,
            title=pr_title,
            body=pr_body,
            diff_preview=diff_preview,
            target_file=target_file,
            message="Pull request successfully submitted to GitHub.",
        )

    if client is not None:
        return _execute(client)
    else:
        with httpx.Client(timeout=20.0) as http_client:
            return _execute(http_client)
