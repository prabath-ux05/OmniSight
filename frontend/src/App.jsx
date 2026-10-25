import React, { useState, useEffect, useCallback } from 'react';
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
} from './services/api';
import './App.css';

export default function App() {
  // Backend health status
  const [health, setHealth] = useState(null);
  const [isHealthLoading, setIsHealthLoading] = useState(false);

  // Active run state
  const [currentRun, setCurrentRun] = useState(null);
  const [isRunLoading, setIsRunLoading] = useState(false);

  // Findings state
  const [findings, setFindings] = useState(null);
  const [isFindingsLoading, setIsFindingsLoading] = useState(false);
  const [selectedFinding, setSelectedFinding] = useState(null);

  // Alerts & status notifications
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // 1. Fetch Backend Health
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

  // 2. Fetch Findings for a specific Run ID
  const fetchFindings = useCallback(async (runId) => {
    if (!runId) return;
    setIsFindingsLoading(true);
    const result = await fetchRunFindings(runId);

    if (result.ok) {
      setFindings(result.data);
      if (result.data && result.data.length > 0) {
        setSelectedFinding(result.data[0]);
      } else {
        setSelectedFinding(null);
      }
    } else {
      setErrorMessage(result.error);
      setFindings(null);
      setSelectedFinding(null);
    }
    setIsFindingsLoading(false);
  }, []);

  // 3. Initiate a New Inspection Run (POST /api/v1/runs)
  const handleStartInspection = async (targetUrl) => {
    // Reset previous feedback alerts and state
    setErrorMessage('');
    setSuccessMessage('');
    setIsRunLoading(true);
    setFindings(null);
    setSelectedFinding(null);

    // Send real HTTP POST request to backend via centralized API service
    const result = await createInspectionRun(targetUrl);

    if (result.ok) {
      const runData = result.data;
      setCurrentRun(runData);
      setSuccessMessage(
        `Run '${runData.run_id}' initiated successfully! Initial status: ${runData.status.toUpperCase()}.`
      );
      // Fetch associated findings for this run
      await fetchFindings(runData.run_id);
    } else {
      // Do not invent success; report real backend or connection error
      setCurrentRun(null);
      setErrorMessage(result.error);
    }

    setIsRunLoading(false);
  };

  // 4. Poll / Refresh Run Status (GET /api/v1/runs/{run_id})
  const handleRefreshRun = async (runId) => {
    if (!runId) return;
    setErrorMessage('');
    setIsRunLoading(true);

    const result = await fetchRun(runId);
    if (result.ok) {
      setCurrentRun(result.data);
      // Refresh findings as well
      await fetchFindings(runId);
    } else {
      setErrorMessage(result.error);
    }

    setIsRunLoading(false);
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
        {/* Loading and error/success message areas */}
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

        {/* 3. Run status section */}
        <RunStatusCard
          run={currentRun}
          onRefresh={handleRefreshRun}
          isRefreshing={isRunLoading}
        />

        {/* 4 & 5. Findings section and Screenshot / Evidence section in responsive grid */}
        <div className="dashboard-split-grid">
          <FindingsSection
            findings={findings}
            isLoading={isFindingsLoading}
            selectedFindingId={selectedFinding?.finding_id}
            onSelectFinding={(item) => setSelectedFinding(item)}
            runId={currentRun?.run_id}
          />

          <EvidenceSection
            finding={selectedFinding}
            runId={currentRun?.run_id}
          />
        </div>
      </main>

      <footer className="dashboard-footer">
        <p>OmniSight &mdash; Multimodal UI Self-Healing &amp; RPA Agent Orchestration</p>
      </footer>
    </div>
  );
}
