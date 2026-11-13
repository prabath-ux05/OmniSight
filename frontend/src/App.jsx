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
import AuthModal from './components/AuthModal';
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
  fetchCurrentUser,
  logoutUser,
} from './services/api';
import { MAX_CONSECUTIVE_POLL_ERRORS } from './utils/findingsState';
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
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMode, setAuthModalMode] = useState('login');

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
  const pollingErrorCountRef = useRef(0);

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

  // Auth Action Handlers & Session Lifecycle
  useEffect(() => {
    let isCancelled = false;
    const checkAuthSession = async () => {
      const res = await fetchCurrentUser();
      if (!isCancelled) {
        if (res.ok && res.data) {
          setUser(res.data);
        } else {
          setUser(null);
        }
      }
    };
    checkAuthSession();
    return () => {
      isCancelled = true;
    };
  }, []);

  const handleSignIn = () => {
    setAuthModalMode('login');
    setIsAuthModalOpen(true);
  };

  const handleSignUp = () => {
    setAuthModalMode('register');
    setIsAuthModalOpen(true);
  };

  const handleAuthSuccess = (userData) => {
    setUser(userData);
    setSuccessMessage(`Signed in successfully as ${userData.email}.`);
    loadRunsList();
  };

  const handleLogout = async () => {
    await logoutUser();
    setUser(null);
    setSuccessMessage('Logged out successfully.');
    loadRunsList();
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
  const handleStartInspection = async (targetUrl, viewports = ['desktop']) => {
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

    // Submit real POST /api/v1/runs?auto_execute=true with selected viewports
    const result = await createInspectionRun(targetUrl, true, viewports);

    if (result.ok) {
      const runData = result.data;
      setCurrentRun(runData);
      const vpsStr = Array.isArray(viewports) && viewports.length > 1 ? ` across ${viewports.join(', ')}` : '';
      setSuccessMessage(
        `Run '${runData.run_id}' dispatched${vpsStr}! Automated inspection pipeline active...`
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

  const handleStartInspectionFromHome = async (targetUrl, viewports = ['desktop']) => {
    setCurrentView('inspection');
    setActiveTab('live');
    await handleStartInspection(targetUrl, viewports);
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
    } else if (viewId === 'profile') {
      setCurrentView('profile');
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
  // 12. Polling Lifecycle Effect (Recursive setTimeout to prevent overlapping requests)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!currentRun?.run_id || !isAutoPolling) {
      if (pollingTimerRef.current) {
        clearTimeout(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    const currentStatusNormalized = typeof currentRun?.status === 'string' ? currentRun.status.trim().toLowerCase() : '';
    if (TERMINAL_STATUSES.includes(currentStatusNormalized)) {
      setIsAutoPolling(false);
      return;
    }

    let isCancelled = false;
    const POLLING_INTERVAL_MS = 2500;

    const executePoll = async () => {
      if (isCancelled) return;

      try {
        const result = await fetchRun(currentRun.run_id);
        if (isCancelled) return;

        if (result.ok) {
          pollingErrorCountRef.current = 0;
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
            return; // Terminal reached: stop scheduling further polls
          }
        } else {
          // Distinct Handling: Genuine 404 (Missing Run) vs Transient Gateway/Network Errors
          if (result.status === 404) {
            setIsAutoPolling(false);
            pollingErrorCountRef.current = 0;
            setErrorMessage(`Polling stopped: Run '${currentRun.run_id}' was not found on the server (404 Not Found).`);
            return; // 404: stop scheduling further polls
          }

          pollingErrorCountRef.current += 1;
          const currentFailures = pollingErrorCountRef.current;

          if (currentFailures >= MAX_CONSECUTIVE_POLL_ERRORS) {
            setIsAutoPolling(false);
            pollingErrorCountRef.current = 0;
            setErrorMessage(
              `Polling paused: Server unavailable after ${MAX_CONSECUTIVE_POLL_ERRORS} attempts (${result.error}). Click 'Refresh' to retry.`
            );
            return; // Error threshold reached: stop scheduling further polls
          } else {
            console.warn(
              `Transient polling error for run '${currentRun.run_id}' (attempt ${currentFailures}/${MAX_CONSECUTIVE_POLL_ERRORS}): ${result.error}`
            );
          }
        }
      } catch (err) {
        if (isCancelled) return;
        pollingErrorCountRef.current += 1;
        if (pollingErrorCountRef.current >= MAX_CONSECUTIVE_POLL_ERRORS) {
          setIsAutoPolling(false);
          pollingErrorCountRef.current = 0;
          setErrorMessage(
            `Polling paused: Unexpected error after ${MAX_CONSECUTIVE_POLL_ERRORS} attempts. Click 'Refresh' to retry.`
          );
          return;
        }
      }

      // Schedule next poll only after current request finishes and if not cancelled
      if (!isCancelled) {
        pollingTimerRef.current = setTimeout(executePoll, POLLING_INTERVAL_MS);
      }
    };

    // Kick off initial poll after the interval
    pollingTimerRef.current = setTimeout(executePoll, POLLING_INTERVAL_MS);

    return () => {
      isCancelled = true;
      if (pollingTimerRef.current) {
        clearTimeout(pollingTimerRef.current);
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
        onLoginSignUp={handleSignIn}
        isMenuOpen={isMenuOpen}
        onToggleMenu={() => setIsMenuOpen((prev) => !prev)}
        onCloseMenu={() => setIsMenuOpen(false)}
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
        {(currentView === 'inspection' || (currentView !== 'home' && currentView !== 'about' && currentView !== 'profile' && currentView !== 'settings' && activeTab === 'live')) && (
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
        {(currentView === 'history' || (currentView !== 'home' && currentView !== 'about' && currentView !== 'profile' && currentView !== 'settings' && activeTab === 'history')) && (
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
        {(currentView === 'repair' || (currentView !== 'home' && currentView !== 'about' && currentView !== 'profile' && currentView !== 'settings' && activeTab === 'proposals')) && (
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

        {/* VIEW 6: Dedicated User Profile Center (Batch 1.1) */}
        {currentView === 'profile' && (
          <div className="shell-view-container profile-view-container">
            <section className="shell-hero-card" aria-label="User Profile Header">
              <div className="shell-hero-badge">👤 User Profile</div>
              <h2 className="shell-hero-title">Account &amp; Profile Center</h2>
              <p className="shell-hero-desc">
                Manage your OmniSight identity, active session status, and workspace preferences.
              </p>
            </section>

            <div className="card settings-section-card">
              <div className="card-header">
                <h3 className="card-title">👤 Account &amp; Session Status</h3>
                <p className="card-description">
                  Current authentication and session state across OmniSight services.
                </p>
              </div>

              {user ? (
                <div className="profile-details-card">
                  <div className="profile-details-avatar-row">
                    {user.avatar || user.avatarUrl || user.picture ? (
                      <img
                        src={user.avatar || user.avatarUrl || user.picture}
                        alt={user.name || user.firstName || 'User'}
                        className="profile-details-avatar-img"
                      />
                    ) : (
                      <div className="user-profile-avatar profile-large-avatar">
                        {user.firstName?.charAt(0).toUpperCase() || user.name?.charAt(0).toUpperCase() || 'U'}
                      </div>
                    )}
                    <div className="profile-details-info">
                      <h4 className="profile-details-name">{user.name || user.firstName || 'User'}</h4>
                      <p className="profile-details-email">{user.email || 'No email associated'}</p>
                      <div className="profile-badge-row">
                        <span className="badge badge-success">Authenticated</span>
                        <span className="badge badge-neutral">User ID: {user.id || 'Active'}</span>
                      </div>
                    </div>
                  </div>

                  <div className="profile-section-divider"></div>

                  <div className="profile-details-grid">
                    <div className="profile-detail-item">
                      <span className="profile-detail-label">Full Name</span>
                      <span className="profile-detail-value">{user.name || user.full_name || 'Not provided'}</span>
                    </div>
                    <div className="profile-detail-item">
                      <span className="profile-detail-label">Email Address</span>
                      <span className="profile-detail-value">{user.email}</span>
                    </div>
                    <div className="profile-detail-item">
                      <span className="profile-detail-label">Workspace Isolation</span>
                      <span className="profile-detail-value text-success">Enabled (User-Partitioned)</span>
                    </div>
                    <div className="profile-detail-item">
                      <span className="profile-detail-label">Session Status</span>
                      <span className="profile-detail-value">Active (Secure Cookie)</span>
                    </div>
                  </div>

                  <div className="profile-actions-row">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleSelectView('history')}
                    >
                      View My Inspections
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={handleLogout}
                    >
                      Log Out
                    </button>
                  </div>
                </div>
              ) : (
                <div className="guest-model-callout">
                  <div className="callout-header">
                    <span className="callout-icon" aria-hidden="true">ℹ️</span>
                    <div>
                      <h4 className="callout-title">Full Guest Access Active</h4>
                      <span className="callout-subtitle">Sign in or register to protect private inspection history</span>
                    </div>
                  </div>
                  <p className="callout-body">
                    OmniSight currently operates with full guest access. You can launch real-time inspections,
                    audit multimodal DOM and screenshot evidence, review defect findings, and test self-healing
                    locator repairs without requiring an account. Sign in to isolate your inspection history.
                  </p>
                  <div className="callout-action-row" style={{ marginTop: '1.25rem', display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={handleSignIn}
                      title="Login or register an account"
                    >
                      Login / Sign Up
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleSelectView('home')}
                      title="Return to Home overview"
                    >
                      Return to Home
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* VIEW 7: Dedicated Settings Page */}
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

      {/* Authentication Modal (Sign In / Register) */}
      <AuthModal
        isOpen={isAuthModalOpen}
        initialMode={authModalMode}
        onClose={() => setIsAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />

      <footer className="dashboard-footer">
        <p>OmniSight &mdash; Multimodal UI Self-Healing &amp; RPA Agent Orchestration</p>
      </footer>
    </div>
  );
}
