import React, { useState, useEffect, useMemo, useRef } from 'react';
import VisualComparisonSplitView from './VisualComparisonSplitView';
import { FindingRepairWorkflow, RunProposalsDashboard } from './RepairProposalWorkflow';
import { fetchChatStatus, getArtifactUrl, repairRunFinding, sendChatMessage } from '../services/api';

/**
 * Strategy human-readable label helper.
 */
function getStrategyLabel(strategy) {
  switch (strategy) {
    case 'data_attribute':
      return 'Data Attribute (data-testid / data-cy)';
    case 'stable_id':
      return 'Stable Semantic ID';
    case 'accessible_role_name':
      return 'Accessible Role / Name';
    case 'unique_text':
      return 'Unique Text Content';
    case 'semantic_css':
      return 'Semantic Tag + Class';
    case 'hierarchical':
      return 'Hierarchical Scope';
    default:
      return strategy || 'Deterministic Heuristic';
  }
}

/**
 * Format timestamp helper.
 */
function formatTime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return isNaN(d.getTime()) ? isoString : d.toLocaleString();
  } catch {
    return isoString;
  }
}

/**
 * Format inline markdown code blocks and bold text.
 */
function formatInlineCode(line) {
  if (!line) return null;
  const parts = line.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      return <code key={i} className="chat-inline-code">{part.slice(1, -1)}</code>;
    }
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

/**
 * Render multi-line markdown text with code and bullets.
 */
function renderMarkdownContent(text) {
  if (!text) return null;
  return text.split('\n').map((line, idx) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('•') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      return (
        <p key={idx} className="bubble-line bubble-bullet">
          {formatInlineCode(line)}
        </p>
      );
    }
    return (
      <p key={idx} className="bubble-line">
        {formatInlineCode(line)}
      </p>
    );
  });
}

/**
 * Extract filename from artifact path.
 */
function extractFilename(p, fallback) {
  if (!p) return null;
  const clean = p.replace(/\\/g, '/');
  const name = clean.substring(clean.lastIndexOf('/') + 1);
  return name || fallback;
}

/**
 * Generate deterministic assistant answer grounded strictly in verified inspection facts.
 * NO generative AI hallucination.
 */
