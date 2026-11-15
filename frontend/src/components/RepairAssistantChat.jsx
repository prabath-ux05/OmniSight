import React, { useState, useEffect, useRef } from 'react';
import { fetchChatStatus, sendChatMessage } from '../services/api';

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
 * RepairAssistantChat
 *
 * Restored contextual AI chatbot assistant grounded in live inspection findings,
 * self-healing locator repairs, patch diffs, and verification proposals.
 */
export default function RepairAssistantChat({
  run = null,
  finding = null,
  repair = null,
  proposal = null,
  isOpen = true,
  onClose = null,
}) {
  const [chatMessages, setChatMessages] = useState([]);
  const [userInput, setUserInput] = useState('');
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [chatStatus, setChatStatus] = useState(null);
  const chatMessagesEndRef = useRef(null);
  const chatInputRef = useRef(null);

  // Check backend LLM status on mount
  useEffect(() => {
    fetchChatStatus().then((res) => {
      if (res.ok) {
        setChatStatus(res.data);
      }
    });
  }, []);

  // Update initial greeting when finding or proposal context changes
  useEffect(() => {
    if (finding || proposal) {
      const targetLabel = finding?.finding_id
        ? `finding #${finding.finding_id} (${finding.category?.replace(/_/g, ' ') || 'defect'})`
        : `proposal ${proposal?.proposal_id || 'active'}`;

      setChatMessages((prev) => {
        // If there is already an active conversation, do not overwrite user messages
        if (prev.length > 1) return prev;
        return [
          {
            id: `init-${finding?.finding_id || proposal?.proposal_id || Date.now()}`,
            sender: 'assistant',
            text: `Hello! I am the OmniSight AI Repair Assistant. I have loaded context for ${targetLabel}.\n\nYou can ask why this defect was detected, examine root cause factors, review synthesized locator repairs, or inspect the proposed code changes. You can also ask any test automation question!`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isInitial: true,
          },
        ];
      });
    } else {
      setChatMessages((prev) => {
        if (prev.length > 1) return prev;
        return [
          {
            id: 'init-default',
            sender: 'assistant',
            text: 'Welcome to the OmniSight Assistant! Ask me anything about your inspection runs, repair proposals, Playwright test automation, or locator healing.',
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            isInitial: true,
          },
        ];
      });
    }
  }, [finding?.finding_id, proposal?.proposal_id]);

  // Auto-scroll chat to latest message
  useEffect(() => {
    if (isOpen && chatMessagesEndRef.current) {
      chatMessagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isChatLoading, isOpen]);

  // Reset conversation
  const handleResetChat = () => {
    const targetLabel = finding?.finding_id
      ? `finding #${finding.finding_id}`
      : proposal?.proposal_id
      ? `proposal ${proposal.proposal_id}`
      : 'inspection';

    setChatMessages([
      {
        id: `init-reset-${Date.now()}`,
        sender: 'assistant',
        text: `Fresh conversation started for ${targetLabel}. What would you like to explore or troubleshoot?`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        isInitial: true,
      },
    ]);
    setUserInput('');
  };

  // Send message to real backend LLM
  const handleSendMessage = async (customText = null) => {
    const text = (customText || userInput).trim();
    if (!text || isChatLoading) return;

    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const historyPayload = chatMessages
      .filter((m) => !m.isInitial && !m.isError)
      .slice(-8)
      .map((m) => ({
        role: m.sender === 'user' ? 'user' : 'assistant',
        content: m.text,
      }));

    const contextPayload = {
      run_id: run?.run_id || null,
      url: run?.url || null,
      run_status: run?.status || null,
      finding: finding
        ? {
            finding_id: finding.finding_id,
            category: finding.category,
            severity: finding.severity,
            description: finding.description,
            selector: finding.selector,
            confidence: finding.confidence,
          }
        : null,
      repair: repair
        ? {
            repaired: repair.repaired,
            best_locator: repair.best_locator,
            strategy: repair.strategy,
            confidence: repair.confidence,
            reason: repair.reason,
          }
        : null,
      proposal: proposal
        ? {
            proposal_id: proposal.proposal_id,
            approval_status: proposal.approval_status,
            proposed_change: proposal.proposed_change,
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

  if (!isOpen) return null;

  return (
    <div className="repair-assistant-pane card" aria-label="AI Repair Assistant">
      <div className="assistant-card-header">
        <div className="assistant-header-left">
          <div className="assistant-avatar">🤖</div>
          <div>
            <h4 className="assistant-title">OmniSight Repair Assistant</h4>
            <span className="assistant-model-pill">
              {chatStatus?.configured ? (
                <>✨ {chatStatus.provider === 'openai' ? 'OpenAI' : 'Google Gemini'} ({chatStatus.model || 'live'})</>
              ) : (
                <>⚡ Contextual Grounded Assistant</>
              )}
            </span>
          </div>
        </div>

        <div className="assistant-header-actions">
          <button
            type="button"
            className="btn btn-secondary btn-xs btn-new-chat"
            onClick={handleResetChat}
            title="Start a fresh conversation"
          >
            ✨ New Chat
          </button>
          {onClose && (
            <button
              type="button"
              className="btn btn-secondary btn-xs btn-close-chat"
              onClick={onClose}
              title="Close assistant panel"
              aria-label="Close Assistant"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {chatStatus && !chatStatus.configured && (
        <div className="assistant-limitation-notice">
          <span className="notice-icon">ℹ️</span>
          <div className="notice-text">
            <strong>LLM Notice:</strong> Add <code>GEMINI_API_KEY</code> to backend environment to enable live Gemini completions.
          </div>
        </div>
      )}

      {/* Quick Question Chips */}
      <div className="assistant-quick-chips">
        <button
          type="button"
          className="quick-chip-btn"
          onClick={() => handleSendMessage('Why was this issue detected? Explain what caused the defect.')}
          disabled={isChatLoading}
        >
          ❓ Why detected?
        </button>
        <button
          type="button"
          className="quick-chip-btn"
          onClick={() => handleSendMessage('Explain the root cause of this defect and why it occurred.')}
          disabled={isChatLoading}
        >
          🔍 Root cause?
        </button>
        <button
          type="button"
          className="quick-chip-btn"
          onClick={() => handleSendMessage('What is the recommended locator repair candidate and why is it resilient?')}
          disabled={isChatLoading}
        >
          ⚡ Recommended fix?
        </button>
        <button
          type="button"
          className="quick-chip-btn"
          onClick={() => handleSendMessage('How does this proposed patch resolve the issue in our test suite?')}
          disabled={isChatLoading}
        >
          📝 Explain patch?
        </button>
        <button
          type="button"
          className="quick-chip-btn"
          onClick={() => handleSendMessage('How does the human-in-the-loop review and approval gate work?')}
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
                      ⚠️ Check API key configuration
                    </span>
                  ) : (
                    <span className="bubble-grounded-tag">
                      ✓ Grounded context &bull; {msg.provider === 'openai' ? 'OpenAI' : 'Google Gemini'} ({msg.model || 'live'})
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

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
                <span className="thinking-label">Consulting LLM with inspection context...</span>
              </div>
            </div>
          </div>
        )}
        <div ref={chatMessagesEndRef} />
      </div>

      {/* Input Bar */}
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
          placeholder="Ask a question about this defect, repairs, or verification (Enter to send, Shift+Enter for newline)..."
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
  );
}
