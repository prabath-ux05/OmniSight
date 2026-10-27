"""Branch management utilities for OmniSight self-healing Git workflows."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Optional
import httpx


class BranchManagementError(Exception):
    """Raised when branch preparation or creation fails."""


def sanitize_branch_name(finding_id: str, suffix: Optional[str] = None) -> str:
    """Format and sanitize a Git branch name for a repair proposal.

    Example output: omnisight/heal-f-missing-01-a1b2c3d4
    """
    normalized = finding_id.replace("_", "-")
    clean_id = re.sub(r"[^a-zA-Z0-9\-]", "-", normalized).strip("-").lower()
    if not clean_id:
        clean_id = "locator-fix"

    if suffix:
        clean_suffix = re.sub(r"[^a-zA-Z0-9\-]", "", suffix).lower()[:8]
    else:
        clean_suffix = hashlib.sha256(f"{finding_id}".encode()).hexdigest()[:8]

    return f"omnisight/heal-{clean_id}-{clean_suffix}"



def create_github_branch(
    branch_name: str,
    base_branch: str,
    owner: str,
    repo: str,
    token: str,
    client: Optional[httpx.Client] = None,
) -> dict[str, Any]:
    """Create a new branch on GitHub via REST API.

    Args:
        branch_name: The branch name to create (e.g. omnisight/heal-...).
        base_branch: The source base branch to branch off of (e.g. main).
        owner: GitHub repository owner.
        repo: GitHub repository name.
        token: GitHub API access token.
        client: Optional preconfigured httpx.Client (e.g. for mock testing).

    Returns:
        Dictionary with branch details and commit SHA.
    """
    if not token or not token.strip():
        raise BranchManagementError("GitHub access token is required for remote branch creation.")
    if not owner or not repo:
        raise BranchManagementError("Repository owner and name are required.")

    headers = {
        "Authorization": f"Bearer {token.strip()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    base_url = "https://api.github.com"

    def _execute(c: httpx.Client) -> dict[str, Any]:
        # 1. Fetch latest SHA of base branch
        ref_url = f"{base_url}/repos/{owner}/{repo}/git/ref/heads/{base_branch}"
        res = c.get(ref_url, headers=headers)
        if res.status_code != 200:
            raise BranchManagementError(
                f"Failed to query base branch '{base_branch}': HTTP {res.status_code}"
            )
        base_data = res.json()
        base_sha = base_data.get("object", {}).get("sha")
        if not base_sha:
            raise BranchManagementError(f"Could not resolve commit SHA for base branch '{base_branch}'.")

        # 2. Create the new reference
        create_url = f"{base_url}/repos/{owner}/{repo}/git/refs"
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha,
        }
        create_res = c.post(create_url, headers=headers, json=payload)
        if create_res.status_code in (200, 201):
            return {
                "branch_name": branch_name,
                "base_branch": base_branch,
                "sha": base_sha,
                "created": True,
            }
        elif create_res.status_code == 422:
            # Branch already exists
            return {
                "branch_name": branch_name,
                "base_branch": base_branch,
                "sha": base_sha,
                "created": False,
                "message": "Branch already exists",
            }
        else:
            raise BranchManagementError(
                f"Failed to create branch '{branch_name}': HTTP {create_res.status_code}"
            )

    if client is not None:
        return _execute(client)
    else:
        with httpx.Client(timeout=15.0) as http_client:
            return _execute(http_client)