function generateGroundedAnswer(questionText, finding, repair, proposal, run) {
  const lower = questionText.toLowerCase();

  // 1. Why was this detected / reason
  if (lower.includes('why') || lower.includes('detect') || lower.includes('flag') || lower.includes('issue')) {
    let answer = `Finding ${finding ? finding.finding_id : 'current'} was detected during the automated inspection of ${run?.url || 'the target page'}.\n\n`;
    answer += `• Category: ${finding?.category || 'UI Defect'}\n`;
    answer += `• Severity: ${(finding?.severity || 'medium').toUpperCase()}\n`;
    answer += `• Description: ${finding?.description || 'Layout defect or missing element'}\n`;
    if (finding?.selector) {
      answer += `• Target Selector: \`${finding.selector}\`\n`;
    }
    if (finding?.confidence) {
      answer += `• Detection Confidence: ${Math.round(finding.confidence * 100)}%\n`;
    }
    answer += `\nThe Vision & DOM analysis engine identified that the element matching this locator was either absent from the DOM snapshot or visually occluded/misaligned.`;
    return answer;
  }

  // 2. Root cause
  if (lower.includes('root') || lower.includes('cause') || lower.includes('reason') || lower.includes('fail')) {
    let answer = `Root-Cause Breakdown:\n\n`;
    if (finding?.category === 'missing_visible_element') {
      answer += `• Failure Mechanism: The test suite or automation script queried \`${finding?.selector || 'the target locator'}\`, but zero visible matching nodes were resolved in the captured DOM snapshot.\n`;
      answer += `• Common Causes: Markup refactoring, dynamic class renaming (e.g. Tailwind/CSS-in-JS hashing), or element migration inside a new container.\n`;
    } else if (finding?.category === 'layout_shift_or_overflow') {
      answer += `• Failure Mechanism: Horizontal viewport overflow or overlapping layout boundary detected beyond standard screen bounds.\n`;
    } else if (finding?.category === 'broken_image_or_asset') {
      answer += `• Failure Mechanism: Image or asset failed to load (HTTP 404/broken src attribute) or rendered with zero natural width/height.\n`;
    } else {
      answer += `• Failure Mechanism: Visual regression or DOM mismatch identified against baseline expectation.\n`;
    }
    if (repair?.reason) {
      answer += `• Self-Healing Engine Note: "${repair.reason}"\n`;
    }
    return answer;
  }

  // 3. Recommended fix / repair
  if (lower.includes('fix') || lower.includes('repair') || lower.includes('recommend') || lower.includes('locator') || lower.includes('suggest')) {
    if (!repair) {
      return `No repair candidate has been synthesized yet for finding ${finding?.finding_id}.\n\nTo generate recommended locators, click "Suggest Locator Repair" in the workspace. OmniSight's deterministic engine will scan the DOM snapshot for stable attributes like data-testid, semantic IDs, accessible roles, and unique text.`;
    }
    if (!repair.repaired && (!repair.candidates || repair.candidates.length === 0)) {
      return `The Self-Healing Engine analyzed finding ${finding?.finding_id}, but could not find a uniquely resolvable replacement candidate.\n\nReason: ${repair.reason || 'No unique DOM match found'}.\nManual inspection of the DOM snapshot is recommended.`;
    }
    let answer = `Recommended Locator Repair:\n\n`;
    answer += `• Best Candidate: \`${repair.best_locator}\`\n`;
    answer += `• Resilience Strategy: ${getStrategyLabel(repair.strategy)}\n`;
    answer += `• Resilience Score: ${Math.round((repair.confidence || 0) * 100)}%\n`;
    if (repair.validation) {
      answer += `• Snapshot Validation: ${repair.validation.is_valid ? 'Unique (1 match) in DOM ✓' : `${repair.validation.matches} matches`}\n`;
    }
    if (repair.live_verification?.attempted) {
      answer += `• Live Page Verification: ${repair.live_verification.is_verified ? 'Verified on live page ✓' : 'Failed live verification'}\n`;
    }
    if (repair.candidate_locators && repair.candidate_locators.length > 1) {
      answer += `\nAlternative Candidates Evaluated (${repair.candidate_locators.length}):\n`;
      repair.candidate_locators.slice(1, 4).forEach((c, idx) => {
        answer += `  ${idx + 1}. \`${c.selector}\` (${getStrategyLabel(c.strategy)} - ${Math.round(c.confidence * 100)}%)\n`;
      });
    }
    return answer;
  }

  // 4. Code changes / diffs
  if (lower.includes('code') || lower.includes('diff') || lower.includes('change') || lower.includes('patch') || lower.includes('file')) {
    let answer = `Proposed Code Modification:\n\n`;
    answer += `The repair workflow generates a minimal, unified diff targeting your test suite (e.g. \`tests/e2e/test_checkout.py\`).\n`;
    answer += `• Replace: \`${finding?.selector || 'old_selector'}\`\n`;
    answer += `• With: \`${repair?.best_locator || 'new_resilient_selector'}\`\n\n`;
    answer += `This modification is created strictly in memory. It will never overwrite local files directly without explicit review and approval.`;
    return answer;
  }

  // 5. Approval / PR / Governance
  if (lower.includes('approv') || lower.includes('pr') || lower.includes('pull request') || lower.includes('github') || lower.includes('submit')) {
    let answer = `Human-in-the-Loop Governance & PR Flow:\n\n`;
    answer += `1. Review: Review the proposed locator and unified diff in Step 2.\n`;
    answer += `2. Explicit Approval: You must explicitly check the confirmation gate checkbox ("Explicit Approval: I authorize creating a repair branch").\n`;
    answer += `3. Simulation vs Live: You can run in Simulation Mode (dry-run without modifying GitHub) or create a real remote GitHub PR if configured.\n`;
    answer += `4. Pull Request: Once submitted, the PR URL and branch name are recorded in the audit log.`;
    return answer;
  }

  // Fallback answer
  return `OmniSight Deterministic Assistant:\n\nCurrently inspecting finding ${finding ? finding.finding_id : 'N/A'}.\n\nAvailable facts for this defect:\n• Target Element: \`${finding?.selector || 'N/A'}\`\n• Category: ${finding?.category || 'N/A'}\n• Best Locator: ${repair?.best_locator ? `\`${repair.best_locator}\`` : 'Not yet generated'}\n\nPlease select one of the quick prompts above to inspect root causes, repair suggestions, diffs, or PR governance.`;
}

/**
 * RepairWorkspacePage renders the complete Batch 6 Repair Workspace.
 */
export default function RepairWorkspacePage({
  run = null,
  runsList = [],
  onSelectRun = () => {},
  findings = [],
  isFindingsLoading = false,
  selectedFinding = null,
  onSelectFinding = () => {},
  repairs = {},
  repairingFindingId = null,
  repairError = '',
  onSuggestRepair = () => {},
  proposals = [],
  isProposalsLoading = false,
  onRefreshProposals = () => {},
  onApproveProposal = async () => false,
  onRejectProposal = async () => false,
  onCreateProposal = async () => false,
  onSelectView = () => {},
}) {
  // Active workflow mode: 'single-finding' | 'run-proposals'
  const [activeWorkflowTab, setActiveWorkflowTab] = useState('single-finding');

  // Preview tab: 'before' | 'after'
  const [activePreviewTab, setActivePreviewTab] = useState('before');

  // Local finding selection fallback
  const currentFinding = useMemo(() => {
    if (selectedFinding) return selectedFinding;
    if (findings && findings.length > 0) return findings[0];
    return null;
  }, [selectedFinding, findings]);

  // Current repair candidate for current finding
  const currentRepair = useMemo(() => {
    if (!currentFinding?.finding_id) return null;
    return repairs[currentFinding.finding_id] || null;
  }, [repairs, currentFinding?.finding_id]);

  // Proposal for current finding if any
  const currentProposal = useMemo(() => {
    if (!currentFinding?.finding_id || !Array.isArray(proposals)) return null;
    return proposals.find((p) => p.finding_id === currentFinding.finding_id) || null;
  }, [proposals, currentFinding?.finding_id]);

  // Visual Evidence paths
  const evidence = currentFinding?.evidence || {};
  const screenshotFilename = extractFilename(evidence.screenshot_path, 'before.png');
  const domFilename = extractFilename(evidence.dom_snapshot_path, 'dom.html');

  const beforeScreenshotUrl = run?.run_id && screenshotFilename
    ? getArtifactUrl(run.run_id, screenshotFilename)
    : null;

  const domSnapshotUrl = run?.run_id && domFilename
    ? getArtifactUrl(run.run_id, domFilename)
    : null;

  // Screenshot image loading states
  const [isImageLoading, setIsImageLoading] = useState(true);
  const [imageError, setImageError] = useState(false);

  // Chatbot conversation state
  const [chatMessages, setChatMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatStatus, setChatStatus] = useState(null);
  const chatMessagesEndRef = useRef(null);
  const chatInputRef = useRef(null);

  // Check LLM readiness on mount
  useEffect(() => {
    fetchChatStatus().then((res) => {
      if (res.ok) {
        setChatStatus(res.data);
      }
    });
  }, []);

  // Initialize or reset chat conversation when selected finding changes
  useEffect(() => {
    if (currentFinding) {
      setChatMessages([
        {
          id: `init-${currentFinding.finding_id}`,
          sender: 'assistant',
          text: `Hello! I am the OmniSight Conversational Assistant. I have loaded context for finding #${currentFinding.finding_id} (${currentFinding.category?.replace(/_/g, ' ') || 'defect'}).\n\nYou can ask why this issue was detected, examine root cause factors, review synthesized locator repairs, or inspect proposed test code diffs. You can also ask any technical or general question!`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isInitial: true,
        },
      ]);
    } else {
      setChatMessages([
        {
          id: 'init-none',
          sender: 'assistant',
          text: 'Welcome to the OmniSight Assistant! Ask me anything about your inspection runs, self-healing repairs, Playwright test automation, or web locator strategies.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isInitial: true,
        },
      ]);
    }
  }, [currentFinding?.finding_id]);

  // Auto-scroll chat to latest message
  useEffect(() => {
    if (chatMessagesEndRef.current) {
      chatMessagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isChatLoading]);

  // Reset conversation to a clean state
  const handleResetChat = () => {
    if (currentFinding) {
      setChatMessages([
        {
          id: `init-${currentFinding.finding_id}-${Date.now()}`,
          sender: 'assistant',
          text: `Fresh conversation started for finding #${currentFinding.finding_id}. What would you like to explore or troubleshoot?`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isInitial: true,
        },
      ]);
    } else {
      setChatMessages([
        {
          id: `init-none-${Date.now()}`,
          sender: 'assistant',
          text: 'Fresh conversation started. Ask me anything about OmniSight, defect diagnosis, or test automation.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isInitial: true,
        },
      ]);
    }
    setUserInput('');
  };

  // Send message in chat to real LLM backend
  const handleSendMessage = async (messageText) => {
    const text = (messageText || userInput).trim();
    if (!text || isChatLoading) return;

    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    // Filter recent history for multi-turn conversational context
    const historyPayload = chatMessages
      .filter((m) => !m.isInitial && !m.isError)
      .slice(-8)
      .map((m) => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.text,
      }));

    // Active inspection context
    const contextPayload = {
      run_id: run?.run_id || null,
      url: run?.url || null,
      run_status: run?.status || null,
      finding: currentFinding
        ? {
            finding_id: currentFinding.finding_id,
            category: currentFinding.category,
            severity: currentFinding.severity,
            description: currentFinding.description,
            selector: currentFinding.selector,
            confidence: currentFinding.confidence,
          }
        : null,
      repair: currentRepair
        ? {
            repaired: currentRepair.repaired,
            best_locator: currentRepair.best_locator,
            strategy: currentRepair.strategy,
            confidence: currentRepair.confidence,
            reason: currentRepair.reason,
          }
        : null,
      proposal: currentProposal
        ? {
            proposal_id: currentProposal.proposal_id,
            approval_status: currentProposal.approval_status,
            proposed_change: currentProposal.proposed_change,
          }
        : null,
    };

    setChatMessages((prev) => [...prev, userMsg]);
    setUserInput('');
    setIsChatLoading(true);

    const result = await sendChatMessage({
      message: text,
      history: historyPayload,
      context: contextPayload,
    });

    if (result.ok && result.data?.message) {
      const assistantMsg = {
        id: `asst-${Date.now() + 1}`,
        sender: 'assistant',
        text: result.data.message,
        provider: result.data.provider,
        model: result.data.model,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: false,
      };
      setChatMessages((prev) => [...prev, assistantMsg]);
    } else {
      const errorMsg = {
        id: `asst-err-${Date.now() + 1}`,
        sender: 'assistant',
        text: result.error || 'Failed to reach AI assistant. Please verify backend LLM credentials.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isError: true,
      };
      setChatMessages((prev) => [...prev, errorMsg]);
    }

    setIsChatLoading(false);
  };

  // Quick question handler
  const handleQuickQuestion = (question) => {
    handleSendMessage(question);
  };

  // Local live verification trigger
  const [isVerifyingLive, setIsVerifyingLive] = useState(false);
  const handleTriggerLiveVerify = async () => {
    if (!run?.run_id || !currentFinding?.finding_id) return;
    setIsVerifyingLive(true);
    await onSuggestRepair(currentFinding.finding_id, true);
    setIsVerifyingLive(false);
    setActivePreviewTab('after');
  };

  return (
    <div className="repair-workspace-container">
      {/* 1. Repair Workspace Hero Banner */}
      <div className="repair-hero-banner">
        <div className="repair-hero-content">
          <div className="repair-hero-badge-row">
            <span className="repair-hero-badge">Autonomous Self-Healing</span>
            <span className="repair-governance-badge">Human-in-the-Loop Governance</span>
          </div>
          <h2 className="repair-hero-title">Repair Workspace &amp; Assistant</h2>
          <p className="repair-hero-desc">
            Diagnose visual defect findings, converse with the grounded repair assistant, generate safe minimal test code diffs, and review pull-request proposals with human approval gates.
          </p>
        </div>

        {/* Run Selector Context Bar */}
        <div className="repair-run-context-bar">
          <div className="context-item">
            <span className="context-label">Active Run:</span>
            {run ? (
              <span className="context-val font-mono">{run.run_id}</span>
            ) : (
              <span className="context-val text-muted">No run selected</span>
            )}
          </div>

          <div className="context-item context-url-item">
            <span className="context-label">Target URL:</span>
            {run?.url ? (
              <a
                href={run.url}
                target="_blank"
                rel="noopener noreferrer"
                className="context-link"
                title={run.url}
              >
                {run.url} ↗
              </a>
            ) : (
              <span className="context-val text-muted">—</span>
            )}
          </div>

          <div className="context-item">
            <span className="context-label">Findings:</span>
            <span className="context-val badge-neutral">
              {Array.isArray(findings) ? findings.length : 0}
            </span>
          </div>

          <div className="context-item">
            <span className="context-label">Proposals:</span>
            <span className="context-val badge-neutral">
              {Array.isArray(proposals) ? proposals.length : 0}
            </span>
          </div>

          {runsList.length > 1 && (
            <div className="context-item context-switch-item">
              <label htmlFor="repair-run-switcher" className="context-label">Switch Run:</label>
              <select
                id="repair-run-switcher"
                className="form-select form-select-xs"
                value={run?.run_id || ''}
                onChange={(e) => {
                  const target = runsList.find((r) => r.run_id === e.target.value);
                  if (target) onSelectRun(target);
                }}
              >
                {runsList.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id} ({r.status})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </div>

      {/* 2. Empty State when No Run is Active */}
      {!run ? (
        <div className="card repair-empty-state-card">
          <div className="empty-state">
            <span className="empty-icon">🛡️</span>
            <h3 className="empty-title">No Inspection Run Loaded</h3>
            <p className="empty-state-text">
              Please launch an inspection run or select a historical audit run to access self-healing locator repairs and proposal governance.
            </p>
            <div className="empty-action-group">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => onSelectView('inspection')}
              >
                🔍 Go to Live Studio
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onSelectView('history')}
              >
                📋 Browse Run History
              </button>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* 3. Finding Selector Tabs / Bar */}
          {findings && findings.length > 0 ? (
            <div className="repair-finding-selector-card">
              <div className="finding-selector-header">
                <span className="finding-selector-title">Select Finding to Heal:</span>
                <span className="finding-selector-count">
                  {findings.length} defect{findings.length === 1 ? '' : 's'} recorded
                </span>
              </div>

              <div className="finding-pills-row">
                {findings.map((f, idx) => {
                  const isSelected = currentFinding?.finding_id === f.finding_id;
                  const sevClass = `badge-sev-${f.severity || 'medium'}`;
                  return (
                    <button
                      key={f.finding_id || idx}
                      type="button"
                      className={`finding-pill-btn ${isSelected ? 'active' : ''}`}
                      onClick={() => onSelectFinding(f)}
                    >
                      <span className={`finding-sev-dot ${sevClass}`}></span>
                      <span className="finding-pill-id">#{f.finding_id}</span>
                      <span className="finding-pill-cat">{f.category?.replace(/_/g, ' ')}</span>
                      {repairs[f.finding_id]?.repaired && (
                        <span className="finding-healed-check" title="Candidate locator synthesized">✓</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : run?.status === 'failed' ? (
            <div className="card repair-clean-run-card" style={{ borderColor: 'var(--color-danger, #ef4444)' }}>
              <div className="clean-check-icon" style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>✕</div>
              <h4 className="clean-title" style={{ color: '#ef4444' }}>Inspection Run Failed</h4>
              <p className="empty-state-text">
                Run <code>{run.run_id}</code> encountered an error and could not complete inspection: {run.error || run.message || 'Pipeline execution failed'}.
              </p>
            </div>
          ) : (
            <div className="card repair-clean-run-card">
              <div className="clean-check-icon">✓</div>
              <h4 className="clean-title">Zero Defects In This Run</h4>
              <p className="empty-state-text">
                Run <code>{run.run_id}</code> completed cleanly with no locator regressions or visual anomalies.
              </p>
            </div>
          )}

          {/* 4. Active Finding Detail Card */}
          {currentFinding && (
            <div className="repair-finding-detail-card">
              <div className="finding-detail-header">
                <div className="finding-detail-title-group">
                  <div className="finding-detail-badges">
                    <span className={`badge badge-sev-${currentFinding.severity || 'medium'}`}>
                      {(currentFinding.severity || 'medium').toUpperCase()}
                    </span>
                    <span className="badge badge-category">
                      {currentFinding.category?.replace(/_/g, ' ')}
                    </span>
                    <span className="finding-id-pill font-mono">
                      ID: {currentFinding.finding_id}
                    </span>
                  </div>
                  <h3 className="finding-detail-heading">{currentFinding.description}</h3>
                </div>

                <div className="finding-detail-actions">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => onSuggestRepair(currentFinding.finding_id, false)}
                    disabled={repairingFindingId === currentFinding.finding_id}
                  >
                    {repairingFindingId === currentFinding.finding_id
                      ? 'Synthesizing...'
                      : currentRepair?.repaired
                      ? '🔄 Re-Analyze Candidates'
                      : '⚡ Synthesize Locator Fix'}
                  </button>
                </div>
              </div>

              {/* Target Selector & Root Cause Details */}
              <div className="finding-meta-grid">
                <div className="finding-meta-item">
                  <span className="meta-label">Failed / Missing Selector:</span>
                  <div className="meta-selector-box">
                    <code className="font-mono selector-text">
                      {currentFinding.selector || 'Global layout scope'}
                    </code>
                  </div>
                </div>

                <div className="finding-meta-item">
                  <span className="meta-label">Detection Confidence:</span>
                  <span className="meta-val">
                    {typeof currentFinding.confidence === 'number'
                      ? `${Math.round(currentFinding.confidence * 100)}%`
                      : '—'}
                  </span>
                </div>

                <div className="finding-meta-item">
                  <span className="meta-label">Self-Healing Status:</span>
                  <span className="meta-val">
                    {currentRepair?.repaired ? (
                      <span className="text-success font-semibold">
                        ✓ Candidate Synthesized ({Math.round((currentRepair.confidence || 0) * 100)}% resilience)
                      </span>
                    ) : currentRepair ? (
                      <span className="text-warning">Repair Inconclusive</span>
                    ) : (
                      <span className="text-muted">Awaiting Diagnosis</span>
                    )}
                  </span>
                </div>

                <div className="finding-meta-item">
                  <span className="meta-label">Root Cause Rationale:</span>
                  <span className="meta-val root-cause-text">
                    {currentRepair?.reason ||
                      (currentFinding.category === 'missing_visible_element'
                        ? 'Target locator failed to resolve in DOM snapshot or was hidden from layout.'
                        : 'Visual regression or viewport boundary discrepancy.')}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* 5. Two-Column Workspace: Chatbot Assistant (Left) + Evidence / Website Preview (Right) */}
          <div className="repair-workspace-dual-grid">
            {/* LEFT PANE: Chatbot / Conversational Assistant */}
            <div className="repair-assistant-pane card">
              <div className="assistant-card-header">
                <div className="assistant-header-left">
                  <span className="assistant-icon">🤖</span>
                  <div>
                    <h4 className="assistant-title">OmniSight AI Assistant</h4>
                    <span className="assistant-grounding-pill">
                      {chatStatus?.configured ? (
                        <>✨ Powered by {chatStatus.provider === 'openai' ? 'OpenAI' : 'Google Gemini'} ({chatStatus.model})</>
                      ) : (
                        <>⚡ Grounded LLM Assistant</>
                      )}
                    </span>
                  </div>
                </div>

                <div className="assistant-header-actions">
                  <button
                    type="button"
                    className="btn btn-secondary btn-xs btn-new-chat"
                    onClick={handleResetChat}
                    title="Start a new conversation session"
                  >
                    ✨ New Chat
                  </button>
                </div>
              </div>

              {/* Status Notice if LLM credentials are not configured */}
              {chatStatus && !chatStatus.configured && (
                <div className="assistant-limitation-notice">
                  <span className="notice-icon">⚠️</span>
                  <div className="notice-text">
                    <strong>LLM Setup Notice:</strong> Backend API key is not currently detected. Add <code>GEMINI_API_KEY</code> to your backend environment to enable live Gemini completions.
                  </div>
                </div>
              )}

              {/* Quick Questions Chips */}
              <div className="assistant-quick-chips">
                <button
                  type="button"
                  className="quick-chip-btn"
                  onClick={() => handleQuickQuestion('Why was this issue detected? Explain what caused the locator failure.')}
                  disabled={isChatLoading}
                >
                  ❓ Why detected?
                </button>
                <button
                  type="button"
                  className="quick-chip-btn"
                  onClick={() => handleQuickQuestion('Explain the root cause of this defect and common reasons for it.')}
                  disabled={isChatLoading}
                >
                  🔍 Root cause?
                </button>
                <button
                  type="button"
                  className="quick-chip-btn"
                  onClick={() => handleQuickQuestion('What is the recommended locator repair candidate and why is it resilient?')}
                  disabled={isChatLoading}
                >
                  ⚡ Recommended fix?
                </button>
                <button
                  type="button"
                  className="quick-chip-btn"
                  onClick={() => handleQuickQuestion('How would this locator repair be applied as a test code diff?')}
                  disabled={isChatLoading}
                >
                  📝 Code diff?
                </button>
                <button
                  type="button"
                  className="quick-chip-btn"
                  onClick={() => handleQuickQuestion('How does the human-in-the-loop approval gate and pull request flow work?')}
                  disabled={isChatLoading}
                >
                  🛡️ Approval rules?
                </button>
              </div>

              {/* Chat Messages Stream */}
              <div className="assistant-chat-stream">
                {chatMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`chat-bubble-row ${msg.sender === 'user' ? 'bubble-user' : 'bubble-assistant'}`}
                  >
                    <div className={`chat-bubble ${msg.isError ? 'bubble-error' : ''}`}>
                      <div className="bubble-header">
                        <span className="bubble-sender">
                          {msg.sender === 'user' ? 'You' : 'OmniSight Assistant'}
                        </span>
                        <span className="bubble-time">{msg.timestamp}</span>
                      </div>
                      <div className="bubble-content">
                        {renderMarkdownContent(msg.text)}
                      </div>
                      {msg.sender === 'assistant' && !msg.isInitial && (
                        <div className="bubble-footer">
                          {msg.isError ? (
                            <span className="bubble-error-tag" style={{ color: '#ef4444', fontSize: '0.7rem' }}>
                              ⚠️ Service guidance: Check API key configuration
                            </span>
                          ) : (
                            <span className="bubble-grounded-tag">
                              ✓ Verified against inspection context &bull; {msg.provider === 'openai' ? 'OpenAI' : 'Google Gemini'} ({msg.model || 'LLM'})
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {/* Animated Thinking Bubble */}
                {isChatLoading && (
                  <div className="chat-bubble-row bubble-assistant">
                    <div className="chat-bubble bubble-thinking">
                      <div className="bubble-header">
                        <span className="bubble-sender">OmniSight Assistant</span>
                        <span className="bubble-time">Thinking...</span>
                      </div>
                      <div className="bubble-content thinking-indicator">
                        <span className="thinking-dot"></span>
                        <span className="thinking-dot"></span>
                        <span className="thinking-dot"></span>
                        <span className="thinking-label">Consulting LLM &amp; analyzing inspection context...</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatMessagesEndRef} />
              </div>

              {/* Chat Input Bar with Multiline Support */}
              <form
                className="assistant-input-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
              >
                <textarea
                  ref={chatInputRef}
                  className="form-input assistant-input assistant-textarea"
                  placeholder="Ask any question about this defect, repairs, Playwright, or general testing (Enter to send, Shift+Enter for newline)..."
                  value={userInput}
                  rows={1}
                  disabled={isChatLoading}
                  onChange={(e) => setUserInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSendMessage();
                    }
                  }}
                />
                <button
                  type="submit"
                  className="btn btn-primary btn-sm btn-send"
                  disabled={!userInput.trim() || isChatLoading}
                >
                  {isChatLoading ? 'Thinking...' : 'Send ➔'}
                </button>
              </form>
            </div>

            {/* RIGHT PANE: Website Evidence & Preview (Before vs After) */}
            <div className="repair-preview-pane card">
              <div className="preview-card-header">
                <div className="preview-header-left">
                  <h4 className="preview-title">Visual Evidence &amp; Verification Preview</h4>
                  <p className="preview-subtitle">
                    Examine captured defect evidence and verified repair outcomes.
                  </p>
                </div>

                <div className="preview-tab-controls">
                  <button
                    type="button"
                    className={`preview-tab-btn ${activePreviewTab === 'split' ? 'active' : ''}`}
                    onClick={() => setActivePreviewTab('split')}
                  >
                    Split-View Comparison ↔
                  </button>
                  <button
                    type="button"
                    className={`preview-tab-btn ${activePreviewTab === 'before' ? 'active' : ''}`}
                    onClick={() => setActivePreviewTab('before')}
                  >
                    Original Evidence (Before)
                  </button>
                  <button
                    type="button"
                    className={`preview-tab-btn ${activePreviewTab === 'after' ? 'active' : ''}`}
                    onClick={() => setActivePreviewTab('after')}
                  >
                    Repaired Preview (After)
                  </button>
                </div>
              </div>

              {/* Tab 0: Visual Comparison Split View */}
              {activePreviewTab === 'split' && (
                <div className="preview-content-box preview-split-box">
                  {currentProposal?.proposal_id || (proposals && proposals[0]?.proposal_id) ? (
                    <VisualComparisonSplitView
                      runId={run?.run_id}
                      proposalId={currentProposal?.proposal_id || proposals[0]?.proposal_id}
                      finding={currentFinding}
                      initialViewport={currentFinding?.viewport || 'desktop'}
                      onDecisionUpdated={() => {
                        if (refreshProposals) refreshProposals();
                      }}
                    />
                  ) : (
                    <div className="preview-fallback-box">
                      <span className="fallback-icon">🛡️</span>
                      <h5 className="fallback-heading">No Active Proposal for Split-View</h5>
                      <p className="fallback-text">
                        Split-view visual comparison compares the original defect screenshot with the proposed repair in a controlled sandbox.
                        Select or draft a repair proposal on the left to inspect visual differences and record approval decisions.
                      </p>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 1: Before Evidence */}
              {activePreviewTab === 'before' && (
                <div className="preview-content-box">
                  <div className="preview-meta-row">
                    <span className="preview-status-pill badge-danger">
                      Defective State (Before Patch)
                    </span>
                    {beforeScreenshotUrl && !imageError && (
                      <a
                        href={beforeScreenshotUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-link btn-link-sm"
                      >
                        Open Full Screenshot ↗
                      </a>
                    )}
                  </div>

                  <div className="preview-viewport-box">
                    {beforeScreenshotUrl && !imageError ? (
                      <div className="preview-img-container">
                        {isImageLoading && (
                          <div className="screenshot-loading-spinner">
                            <span className="spinner-sm"></span>
                            <span>Loading viewport screenshot...</span>
                          </div>
                        )}
                        <img
                          src={beforeScreenshotUrl}
                          alt="Before Defect Viewport"
                          className={`preview-img ${isImageLoading ? 'preview-img-hidden' : ''}`}
                          onLoad={() => setIsImageLoading(false)}
                          onError={() => {
                            setIsImageLoading(false);
                            setImageError(true);
                          }}
                        />
                      </div>
                    ) : (
                      <div className="preview-fallback-box">
                        <span className="fallback-icon">🖼️</span>
                        <h5 className="fallback-heading">Screenshot Artifact Not Found On Disk</h5>
                        <p className="fallback-text">
                          {evidence.screenshot_path ? (
                            <>
                              Expected at: <code>{evidence.screenshot_path}</code>
                              <br />
                              The Browser Agent has not yet captured this viewport file or it was moved.
                            </>
                          ) : (
                            'No visual screenshot artifact path was recorded for this finding.'
                          )}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* DOM snapshot & affected element snippet */}
                  <div className="preview-artifact-links">
                    <div className="artifact-link-item">
                      <span className="artifact-label">DOM Snapshot:</span>
                      {domSnapshotUrl ? (
                        <a
                          href={domSnapshotUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-link btn-link-sm"
                        >
                          View Captured HTML ↗
                        </a>
                      ) : (
                        <span className="text-muted">None recorded</span>
                      )}
                    </div>

                    <div className="artifact-link-item">
                      <span className="artifact-label">Live Target:</span>
                      {run?.url ? (
                        <a
                          href={run.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-link btn-link-sm"
                        >
                          Open Live Page ↗
                        </a>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: After Evidence / Verification Preview */}
              {activePreviewTab === 'after' && (
                <div className="preview-content-box">
                  {/* Strict Requirement: Never display a successful repaired preview unless backend confirms verification */}
                  {currentRepair?.live_verification?.is_verified ||
                  currentProposal?.verification_status === 'verified_success' ? (
                    <div className="verification-success-box">
                      <div className="verification-header">
                        <span className="verification-check-icon">✓</span>
                        <div>
                          <h5 className="verification-title">Live Fresh-Page Verification Succeeded!</h5>
                          <span className="verification-badge badge-success">
                            Verified on Live Target
                          </span>
                        </div>
                      </div>

                      <div className="verification-details-grid">
                        <div className="verify-detail-item">
                          <span className="detail-label">Verified Target URL:</span>
                          <span className="detail-val font-mono">
                            {currentRepair.live_verification.target_url || run?.url}
                          </span>
                        </div>
                        <div className="verify-detail-item">
                          <span className="detail-label">Resolved Element Tag:</span>
                          <span className="detail-val font-mono">
                            &lt;{currentRepair.live_verification.resolved_tag || 'element'}&gt;
                          </span>
                        </div>
                        <div className="verify-detail-item">
                          <span className="detail-label">DOM Unique Matches:</span>
                          <span className="detail-val">
                            {currentRepair.live_verification.matches} (Exactly 1 expected)
                          </span>
                        </div>
                        <div className="verify-detail-item">
                          <span className="detail-label">Validation Message:</span>
                          <span className="detail-val">
                            {currentRepair.live_verification.validation_message}
                          </span>
                        </div>
                      </div>

                      <p className="verification-note">
                        Candidate locator <code>{currentRepair.best_locator}</code> was tested against the live webpage and uniquely resolved the intended element.
                      </p>
                    </div>
                  ) : (
                    <div className="verification-pending-box">
                      <div className="pending-icon-row">
                        <span className="pending-icon">⏳</span>
                        <span className="badge badge-warning">Verification Pending</span>
                      </div>
                      <h5 className="pending-title">Post-Repair Preview Withheld</h5>
                      <p className="pending-desc">
                        OmniSight enforces strict empirical verification: a repaired preview is <strong>never displayed</strong> unless the backend executes a fresh browser session and confirms successful element resolution.
                      </p>

                      <div className="pending-status-checklist">
                        <div className="check-item">
                          <span className="check-bullet">•</span>
                          <span>Candidate Locator Synthesized: {currentRepair?.repaired ? '✓ Yes' : '— Pending'}</span>
                        </div>
                        <div className="check-item">
                          <span className="check-bullet">•</span>
                          <span>Snapshot DOM Resolution: {currentRepair?.validation?.is_valid ? '✓ Validated' : '— Pending'}</span>
                        </div>
                        <div className="check-item">
                          <span className="check-bullet">•</span>
                          <span>Live Page Browser Verification: {currentRepair?.live_verification?.attempted ? 'Attempted' : '— Not yet run'}</span>
                        </div>
                      </div>

                      <div className="pending-actions">
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={handleTriggerLiveVerify}
                          disabled={isVerifyingLive || !currentFinding?.finding_id}
                        >
                          {isVerifyingLive ? 'Testing Live Page...' : '🚀 Test Candidate Against Live Page'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 6. Human-in-the-Loop Workflow Tabs: Single-Finding Workflow vs Full Run Proposals */}
          <div className="repair-governance-section">
            <div className="governance-tab-bar">
              <button
                type="button"
                className={`gov-tab-btn ${activeWorkflowTab === 'single-finding' ? 'active' : ''}`}
                onClick={() => setActiveWorkflowTab('single-finding')}
              >
                🛠️ Single Finding Patch &amp; PR Workflow
              </button>
              <button
                type="button"
                className={`gov-tab-btn ${activeWorkflowTab === 'run-proposals' ? 'active' : ''}`}
                onClick={() => setActiveWorkflowTab('run-proposals')}
              >
                📋 Run Proposals Review &amp; Decisions ({proposals.length})
              </button>
            </div>

            <div className="governance-tab-content">
              {activeWorkflowTab === 'single-finding' ? (
                currentFinding ? (
                  <FindingRepairWorkflow
                    finding={currentFinding}
                    runId={run?.run_id}
                    repair={currentRepair}
                  />
                ) : (
                  <div className="empty-state">
                    <p className="empty-state-text">Select a finding above to generate a patch and review proposals.</p>
                  </div>
                )
              ) : (
                <RunProposalsDashboard
                  run={run}
                  findings={findings || []}
                  proposals={proposals}
                  isLoading={isProposalsLoading}
                  onRefreshProposals={onRefreshProposals}
                  onApprove={onApproveProposal}
                  onReject={onRejectProposal}
                  onCreateProposal={onCreateProposal}
                />
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
