import React from 'react';

/**
 * AboutPage renders the polished, comprehensive About view for OmniSight.
 *
 * Source of truth:
 * - Architecture: Python 3.12 + FastAPI + Playwright + PostgreSQL (port 5433) + React 18 / Vite.
 * - Vision Engine: Multimodal VLM (Google Gemini / OpenAI) + Deterministic DOM Parser fallback.
 * - Self-Healing: Heuristic locator synthesis, minimal memory diffs, human approval gate, GitHub PR integration.
 */
export default function AboutPage({
  onSelectView = () => {},
  onStartTour = () => {},
}) {
  return (
    <div className="about-page-container">
      {/* 1. Hero Banner */}
      <section className="about-hero-banner">
        <div className="about-hero-badge-row">
          <span className="about-hero-badge">Architecture &amp; Documentation</span>
          <span className="about-version-badge">Version 0.1.0</span>
          <span className="about-open-badge">Developer Preview</span>
        </div>
        <h2 className="about-hero-title">OmniSight: Multimodal UI Self-Healing &amp; RPA Agent</h2>
        <p className="about-hero-desc">
          OmniSight is an autonomous visual quality assurance and self-healing automation platform.
          It combines headless browser perception, multimodal vision-language intelligence, and heuristic
          DOM analysis to eliminate test flakiness, catch visual regressions, and propose resilient locator repairs with human-in-the-loop governance.
        </p>

        <div className="about-hero-actions">
          <button
            type="button"
            className="btn btn-primary btn-md"
            onClick={() => onSelectView('inspection')}
          >
            🔍 Open Live Studio
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-md"
            onClick={onStartTour}
          >
            🎓 Take Interactive Tour
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-md"
            onClick={() => onSelectView('history')}
          >
            📋 Browse Run History
          </button>
        </div>
      </section>

      {/* 2. The Core Problem OmniSight Solves */}
      <section className="about-section">
        <div className="about-section-header">
          <span className="section-label">Problem Statement</span>
          <h3 className="section-title">The Challenge of Modern Web Automation &amp; UI Testing</h3>
          <p className="section-desc">
            Traditional web test suites (Selenium, Cypress, Playwright) and RPA bots suffer from chronic maintenance overhead and blind spots:
          </p>
        </div>

        <div className="about-cards-grid">
          <div className="about-feature-card">
            <span className="feature-card-icon">💥</span>
            <h4 className="feature-card-title">Brittle Selectors &amp; Test Rot</h4>
            <p className="feature-card-desc">
              Minor UI refactoring, dynamic class hashing (Tailwind, CSS Modules), or markup restructuring routinely breaks CSS and XPath locators, causing false-positive test failures.
            </p>
          </div>

          <div className="about-feature-card">
            <span className="feature-card-icon">🙈</span>
            <h4 className="feature-card-title">Visual Blindness of DOM Assertions</h4>
            <p className="feature-card-desc">
              Standard assertions pass as long as an element is present in the DOM tree, completely missing visual text cut-offs, overlapping buttons, 404 broken images, or responsive viewport blowouts.
            </p>
          </div>

          <div className="about-feature-card">
            <span className="feature-card-icon">⏳</span>
            <h4 className="feature-card-title">Manual Remediation Overhead</h4>
            <p className="feature-card-desc">
              Engineers waste hours hunting through build logs, reproducing flaky runs locally, finding updated selectors, and manually creating pull requests to fix tests.
            </p>
          </div>

          <div className="about-feature-card">
            <span className="feature-card-icon">⚠️</span>
            <h4 className="feature-card-title">Ungoverned Autonomous Code Edits</h4>
            <p className="feature-card-desc">
              Unsupervised bots that directly mutate repository source code without review risk introducing unintended side-effects, syntax breakages, and security vulnerabilities.
            </p>
          </div>
        </div>
      </section>

      {/* 3. How OmniSight Works: Multimodal Perception & Self-Healing */}
      <section className="about-section">
        <div className="about-section-header">
          <span className="section-label">Core Mechanics</span>
          <h3 className="section-title">How Multimodal UI Inspection &amp; Self-Healing Work</h3>
          <p className="section-desc">
            OmniSight unites visual perception (rendered viewport pixels) with document structure (DOM snapshot trees) across four integrated layers:
          </p>
        </div>

        <div className="about-workflow-steps">
          <div className="workflow-step-card">
            <div className="workflow-step-num">1</div>
            <div className="workflow-step-content">
              <h4 className="workflow-step-title">Autonomous Perception (Browser Agent)</h4>
              <p className="workflow-step-desc">
                Playwright launches a headless Chromium session to navigate the target web URL. It waits for network idle stabilization, intercepts console/page errors, and writes two synchronized artifacts to disk: a high-resolution viewport screenshot (<code>before.png</code>) and the serialized DOM tree (<code>dom.html</code>).
              </p>
            </div>
          </div>

          <div className="workflow-step-card">
            <div className="workflow-step-num">2</div>
            <div className="workflow-step-content">
              <h4 className="workflow-step-title">Multimodal Defect Detection (Vision Engine)</h4>
              <p className="workflow-step-desc">
                The Vision Engine supports multimodal Vision-Language Models (such as Google Gemini or OpenAI when API keys are configured) to analyze visual anomalies alongside DOM context, with an automated fallback to deterministic DOM structure parsing when external models are unconfigured or unreachable. Defects are classified into <code>missing_visible_element</code>, <code>layout_shift_or_overflow</code>, and <code>broken_image_or_asset</code>.
              </p>
            </div>
          </div>

          <div className="workflow-step-card">
            <div className="workflow-step-num">3</div>
            <div className="workflow-step-content">
              <h4 className="workflow-step-title">Resilient Heuristic Repair (Self-Healing Engine)</h4>
              <p className="workflow-step-desc">
                When an element locator fails, the Self-Healing Engine analyzes the DOM tree and synthesizes replacement locators ranked by structural stability: Data Attributes (<code>data-testid</code>) &gt; Stable IDs &gt; Accessible Roles &amp; Names &gt; Unique Text &gt; Semantic CSS. Each candidate is tested for strict DOM uniqueness (must match exactly 1 intended element).
              </p>
            </div>
          </div>

          <div className="workflow-step-card">
            <div className="workflow-step-num">4</div>
            <div className="workflow-step-content">
              <h4 className="workflow-step-title">Safe Patch Generation &amp; Human Approval (Governance)</h4>
              <p className="workflow-step-desc">
                The system generates a safe unified diff patch in memory against your test suite (e.g. <code>tests/e2e/test_checkout.py</code>). A human reviewer must explicitly authorize the change via a mandatory approval checkbox gate in the frontend before pull request dispatch is requested.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Architecture & Technical Pipeline */}
      <section className="about-section">
        <div className="about-section-header">
          <span className="section-label">System Architecture</span>
          <h3 className="section-title">End-to-End Orchestration Architecture</h3>
          <p className="section-desc">
            A modular architecture connecting the web dashboard, FastAPI REST API, background execution tasks, headless browser, and relational audit store:
          </p>
        </div>

        <div className="about-arch-grid">
          <div className="arch-tier-card">
            <div className="arch-tier-header">
              <span className="arch-tier-icon">🖥️</span>
              <h4 className="arch-tier-title">Frontend Dashboard</h4>
              <span className="badge badge-neutral">Client Tier</span>
            </div>
            <ul className="arch-tier-list">
              <li><strong>Framework:</strong> React 18 + Vite 5 with pure CSS design tokens.</li>
              <li><strong>Themes:</strong> Dark Mode, Light Mode, and Automatic System Matching.</li>
              <li><strong>Workspaces:</strong> Home, Live Inspection Studio, Run History, Repair Workspace.</li>
              <li><strong>Accessibility:</strong> Keyboard shortcuts (Esc, Arrows, Enter) &amp; guided tour.</li>
              <li><strong>Guest Mode:</strong> Full functionality enabled without mandatory auth barriers.</li>
            </ul>
          </div>

          <div className="arch-tier-card">
            <div className="arch-tier-header">
              <span className="arch-tier-icon">⚙️</span>
              <h4 className="arch-tier-title">FastAPI Orchestrator</h4>
              <span className="badge badge-neutral">Service Tier</span>
            </div>
            <ul className="arch-tier-list">
              <li><strong>Runtime:</strong> Python 3.12 with Uvicorn and Pydantic v2 schemas.</li>
              <li><strong>Concurrency:</strong> FastAPI BackgroundTasks for non-blocking browser execution.</li>
              <li><strong>Windows Loop:</strong> ProactorEventLoop policy for stable Playwright subprocesses.</li>
              <li><strong>Artifact Security:</strong> Path traversal sanitization preventing arbitrary file reads.</li>
              <li><strong>REST API:</strong> <code>/runs</code>, <code>/findings</code>, <code>/artifacts</code>, <code>/repair</code>, <code>/proposals</code>.</li>
            </ul>
          </div>

          <div className="arch-tier-card">
            <div className="arch-tier-header">
              <span className="arch-tier-icon">🗄️</span>
              <h4 className="arch-tier-title">PostgreSQL Audit Database</h4>
              <span className="badge badge-neutral">Data Tier</span>
            </div>
            <ul className="arch-tier-list">
              <li><strong>Engine:</strong> PostgreSQL 16 (default host port <code>5433</code> in docker-compose.yml).</li>
              <li><strong>Container:</strong> Managed via Docker Compose (<code>omnisight-postgres</code>).</li>
              <li><strong>Migrations:</strong> Versioned Alembic schema migrations (<code>001_initial_tables</code>).</li>
              <li><strong>Records:</strong> Persistent inspection runs, findings, proposals, and decisions.</li>
              <li><strong>Data Integrity:</strong> Zero invented data; read-only historical inspection.</li>
            </ul>
          </div>
        </div>
      </section>

      {/* 5. Technology Stack (Exact Source of Truth) */}
      <section className="about-section">
        <div className="about-section-header">
          <span className="section-label">Technology Stack</span>
          <h3 className="section-title">Verified Technologies &amp; Dependencies</h3>
          <p className="section-desc">
            OmniSight is constructed strictly using verified production dependencies within this repository:
          </p>
        </div>

        <div className="tech-stack-container">
          <div className="tech-stack-group">
            <h5 className="tech-group-title">Backend &amp; API</h5>
            <div className="tech-badges-row">
              <span className="tech-pill">Python 3.12</span>
              <span className="tech-pill">FastAPI 0.115+</span>
              <span className="tech-pill">Pydantic v2</span>
              <span className="tech-pill">Uvicorn</span>
              <span className="tech-pill">SQLAlchemy 2.0</span>
              <span className="tech-pill">Alembic</span>
              <span className="tech-pill">psycopg2-binary</span>
            </div>
          </div>

          <div className="tech-stack-group">
            <h5 className="tech-group-title">Browser Agent &amp; Vision</h5>
            <div className="tech-badges-row">
              <span className="tech-pill">Playwright (Chromium Sync)</span>
              <span className="tech-pill">Google Gemini API (VLM)</span>
              <span className="tech-pill">OpenAI GPT-4o (VLM)</span>
              <span className="tech-pill">HTMLParser (DOM Heuristics)</span>
              <span className="tech-pill">PyGithub / GitHub REST</span>
            </div>
          </div>

          <div className="tech-stack-group">
            <h5 className="tech-group-title">Frontend Dashboard</h5>
            <div className="tech-badges-row">
              <span className="tech-pill">React 18.3</span>
              <span className="tech-pill">Vite 5.4</span>
              <span className="tech-pill">Native CSS Design Tokens</span>
              <span className="tech-pill">Node.js Test Runner (TAP 13)</span>
              <span className="tech-pill">LocalStorage Preferences</span>
            </div>
          </div>

          <div className="tech-stack-group">
            <h5 className="tech-group-title">Infrastructure &amp; DevOps</h5>
            <div className="tech-badges-row">
              <span className="tech-pill">Docker Compose</span>
              <span className="tech-pill">PostgreSQL 16</span>
              <span className="tech-pill">Git / GitHub Actions</span>
            </div>
          </div>
        </div>
      </section>

      {/* 6. Human-in-the-Loop Governance Guarantee */}
      <section className="about-section">
        <div className="governance-highlight-card">
          <div className="gov-icon-badge">🛡️</div>
          <div className="gov-content">
            <h3 className="gov-title">Human-in-the-Loop Governance Guarantee</h3>
            <p className="gov-desc">
              OmniSight adheres to four immutable safety principles to guarantee reliability and developer control:
            </p>
            <div className="gov-principles-grid">
              <div className="gov-principle-item">
                <strong>1. In-Memory Diff Generation:</strong>
                <span>Patches are synthesized in memory for preview and never mutate local files directly without explicit authorization.</span>
              </div>
              <div className="gov-principle-item">
                <strong>2. Mandatory Human Approval Gate:</strong>
                <span>Pull request submission enforces a mandatory confirmation gate: the user must explicitly authorize the repair in the frontend UI before PR dispatch is initiated.</span>
              </div>
              <div className="gov-principle-item">
                <strong>3. Simulation Mode by Default:</strong>
                <span>PR workflows operate in dry-run simulation mode unless live GitHub credentials and repository configurations are confirmed.</span>
              </div>
              <div className="gov-principle-item">
                <strong>4. Empirical Verification Workflow:</strong>
                <span>Candidate locators are validated against the captured DOM snapshot for strict uniqueness (1 match), with optional live-page verification when the target endpoint is actively reachable.</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 7. Quick Actions Footer */}
      <section className="about-footer-card card">
        <div className="about-footer-content">
          <h4 className="about-footer-title">Ready to Experience OmniSight?</h4>
          <p className="about-footer-text">
            Start an automated inspection run or explore the interactive guided walkthrough.
          </p>
        </div>
        <div className="about-footer-actions">
          <button
            type="button"
            className="btn btn-primary btn-md"
            onClick={() => onSelectView('home')}
          >
            🏠 Return to Home
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-md"
            onClick={onStartTour}
          >
            🎓 Start Guided Tour
          </button>
        </div>
      </section>
    </div>
  );
}
