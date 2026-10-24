import React, { useState, useEffect, useCallback } from 'react';
import Header from './components/Header';
import InspectionForm from './components/InspectionForm';
import RunStatusCard from './components/RunStatusCard';
import FindingsSection from './components/FindingsSection';
import EvidenceSection from './components/EvidenceSection';
import Alert from './components/Alert';
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

  // Alerts & errors
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // 1. Fetch Backend Health
  const checkHealth = useCallback(async () => {
    setIsHealthLoading(true);
    try {
      const res = await fetch('/health');
      if (res.ok) {
        const data = await res.json();
        setHealth(data);
      } else {
        setHealth({ status: 'unreachable' });
      }
    } catch (err) {
      setHealth({ status: 'offline', error: err.message });
    } finally {
      setIsHealthLoading(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // 2. Fetch Findings for a specific Run ID
  const fetchFindings = useCallback(async (runId) => {
    if (!runId) return;
    setIsFindingsLoading(true);
    try {
      const res = await fetch(`/api/v1/runs/${encodeURIComponent(runId)}/findings`);
      if (res.ok) {
        const data = await res.json();
        setFindings(data);
        if (data && data.length > 0) {
          setSelectedFinding(data[0]);
        } else {
          setSelectedFinding(null);
        }
      } else {
        const errData = await res.json().catch(() => ({}));
        setErrorMessage(errData.detail || `Failed to fetch findings for run ${runId}`);
        setFindings(null);
        setSelectedFinding(null);
      }
    } catch (err) {
      setErrorMessage(`Network error fetching findings: ${err.message}`);
      setFindings(null);
      setSelectedFinding(null);
    } finally {
      setIsFindingsLoading(false);
    }
  }, []);

  // 3. Initiate a New Inspection Run
  const handleStartInspection = async (targetUrl) => {
    setErrorMessage('');
    setSuccessMessage('');
    setIsRunLoading(true);
    setFindings(null);
    setSelectedFinding(null);

    try {
      const res = await fetch('/api/v1/runs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: targetUrl }),
      });

      if (res.status === 201) {
        const runData = await res.json();
        setCurrentRun(runData);
        setSuccessMessage(`Run ${runData.run_id} initiated successfully!`);
        // Immediately fetch findings associated with this run
        fetchFindings(runData.run_id);
      } else {
        const errData = await res.json().catch(() => ({}));
        let errText = errData.detail || 'Failed to initiate inspection run.';
        if (Array.isArray(errData.detail)) {
          errText = errData.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
        }
        setErrorMessage(`Error (${res.status}): ${errText}`);
      }
    } catch (err) {
      setErrorMessage(
        `Unable to connect to OmniSight backend at http://127.0.0.1:8000. Please ensure the backend server is running. (${err.message})`
      );
    } finally {
      setIsRunLoading(false);
    }
  };

  // 4. Poll/Refresh Run Status
  const handleRefreshRun = async (runId) => {
    if (!runId) return;
    setErrorMessage('');
    setIsRunLoading(true);

    try {
      const res = await fetch(`/api/v1/runs/${encodeURIComponent(runId)}`);
      if (res.ok) {
        const runData = await res.json();
        setCurrentRun(runData);
        // Refresh findings as well
        fetchFindings(runId);
      } else {
        const errData = await res.json().catch(() => ({}));
        setErrorMessage(errData.detail || `Run ${runId} not found.`);
      }
    } catch (err) {
      setErrorMessage(`Error refreshing run status: ${err.message}`);
    } finally {
      setIsRunLoading(false);
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
        {/* 6. Error & Success alert areas */}
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
