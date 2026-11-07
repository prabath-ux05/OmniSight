import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import InspectionForm from './components/InspectionForm';
import RunStatusCard from './components/RunStatusCard';
import FindingsSection from './components/FindingsSection';
import EvidenceSection from './components/EvidenceSection';
import InspectionHistoryTable from './components/InspectionHistoryTable';
import RepairProposalWorkflow from './components/RepairProposalWorkflow';
import Alert from './components/Alert';
import {
  fetchHealth,
  createInspectionRun,
  fetchRun,
  fetchInspectionRuns,
  fetchRunFindings,
  executeRunPipeline,
  fetchRunProposals,
  createRepairProposal,
  approveProposal,
  rejectProposal,
  repairRunFinding,
} from './services/api';
import './App.css';

const TERMINAL_STATUSES = ['completed', 'failed', 'cancelled'];

export default function App() {
  // Navigation tabs: 'live' | 'history' | 'proposals'
  const [activeTab, setActiveTab] = useState('live');

  // Backend health status
  const [health, setHealth] = useState(null);
  const [isHealthLoading, setIsHealthLoading] = useState(false);

  // Active run state
  const [currentRun, setCurrentRun] = useState(null);
  const [isRunLoading, setIsRunLoading] = useState(false);
  const [isAutoPolling, setIsAutoPolling] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  // Historical runs list (Day 4: GET /api/v1/runs)
  const [runsList, setRunsList] = useState([]);
  const [isRunsLoading, setIsRunsLoading] = useState(false);
  const [runsError, setRunsError] = useState('');

  // Findings state
  const [findings, setFindings] = useState(null);
  const [isFindingsLoading, setIsFindingsLoading] = useState(false);
  const [findingsError, setFindingsError] = useState('');
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [includeMockFindings, setIncludeMockFindings] = useState(false);

  // Repair Proposals state (Day 4 & 5: Review & Approval Workflow)
  const [proposalsList, setProposalsList] = useState([]);
  const [isProposalsLoading, setIsProposalsLoading] = useState(false);

  // Self-healing repairs state
  const [repairs, setRepairs] = useState({});
  const [repairingFindingId, setRepairingFindingId] = useState(null);
  const [repairError, setRepairError] = useState('');

  // Alerts & notifications
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Ref to prevent overlapping polling intervals
  const pollingTimerRef = useRef(null);

  // ---------------------------------------------------------------------------
  // 1. Backend Health Check
  // ---------------------------------------------------------------------------
  const checkHealth = useCallback(async () => {
    setIsHealthLoading(true);
    const result = await fetchHealth();
    if (result.ok) {
      setHealth(result.data);
    } else {
      setHealth({ status: 'offline', error: result.error });
    }
    setIsHealthLoading(false);
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // ---------------------------------------------------------------------------
  // 2. Fetch Historical Runs List (Day 4)
  // ---------------------------------------------------------------------------
  const loadRunsList = useCallback(async () => {
    setIsRunsLoading(true);
    setRunsError('');
    const result = await fetchInspectionRuns();
    if (result.ok) {
      setRunsList(result.data || []);
    } else {
      setRunsError(result.error);
    }
    setIsRunsLoading(false);
  }, []);

  useEffect(() => {
    loadRunsList();
  }, [loadRunsList]);

  // ---------------------------------------------------------------------------
  // 3. Fetch Repair Proposals for Run (Day 4 & 5)
  // ---------------------------------------------------------------------------
  const loadProposals = useCallback(async (runId) => {
    if (!runId) {
      setProposalsList([]);
      return;
    }
    setIsProposalsLoading(true);
    const result = await fetchRunProposals(runId);
    if (result.ok) {
      setProposalsList(result.data || []);
    } else {
      setProposalsList([]);
    }
    setIsProposalsLoading(false);
  }, []);

  // ---------------------------------------------------------------------------
  // 4. Fetch Findings
  // ---------------------------------------------------------------------------
  const loadFindings = useCallback(async (runId, useMock) => {
    if (!runId) return;
    setIsFindingsLoading(true);
    setFindingsError('');

    const result = await fetchRunFindings(runId, useMock);

    if (result.ok) {
      setFindings(result.data);
      if (Array.isArray(result.data) && result.data.length > 0) {
        setSelectedFinding(result.data[0]);
      } else {
        setSelectedFinding(null);
      }
    } else {
      setFindings(null);
      setSelectedFinding(null);
      setFindingsError(result.error);
    }

    setIsFindingsLoading(false);
  }, []);

  // ---------------------------------------------------------------------------
  // 5. Initiate a New Inspection Run
  // ---------------------------------------------------------------------------
  const handleStartInspection = async (targetUrl) => {
    setErrorMessage('');
    setSuccessMessage('');
    setIsRunLoading(true);
    setFindings(null);
    setSelectedFinding(null);
    setFindingsError('');
    setProposalsList([]);
    setRepairs({});
    setRepairError('');

    // Submit real POST /api/v1/runs?auto_execute=true
    const result = await createInspectionRun(targetUrl, true);

    if (result.ok) {
      const runData = result.data;
      setCurrentRun(runData);
      setSuccessMessage(
        `Run '${runData.run_id}' dispatched! Automated inspection pipeline active...`
      );

      // Start auto-polling until terminal status (completed/failed)
      if (!TERMINAL_STATUSES.includes(runData.status)) {
        setIsAutoPolling(true);
      } else {
        setIsAutoPolling(false);
      }

      await loadFindings(runData.run_id, includeMockFindings);
      await loadProposals(runData.run_id);
      loadRunsList();
    } else {
      setCurrentRun(null);
      setIsAutoPolling(false);
      setErrorMessage(result.error);
    }

    setIsRunLoading(false);
  };

  // ---------------------------------------------------------------------------
  // 6. Poll / Refresh Run Status
  // ---------------------------------------------------------------------------
  const handleRefreshRun = async (runId) => {
    if (!runId) return;
    setErrorMessage('');
    setIsRunLoading(true);

    const result = await fetchRun(runId);
    if (result.ok) {
      const updatedRun = result.data;
      setCurrentRun(updatedRun);

      if (TERMINAL_STATUSES.includes(updatedRun.status)) {
        setIsAutoPolling(false);
      }

      await loadFindings(runId, includeMockFindings);
      await loadProposals(runId);
      loadRunsList();
    } else {
      setIsAutoPolling(false);
      setErrorMessage(result.error);
    }

    setIsRunLoading(false);
  };

  // ---------------------------------------------------------------------------
  // 7. Look up an existing or unknown run ID
  // ---------------------------------------------------------------------------
  const handleLookupRun = async (runId) => {
    setErrorMessage('');
    setSuccessMessage('');
    setIsRunLoading(true);
    setFindings(null);
    setSelectedFinding(null);
    setFindingsError('');
    setProposalsList([]);
    setRepairs({});
    setRepairError('');

    const result = await fetchRun(runId);
    if (result.ok) {
      const runData = result.data;
      setCurrentRun(runData);
      setSuccessMessage(`Loaded run '${runData.run_id}'. Status: ${runData.status.toUpperCase()}.`);

      if (!TERMINAL_STATUSES.includes(runData.status)) {
        setIsAutoPolling(true);
      } else {
        setIsAutoPolling(false);
      }

      await loadFindings(runData.run_id, includeMockFindings);
      await loadProposals(runData.run_id);
      loadRunsList();
    } else {
      setCurrentRun(null);
      setIsAutoPolling(false);
      setErrorMessage(result.error);
    }

    setIsRunLoading(false);
  };

  // ---------------------------------------------------------------------------
  // 8. Execute Run Pipeline On Demand
  // ---------------------------------------------------------------------------
  const handleExecutePipeline = async (runId) => {
    if (!runId) return;
    setErrorMessage('');
    setIsExecuting(true);

    const result = await executeRunPipeline(runId);
    if (result.ok) {
      setCurrentRun(result.data);
      setSuccessMessage(`Inspection pipeline dispatched for run '${runId}'.`);
      setIsAutoPolling(true);
      loadRunsList();
    } else {
      setErrorMessage(result.error);
    }

    setIsExecuting(false);
  };

  // ---------------------------------------------------------------------------
  // 9. Select Run From Historical Table (Day 4)
  // ---------------------------------------------------------------------------
  const handleSelectRunFromHistory = async (run) => {
    setCurrentRun(run);
    setActiveTab('live');
    setErrorMessage('');
    setSuccessMessage(`Selected run '${run.run_id}' from history.`);

    if (!TERMINAL_STATUSES.includes(run.status)) {
      setIsAutoPolling(true);
    } else {
      setIsAutoPolling(false);
    }

    await loadFindings(run.run_id, includeMockFindings);
    await loadProposals(run.run_id);
  };

  // ---------------------------------------------------------------------------
  // 10. Repair Proposal Decision Handlers (Day 4 & 5)
  // ---------------------------------------------------------------------------
  const handleApproveProposal = async (proposalId, notes) => {
    setErrorMessage('');
    const result = await approveProposal(proposalId, notes);
    if (result.ok) {
      setSuccessMessage(
        `Proposal '${proposalId}' approved successfully! Review status updated to APPROVED.`
      );
      if (currentRun?.run_id) {
        await loadProposals(currentRun.run_id);
      }
      return true;
    } else {
      setErrorMessage(result.error || `Failed to approve proposal '${proposalId}'.`);
      return false;
    }
  };

  const handleRejectProposal = async (proposalId, notes) => {
    setErrorMessage('');
    const result = await rejectProposal(proposalId, notes);
    if (result.ok) {
      setSuccessMessage(
        `Proposal '${proposalId}' rejected. Review status updated to REJECTED.`
      );
      if (currentRun?.run_id) {
        await loadProposals(currentRun.run_id);
      }
      return true;
    } else {
      setErrorMessage(result.error || `Failed to reject proposal '${proposalId}'.`);
      return false;
    }
  };

  const handleCreateProposal = async (runId, payload) => {
    setErrorMessage('');
    const result = await createRepairProposal(runId, payload);
    if (result.ok) {
      setSuccessMessage(
        `Repair proposal '${result.data.proposal_id}' created successfully for run '${runId}'.`
      );
      await loadProposals(runId);
      return true;
    } else {
      setErrorMessage(result.error || 'Failed to create repair proposal.');
      return false;
    }
  };

  // ---------------------------------------------------------------------------
  // 11. Self-Healing Locator Repair Suggestion
  // ---------------------------------------------------------------------------
  const handleSuggestRepair = async (findingId, verifyLive = false) => {
    if (!currentRun?.run_id) return;
    setRepairingFindingId(findingId);
    setRepairError('');

    const result = await repairRunFinding(currentRun.run_id, findingId, verifyLive);
    if (result.ok && result.data) {
      const repairsList = Array.isArray(result.data) ? result.data : (result.data.repairs || []);
      const matched = repairsList.find((r) => r.finding_id === findingId) || repairsList[0];
      if (matched) {
        setRepairs((prev) => ({
          ...prev,
          [findingId]: matched,
        }));
      }
    } else {
      setRepairError(result.error || 'Failed to generate repair candidates.');
    }

    setRepairingFindingId(null);
  };

  // ---------------------------------------------------------------------------
  // 12. Polling Lifecycle Effect
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!currentRun?.run_id || !isAutoPolling) {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    if (TERMINAL_STATUSES.includes(currentRun.status)) {
      setIsAutoPolling(false);
      return;
    }

    // Poll every 2.5 seconds
    pollingTimerRef.current = setInterval(async () => {
      const result = await fetchRun(currentRun.run_id);
      if (result.ok) {
        const freshRun = result.data;
        setCurrentRun(freshRun);

        if (TERMINAL_STATUSES.includes(freshRun.status)) {
          setIsAutoPolling(false);
          await loadFindings(freshRun.run_id, includeMockFindings);
          await loadProposals(freshRun.run_id);
          loadRunsList();

          if (freshRun.status === 'completed') {
            setSuccessMessage(`Run '${freshRun.run_id}' completed successfully!`);
          } else if (freshRun.status === 'failed') {
            setErrorMessage(`Run '${freshRun.run_id}' failed: ${freshRun.error || freshRun.message || 'Inspection pipeline failure'}`);
          }
        }
      } else {
        setIsAutoPolling(false);
        setErrorMessage(`Polling stopped: ${result.error}`);
      }
    }, 2500);

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [currentRun?.run_id, currentRun?.status, isAutoPolling, includeMockFindings, loadFindings, loadProposals, loadRunsList]);

  // ---------------------------------------------------------------------------
  // 13. Toggle Mock Findings
  // ---------------------------------------------------------------------------
  const handleToggleMockFindings = () => {
    const nextValue = !includeMockFindings;
    setIncludeMockFindings(nextValue);
    if (currentRun?.run_id) {
      loadFindings(currentRun.run_id, nextValue);
    }
  };

  return (
    <div className="dashboard-layout">
      {/* 1. Header with OmniSight title and backend health */}
      <Header
        health={health}
        onRefreshHealth={checkHealth}
        isHealthLoading={isHealthLoading}
      />

      <main className="dashboard-container">
        {/* Navigation Tabs */}
        <nav className="dashboard-nav-tabs" aria-label="Dashboard views">
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'live' ? 'nav-tab-active' : ''}`}
            onClick={() => setActiveTab('live')}
          >
            🔍 Live Inspection &amp; Evidence
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'history' ? 'nav-tab-active' : ''}`}
            onClick={() => {
              setActiveTab('history');
              loadRunsList();
            }}
          >
            📋 Run History ({runsList.length})
          </button>
          <button
            type="button"
            className={`nav-tab-btn ${activeTab === 'proposals' ? 'nav-tab-active' : ''}`}
            onClick={() => {
              setActiveTab('proposals');
              if (currentRun?.run_id) {
                loadProposals(currentRun.run_id);
              }
            }}
          >
            🛡️ Repair Proposals ({proposalsList.length})
          </button>
        </nav>

        {/* Global Error & Success alerts */}
        {errorMessage && (
          <Alert
            type="error"
            message={errorMessage}
            onDismiss={() => setErrorMessage('')}
          />
        )}
        {successMessage && (
          <Alert
            type="success"
            message={successMessage}
            onDismiss={() => setSuccessMessage('')}
          />
        )}

        {/* TAB 1: Live Inspection View */}
        {activeTab === 'live' && (
          <>
            {/* Initiate inspection */}
            <InspectionForm
              onSubmit={handleStartInspection}
              isLoading={isRunLoading}
            />

            {/* Run status & controls */}
            <RunStatusCard
              run={currentRun}
              onRefresh={handleRefreshRun}
              isRefreshing={isRunLoading}
              isAutoPolling={isAutoPolling}
              onToggleAutoPolling={() => setIsAutoPolling((prev) => !prev)}
              onLookupRun={handleLookupRun}
              onExecutePipeline={handleExecutePipeline}
              isExecuting={isExecuting}
            />

            {/* Split grid: Findings list and Evidence / Screenshot */}
            <div className="dashboard-split-grid">
              <FindingsSection
                findings={findings}
                isLoading={isFindingsLoading}
                selectedFindingId={selectedFinding?.finding_id}
                onSelectFinding={(item) => setSelectedFinding(item)}
                runId={currentRun?.run_id}
                includeMock={includeMockFindings}
                onToggleMockFindings={handleToggleMockFindings}
                onRefreshFindings={() => loadFindings(currentRun?.run_id, includeMockFindings)}
                findingsError={findingsError}
                repairs={repairs}
                onSuggestRepair={handleSuggestRepair}
                repairingFindingId={repairingFindingId}
              />

              <EvidenceSection
                finding={selectedFinding}
                runId={currentRun?.run_id}
                repair={selectedFinding ? repairs[selectedFinding.finding_id] : null}
                isRepairing={selectedFinding && repairingFindingId === selectedFinding.finding_id}
                repairError={repairError}
                onSuggestRepair={(verifyLive) => selectedFinding && handleSuggestRepair(selectedFinding.finding_id, verifyLive)}
              />
            </div>

            {/* Quick banner linking to repair proposals if current run has findings */}
            {currentRun && (
              <div className="card proposals-shortcut-card">
                <div className="shortcut-content">
                  <div>
                    <h3 className="shortcut-title">Self-Healing Repair Proposals</h3>
                    <p className="shortcut-desc">
                      {proposalsList.length > 0
                        ? `${proposalsList.length} repair proposal(s) recorded for this run. Review and authorize fixes.`
                        : 'No repair proposals generated yet for this run. Draft or review repair proposals in the workflow tab.'}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => {
                      setActiveTab('proposals');
                      loadProposals(currentRun.run_id);
                    }}
                  >
                    Go to Repair Workflow ({proposalsList.length}) →
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* TAB 2: Inspection Run History */}
        {activeTab === 'history' && (
          <InspectionHistoryTable
            runs={runsList}
            isLoading={isRunsLoading}
            error={runsError}
            onRefresh={loadRunsList}
            onSelectRun={handleSelectRunFromHistory}
            selectedRunId={currentRun?.run_id}
          />
        )}

        {/* TAB 3: Repair Proposal Workflow */}
        {activeTab === 'proposals' && (
          <RepairProposalWorkflow
            run={currentRun}
            findings={findings || []}
            proposals={proposalsList}
            isLoading={isProposalsLoading}
            onRefreshProposals={() => currentRun && loadProposals(currentRun.run_id)}
            onApprove={handleApproveProposal}
            onReject={handleRejectProposal}
            onCreateProposal={handleCreateProposal}
          />
        )}
      </main>

      <footer className="dashboard-footer">
        <p>OmniSight &mdash; Multimodal UI Self-Healing &amp; RPA Agent Orchestration</p>
      </footer>
    </div>
  );
}
