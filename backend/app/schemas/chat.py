"""Pydantic schemas for OmniSight LLM conversational assistant."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single message in a conversational session."""

    role: str = Field(..., description="Role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message text content")


class ChatContextFinding(BaseModel):
    """Contextual defect finding metadata."""

    finding_id: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    selector: Optional[str] = None
    confidence: Optional[float] = None


class ChatContextRepair(BaseModel):
    """Contextual self-healing repair candidate."""

    repaired: Optional[bool] = None
    best_locator: Optional[str] = None
    strategy: Optional[str] = None
    confidence: Optional[float] = None
    reason: Optional[str] = None


class ChatContextProposal(BaseModel):
    """Contextual repair proposal."""

    proposal_id: Optional[str] = None
    approval_status: Optional[str] = None
    proposed_change: Optional[str] = None


class ChatContext(BaseModel):
    """Active inspection context attached to a chat request."""

    run_id: Optional[str] = None
    url: Optional[str] = None
    run_status: Optional[str] = None
    finding: Optional[ChatContextFinding] = None
    repair: Optional[ChatContextRepair] = None
    proposal: Optional[ChatContextProposal] = None


class ChatRequest(BaseModel):
    """Incoming user chat query with conversation history and optional context."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Natural-language question or prompt from the user",
    )
    history: list[ChatMessage] = Field(
        default_factory=list,
        description="Recent conversation turns for multi-turn context",
    )
    context: Optional[ChatContext] = Field(
        default=None,
        description="Optional active inspection run and finding context",
    )


class ChatResponse(BaseModel):
    """Model-generated assistant reply."""

    message: str = Field(..., description="Assistant text response")
    provider: str = Field(..., description="LLM provider: gemini, openai, or mock")
    model: str = Field(..., description="Model identifier used for inference")


class ChatStatusResponse(BaseModel):
    """LLM configuration and availability status."""

    configured: bool = Field(
        ...,
        description="Whether a valid LLM API key is present in backend environment",
    )
    provider: str = Field(..., description="Configured LLM provider")
    model: str = Field(..., description="Active model name")
    message: str = Field(
        ...,
        description="Readiness description or actionable configuration instructions",
    )
