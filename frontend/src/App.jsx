import React, { useState, useEffect, useCallback, useRef } from 'react';
import Header from './components/Header';
import InspectionForm from './components/InspectionForm';
import RunStatusCard from './components/RunStatusCard';
import FindingsSection from './components/FindingsSection';
import EvidenceSection from './components/EvidenceSection';
import Alert from './components/Alert';
import {
  fetchHealth,
  createInspectionRun,
  fetchRun,
  fetchRunFindings,
  executeRunPipeline,
  repairRunFinding,
} from './services/api';
import './App.css';

const TERMINAL_STATUSES = ['completed', 'failed', 'cancelled'];

export default function App() {
  // Backend health status
  const [health, setHealth] = useState(null);
  const [isHealthLoading, setIsHealthLoading] = useState(false);

  // Active run state (Day 14 & 17)
  const [currentRun, setCurrentRun] = useState(null);
  const [isRunLoading, setIsRunLoading] = useState(false);
  const [isAutoPolling, setIsAutoPolling] = useState(false);
  const [isExecuting, setIsExecuting] = useState(false);

  // Findings state (Day 15)
  const [findings, setFindings] = useState(null);
  const [isFindingsLoading, setIsFindingsLoading] = useState(false);
  const [findingsError, setFindingsError] = useState('');
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [includeMockFindings, setIncludeMockFindings] = useState(false);

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
  // 2. Fetch Findings (Day 15)
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
  // 3. Initiate a New Inspection Run (Day 13 & 14)
  // ---------------------------------------------------------------------------
  const handleStartInspection = async (targetUrl) => {
    setErrorMessage('');
    setSuccessMessage('');
    setIsRunLoading(true);
    setFindings(null);
    setSelectedFinding(null);
    setFindingsError('');
    setRepairs({});
    setRepairError('');

    // 1. Submit real POST /api/v1/runs?auto_execute=true
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

      // Load initial findings (default to real findings)
      await loadFindings(runData.run_id, false);
    } else {
      setCurrentRun(null);
      setIsAutoPolling(false);
      setErrorMessage(result.error);
    }

    setIsRunLoading(false);
  };

  // ---------------------------------------------------------------------------
  // 4. Poll / Refresh Run Status (Day 14)
  // ---------------------------------------------------------------------------
  const handleRefreshRun = async (runId) => {
    if (!runId) return;
    setErrorMessage('');
    setIsRunLoading(true);

    const result = await fetchRun(runId);
    if (result.ok) {
      const updatedRun = result.data;
      setCurrentRun(updatedRun);

      // Stop auto-polling if terminal status reached
      if (TERMINAL_STATUSES.includes(updatedRun.status)) {
        setIsAutoPolling(false);
      }

      // Refresh findings as well
      await loadFindings(runId, includeMockFindings);
    } else {
      // If run not found or network error, stop polling
      setIsAutoPolling(false);
      setErrorMessage(result.error);
    }

    setIsRunLoading(false);
  };

  // ---------------------------------------------------------------------------
  // 5. Look up an existing or unknown run ID (Day 14 testing)
  // ---------------------------------------------------------------------------
  const handleLookupRun = async (runId) => {
    setErrorMessage('');
    setSuccessMessage('');
    setIsRunLoading(true);
    setFindings(null);
    setSelectedFinding(null);
    setFindingsError('');
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
    } else {
      // Report exact error (e.g. HTTP 404: Run 'xxx' not found.)
      setCurrentRun(null);
      setIsAutoPolling(false);
      setErrorMessage(result.error);
    }

    setIsRunLoading(false);
  };

  // ---------------------------------------------------------------------------
  // 6. Execute Run Pipeline On Demand (Day 17)
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
    } else {
      setErrorMessage(result.error);
    }

    setIsExecuting(false);
  };

  // ---------------------------------------------------------------------------
  // 7. Self-Healing Locator Repair Suggestion
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
  // 7. Polling Lifecycle Effect (Day 14)
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!currentRun?.run_id || !isAutoPolling) {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
      return;
    }

    // Stop polling if terminal status reached
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
          // Refresh findings upon run completion (real detector findings)
          await loadFindings(freshRun.run_id, false);

          if (freshRun.status === 'completed') {
            setSuccessMessage(`Run '${freshRun.run_id}' completed successfully!`);
          } else if (freshRun.status === 'failed') {
            setErrorMessage(`Run '${freshRun.run_id}' failed: ${freshRun.error || freshRun.message || 'Inspection pipeline failure'}`);
          }
        }
      } else {
        // Stop polling on error (e.g. unknown run 404 or backend shutdown)
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
  }, [currentRun?.run_id, currentRun?.status, isAutoPolling, loadFindings]);

  // ---------------------------------------------------------------------------
  // 8. Toggle Mock Findings (Day 15 testing both empty and populated states)
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
        {/* Error & Success alerts */}
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

        {/* 2. Section to initiate a website inspection */}
        <InspectionForm
          onSubmit={handleStartInspection}
          isLoading={isRunLoading}
        />

        {/* 3. Run status section with polling, lookup & pipeline execution (Day 14 & 17) */}
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

        {/* 4 & 5. Findings section and Screenshot / Evidence section in responsive grid (Day 15) */}
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
      </main>


      <footer className="dashboard-footer">
        <p>OmniSight &mdash; Multimodal UI Self-Healing &amp; RPA Agent Orchestration</p>
      </footer>
    </div>
  );
}
