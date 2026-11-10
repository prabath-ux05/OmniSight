import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import HomePage from './components/HomePage';
import InspectionPage from './components/InspectionPage';
import InspectionForm from './components/InspectionForm';
import RunStatusCard from './components/RunStatusCard';
import FindingsSection from './components/FindingsSection';
import EvidenceSection from './components/EvidenceSection';
import InspectionHistoryTable from './components/InspectionHistoryTable';
import HistoryPage from './components/HistoryPage';
import RepairWorkspacePage from './components/RepairWorkspacePage';
import RepairProposalWorkflow from './components/RepairProposalWorkflow';
import AboutPage from './components/AboutPage';
import SettingsPage from './components/SettingsPage';
import GuidedTutorial, { TUTORIAL_STEPS } from './components/GuidedTutorial';
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

  // Shared Application Shell view: 'home' | 'inspection' | 'history' | 'repair' | 'about' | 'settings'
  const [currentView, setCurrentView] = useState('inspection');

  // Responsive navigation drawer state
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  // Theme foundation: 'dark' | 'light' | 'system'
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('omnisight_theme') || 'system';
    } catch {
      return 'system';
    }
  });

  // Authenticated user session state (null when not logged in - strictly no fake sessions)
  const [user, setUser] = useState(null);

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
  const [infoMessage, setInfoMessage] = useState('');

  // Guided Onboarding Tour state (Batch 7)
  const [hasCompletedTour, setHasCompletedTour] = useState(() => {
    try {
      return localStorage.getItem('omnisight_tour_completed') === 'true';
    } catch {
      return false;
    }
  });
  const [isTourOpen, setIsTourOpen] = useState(() => {
    try {
      return localStorage.getItem('omnisight_tour_completed') !== 'true';
    } catch {
      return false;
    }
  });
  const [tourStep, setTourStep] = useState(0);

  // Ref to prevent overlapping polling intervals
  const pollingTimerRef = useRef(null);

  // Refs to track active run requests and prevent stale async race conditions
  const activeFindingsRunIdRef = useRef(null);
  const activeProposalsRunIdRef = useRef(null);
  const findingsSeqRef = useRef(0);
  const proposalsSeqRef = useRef(0);

  // ---------------------------------------------------------------------------
  // Theme Management & Persistence
  // ---------------------------------------------------------------------------
  useEffect(() => {
    try {
      if (theme === 'dark') {
        document.documentElement.setAttribute('data-theme', 'dark');
      } else if (theme === 'light') {
        document.documentElement.setAttribute('data-theme', 'light');
      } else {
        document.documentElement.removeAttribute('data-theme');
      }
      localStorage.setItem('omnisight_theme', theme);
    } catch {
      // Safely ignore storage quotas or sandboxed iframe restrictions
    }
  }, [theme]);

  const handleToggleTheme = () => {
    setTheme((prev) => {
      if (prev === 'system') return 'dark';
      if (prev === 'dark') return 'light';
      return 'system';
    });
  };

  // Close navigation drawer when Escape key is pressed
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isMenuOpen) {
        setIsMenuOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isMenuOpen]);

  // Auth Action Handlers (Optional Sign In / Sign Up triggers)
  const handleSignIn = () => {
    setInfoMessage('Authentication Not Configured: No backend authentication service or user session exists. OmniSight operates in full Guest Mode — all inspection, history, and repair workflows are completely unlocked.');
  };

  const handleSignUp = () => {
    setInfoMessage('Account Registration Not Configured: No user database is provisioned. OmniSight is fully unlocked in Guest Mode without requiring an account.');
  };

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
      activeProposalsRunIdRef.current = null;
      proposalsSeqRef.current += 1;
      setProposalsList([]);
      setIsProposalsLoading(false);
      return;
    }

    activeProposalsRunIdRef.current = runId;
    const currentSeq = ++proposalsSeqRef.current;
    setIsProposalsLoading(true);

    try {
      const result = await fetchRunProposals(runId);
      // Discard stale response if active run has switched or newer request dispatched
      if (activeProposalsRunIdRef.current === runId && proposalsSeqRef.current === currentSeq) {
        if (result.ok) {
          setProposalsList(result.data || []);
        } else {
          setProposalsList([]);
        }
      }
    } catch {
      if (activeProposalsRunIdRef.current === runId && proposalsSeqRef.current === currentSeq) {
        setProposalsList([]);
      }
    } finally {
      if (activeProposalsRunIdRef.current === runId && proposalsSeqRef.current === currentSeq) {
        setIsProposalsLoading(false);
      }
    }
  }, []);

  // ---------------------------------------------------------------------------
  // 4. Fetch Findings
  // ---------------------------------------------------------------------------
  const loadFindings = useCallback(async (runId, useMock) => {
    if (!runId) {
      activeFindingsRunIdRef.current = null;
      findingsSeqRef.current += 1;
      setFindings(null);
      setSelectedFinding(null);
      setFindingsError('');
      setIsFindingsLoading(false);
      return;
    }

    activeFindingsRunIdRef.current = runId;
    const currentSeq = ++findingsSeqRef.current;
    setIsFindingsLoading(true);
    setFindingsError('');

    try {
      const result = await fetchRunFindings(runId, useMock);
      // Discard stale response if active run has switched or newer request dispatched
      if (activeFindingsRunIdRef.current === runId && findingsSeqRef.current === currentSeq) {
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
      }
    } catch (err) {
      if (activeFindingsRunIdRef.current === runId && findingsSeqRef.current === currentSeq) {
        setFindings(null);
        setSelectedFinding(null);
        setFindingsError(err?.message || 'Failed to fetch findings');
      }
    } finally {
      if (activeFindingsRunIdRef.current === runId && findingsSeqRef.current === currentSeq) {
        setIsFindingsLoading(false);
      }
    }
  }, []);

  // ---------------------------------------------------------------------------
  // 5. Initiate a New Inspection Run
  // ---------------------------------------------------------------------------
  const handleStartInspection = async (targetUrl) => {
    // Invalidate outstanding findings/proposals requests from any previous run
    activeFindingsRunIdRef.current = null;
    activeProposalsRunIdRef.current = null;
    findingsSeqRef.current += 1;
    proposalsSeqRef.current += 1;

    setErrorMessage('');
    setSuccessMessage('');
    setIsRunLoading(true);
    setFindings(null);
    setSelectedFinding(null);
    setFindingsError('');
    setIsFindingsLoading(false);
    setProposalsList([]);
    setIsProposalsLoading(false);
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
      const runStatus = typeof runData?.status === 'string' ? runData.status.trim().toLowerCase() : '';
      if (!TERMINAL_STATUSES.includes(runStatus)) {
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

  const handleStartInspectionFromHome = async (targetUrl) => {
    setCurrentView('inspection');
    setActiveTab('live');
    await handleStartInspection(targetUrl);
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

      const updatedStatus = typeof updatedRun?.status === 'string' ? updatedRun.status.trim().toLowerCase() : '';
      if (TERMINAL_STATUSES.includes(updatedStatus)) {
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
    // Invalidate outstanding findings/proposals requests from any previous run
    activeFindingsRunIdRef.current = null;
    activeProposalsRunIdRef.current = null;
    findingsSeqRef.current += 1;
    proposalsSeqRef.current += 1;

    setErrorMessage('');
    setSuccessMessage('');
    setIsRunLoading(true);
    setFindings(null);
    setSelectedFinding(null);
    setFindingsError('');
    setIsFindingsLoading(false);
    setProposalsList([]);
    setIsProposalsLoading(false);
    setRepairs({});
    setRepairError('');

    const result = await fetchRun(runId);
    if (result.ok) {
      const runData = result.data;
      setCurrentRun(runData);
      const lookupStatus = typeof runData?.status === 'string' ? runData.status.trim().toLowerCase() : '';
      setSuccessMessage(`Loaded run '${runData.run_id}'. Status: ${lookupStatus ? lookupStatus.toUpperCase() : 'UNKNOWN'}.`);

      if (!TERMINAL_STATUSES.includes(lookupStatus)) {
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
  // View Routing & Sub-Tab Synchronization
  // ---------------------------------------------------------------------------
  const handleSelectView = (viewId) => {
    setIsMenuOpen(false);
    if (viewId === 'home') {
      setCurrentView('home');
    } else if (viewId === 'inspection' || viewId === 'live') {
      setCurrentView('inspection');
      setActiveTab('live');
    } else if (viewId === 'history') {
      setCurrentView('history');
      setActiveTab('history');
      loadRunsList();
    } else if (viewId === 'repair' || viewId === 'proposals') {
      setCurrentView('repair');
      setActiveTab('proposals');
      if (currentRun?.run_id) {
        loadProposals(currentRun.run_id);
      }
    } else if (viewId === 'about') {
      setCurrentView('about');
    } else if (viewId === 'settings') {
      setCurrentView('settings');
    }
  };

  const handleNavigateToRepair = (finding) => {
    if (finding) {
      setSelectedFinding(finding);
    }
    handleSelectView('repair');
  };

  // ---------------------------------------------------------------------------
  // Guided Onboarding Tour Handlers (Batch 7)
  // ---------------------------------------------------------------------------
  const handleTourNext = () => {
    const nextStep = Math.min(tourStep + 1, TUTORIAL_STEPS.length - 1);
    const targetView = TUTORIAL_STEPS[nextStep]?.viewId;
    if (targetView && targetView !== currentView) {
      handleSelectView(targetView);
    }
    setTourStep(nextStep);
  };

  const handleTourPrev = () => {
    const prevStep = Math.max(tourStep - 1, 0);
    const targetView = TUTORIAL_STEPS[prevStep]?.viewId;
    if (targetView && targetView !== currentView) {
      handleSelectView(targetView);
    }
    setTourStep(prevStep);
  };

  const handleTourSkip = () => {
    setIsTourOpen(false);
    setHasCompletedTour(true);
    try {
      localStorage.setItem('omnisight_tour_completed', 'true');
    } catch {}
  };

  const handleTourFinish = () => {
    setIsTourOpen(false);
    setHasCompletedTour(true);
    try {
      localStorage.setItem('omnisight_tour_completed', 'true');
    } catch {}
    setSuccessMessage('🎉 Onboarding tour completed! You are ready to run inspections and heal defect locators.');
  };

  const handleTourJumpToStep = (index) => {
    const clampedIndex = Math.max(0, Math.min(index, TUTORIAL_STEPS.length - 1));
    const targetView = TUTORIAL_STEPS[clampedIndex]?.viewId;
    if (targetView && targetView !== currentView) {
      handleSelectView(targetView);
    }
    setTourStep(clampedIndex);
  };

  const handleReplayTour = () => {
    setTourStep(0);
    setIsTourOpen(true);
    handleSelectView('home');
  };

  // ---------------------------------------------------------------------------
  // 9. Select Run & Synchronize State
  // ---------------------------------------------------------------------------
  const handleSelectRun = async (run, targetView = null) => {
    if (!run?.run_id) return;

    // Immediately cancel/invalidate in-flight requests for prior runs or overlapping requests
    activeFindingsRunIdRef.current = run.run_id;
    activeProposalsRunIdRef.current = run.run_id;
    findingsSeqRef.current += 1;
    proposalsSeqRef.current += 1;

    // Clear prior run state immediately to prevent cross-run data bleed
    setFindings(null);
    setSelectedFinding(null);
    setFindingsError('');
    setIsFindingsLoading(false);
    setProposalsList([]);
    setIsProposalsLoading(false);
    setRepairs({});
    setRepairError('');

    setCurrentRun(run);
    if (targetView) {
      handleSelectView(targetView);
    }

    setErrorMessage('');
    setSuccessMessage(`Selected run '${run.run_id}'.`);

    const historyRunStatus = typeof run?.status === 'string' ? run.status.trim().toLowerCase() : '';
    if (!TERMINAL_STATUSES.includes(historyRunStatus)) {
      setIsAutoPolling(true);
    } else {
      setIsAutoPolling(false);
    }

    await loadFindings(run.run_id, includeMockFindings);
    await loadProposals(run.run_id);
  };

  const handleSelectRunFromHistory = (run) => {
    handleSelectRun(run, 'inspection');
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

    const currentStatusNormalized = typeof currentRun?.status === 'string' ? currentRun.status.trim().toLowerCase() : '';
    if (TERMINAL_STATUSES.includes(currentStatusNormalized)) {
      setIsAutoPolling(false);
      return;
    }

    // Poll every 2.5 seconds
    pollingTimerRef.current = setInterval(async () => {
      const result = await fetchRun(currentRun.run_id);
      if (result.ok) {
        const freshRun = result.data;
        setCurrentRun(freshRun);

        const freshStatus = typeof freshRun?.status === 'string' ? freshRun.status.trim().toLowerCase() : '';
        if (TERMINAL_STATUSES.includes(freshStatus)) {
          setIsAutoPolling(false);
          await loadFindings(freshRun.run_id, includeMockFindings);
          await loadProposals(freshRun.run_id);
          loadRunsList();

          if (freshStatus === 'completed') {
            setSuccessMessage(`Run '${freshRun.run_id}' completed successfully!`);
          } else if (freshStatus === 'failed') {
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
      {/* 1. Shared Header with branding, navigation, health, theme & auth */}
      <Header
        health={health}
        onRefreshHealth={checkHealth}
        isHealthLoading={isHealthLoading}
        currentView={currentView}
        onSelectView={handleSelectView}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        user={user}
        onSignIn={handleSignIn}
        onSignUp={handleSignUp}
        isMenuOpen={isMenuOpen}
        onToggleMenu={() => setIsMenuOpen((prev) => !prev)}
      />

      <main className="dashboard-container">
        {/* Secondary Sub-navigation Tabs (for Inspection, History & Repair views) */}
        {['inspection', 'live', 'history', 'repair', 'proposals'].includes(currentView) && (
          <nav className="dashboard-nav-tabs" aria-label="Dashboard views">
            <button
              type="button"
              className={`nav-tab-btn ${activeTab === 'live' ? 'nav-tab-active' : ''}`}
              onClick={() => handleSelectView('inspection')}
            >
              🔍 Live Inspection &amp; Evidence
            </button>
            <button
              type="button"
              className={`nav-tab-btn ${activeTab === 'history' ? 'nav-tab-active' : ''}`}
              onClick={() => handleSelectView('history')}
            >
              📋 Run History ({runsList.length})
            </button>
            <button
              type="button"
              className={`nav-tab-btn ${activeTab === 'proposals' ? 'nav-tab-active' : ''}`}
              onClick={() => handleSelectView('repair')}
            >
              🛡️ Repair Proposals ({proposalsList.length})
            </button>
          </nav>
        )}

        {/* Global Error, Success & Info alerts */}
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
        {infoMessage && (
          <Alert
            type="info"
            message={infoMessage}
            onDismiss={() => setInfoMessage('')}
          />
        )}

        {/* VIEW 1: Polished Home Landing View */}
        {currentView === 'home' && (
          <HomePage
            health={health}
            isHealthLoading={isHealthLoading}
            onRefreshHealth={checkHealth}
            runsList={runsList}
            isRunsLoading={isRunsLoading}
            runsError={runsError}
            onRefreshRuns={loadRunsList}
            currentRun={currentRun}
            onStartInspection={handleStartInspectionFromHome}
            isRunLoading={isRunLoading}
            onSelectView={handleSelectView}
            onSelectRun={handleSelectRunFromHistory}
          />
        )}

        {/* VIEW 2: Dedicated Live Inspection Studio */}
        {(currentView === 'inspection' || (currentView !== 'home' && currentView !== 'about' && currentView !== 'settings' && activeTab === 'live')) && (
          <InspectionPage
            onStartInspection={handleStartInspection}
            isRunLoading={isRunLoading}
            currentRun={currentRun}
            onRefreshRun={handleRefreshRun}
            isAutoPolling={isAutoPolling}
            onToggleAutoPolling={() => setIsAutoPolling((prev) => !prev)}
            onLookupRun={handleLookupRun}
            onExecutePipeline={handleExecutePipeline}
            isExecuting={isExecuting}
            findings={findings}
            isFindingsLoading={isFindingsLoading}
            findingsError={findingsError}
            selectedFinding={selectedFinding}
            onSelectFinding={(item) => setSelectedFinding(item)}
            includeMockFindings={includeMockFindings}
            onToggleMockFindings={handleToggleMockFindings}
            onRefreshFindings={() => loadFindings(currentRun?.run_id, includeMockFindings)}
            repairs={repairs}
            onSuggestRepair={handleSuggestRepair}
            repairingFindingId={repairingFindingId}
            repairError={repairError}
            proposalsCount={proposalsList.length}
            onNavigateToRepair={handleNavigateToRepair}
            onSelectView={handleSelectView}
          />
        )}

        {/* VIEW 3: Dedicated Inspection Run History Page */}
        {(currentView === 'history' || (currentView !== 'home' && currentView !== 'about' && currentView !== 'settings' && activeTab === 'history')) && (
          <HistoryPage
            runs={runsList}
            isLoading={isRunsLoading}
            error={runsError}
            onRefresh={loadRunsList}
            onSelectRun={handleSelectRunFromHistory}
            selectedRunId={currentRun?.run_id}
            currentRun={currentRun}
            findings={findings}
            isFindingsLoading={isFindingsLoading}
            onSelectView={handleSelectView}
            includeMockFindings={includeMockFindings}
          />
        )}

        {/* VIEW 4: Dedicated Self-Healing Repair Workspace & Assistant */}
        {(currentView === 'repair' || (currentView !== 'home' && currentView !== 'about' && currentView !== 'settings' && activeTab === 'proposals')) && (
          <RepairWorkspacePage
            run={currentRun}
            runsList={runsList}
            onSelectRun={(targetRun) => handleSelectRun(targetRun, 'repair')}
            findings={findings || []}
            isFindingsLoading={isFindingsLoading}
            selectedFinding={selectedFinding}
            onSelectFinding={(f) => setSelectedFinding(f)}
            repairs={repairs}
            repairingFindingId={repairingFindingId}
            repairError={repairError}
            onSuggestRepair={handleSuggestRepair}
            proposals={proposalsList}
            isProposalsLoading={isProposalsLoading}
            onRefreshProposals={() => currentRun && loadProposals(currentRun.run_id)}
            onApproveProposal={handleApproveProposal}
            onRejectProposal={handleRejectProposal}
            onCreateProposal={handleCreateProposal}
            onSelectView={handleSelectView}
          />
        )}

        {/* VIEW 5: Dedicated About & Architecture Documentation */}
        {currentView === 'about' && (
          <AboutPage
            onSelectView={handleSelectView}
            onStartTour={handleReplayTour}
          />
        )}

        {/* VIEW 6: Dedicated Settings Page */}
        {currentView === 'settings' && (
          <SettingsPage
            theme={theme}
            onSelectTheme={setTheme}
            hasCompletedTour={hasCompletedTour}
            onReplayTour={handleReplayTour}
            health={health}
            isHealthLoading={isHealthLoading}
            onCheckHealth={checkHealth}
            includeMockFindings={includeMockFindings}
            onToggleMockFindings={handleToggleMockFindings}
            onSelectView={handleSelectView}
          />
        )}
      </main>

      {/* 6-Step Guided Onboarding Tour Overlay */}
      <GuidedTutorial
        isOpen={isTourOpen}
        currentStepIndex={tourStep}
        onNext={handleTourNext}
        onPrev={handleTourPrev}
        onSkip={handleTourSkip}
        onFinish={handleTourFinish}
        onJumpToStep={handleTourJumpToStep}
      />

      <footer className="dashboard-footer">
        <p>OmniSight &mdash; Multimodal UI Self-Healing &amp; RPA Agent Orchestration</p>
      </footer>
    </div>
  );
}
