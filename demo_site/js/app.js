/**
 * OmniSight Demo Portal — Interactive Application Logic
 */

(function () {
  'use strict';

  // Global toast function
  window.showToast = function (message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type === 'defect' ? 'toast-defect' : type === 'clean' ? 'toast-clean' : ''}`;
    
    const icon = type === 'defect' ? '⚠️' : type === 'clean' ? '✅' : 'ℹ️';
    toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
    
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(10px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  };

  document.addEventListener('DOMContentLoaded', function () {
    // 1. Primary Action: Trigger Self-Healing
    const btnTriggerSelfHeal = document.getElementById('btn-trigger-self-heal');
    if (btnTriggerSelfHeal) {
      btnTriggerSelfHeal.addEventListener('click', function () {
        window.showToast('Self-healing pipeline initiated for active workflow run WF-8492', 'info');
      });
    }

    // 2. Secondary Action: Export Telemetry
    const btnExportTelemetry = document.getElementById('btn-export-telemetry');
    if (btnExportTelemetry) {
      btnExportTelemetry.addEventListener('click', function () {
        window.showToast('Telemetry data exported successfully as JSON package', 'clean');
      });
    }

    // 3. Refresh Dashboard
    const btnRefresh = document.getElementById('btn-refresh-dashboard');
    if (btnRefresh) {
      btnRefresh.addEventListener('click', function () {
        btnRefresh.style.transform = 'rotate(360deg)';
        btnRefresh.style.transition = 'transform 0.5s ease';
        setTimeout(() => {
          btnRefresh.style.transform = 'none';
          btnRefresh.style.transition = 'none';
        }, 500);

        // Slightly adjust metric active jobs value to demonstrate live dynamic state
        const valElem = document.getElementById('metric-active-jobs-value');
        if (valElem) {
          const currentVal = parseInt(valElem.textContent.replace(/,/g, ''), 10) || 1482;
          const nextVal = currentVal + Math.floor(Math.random() * 5) - 2;
          valElem.textContent = nextVal.toLocaleString();
        }
        window.showToast('Dashboard metrics refreshed from live agent telemetry', 'clean');
      });
    }

    // 4. Table Search Filter
    const filterInput = document.getElementById('table-filter-input');
    const tableBody = document.getElementById('workflow-runs-tbody');
    if (filterInput && tableBody) {
      filterInput.addEventListener('input', function (e) {
        const query = e.target.value.toLowerCase().trim();
        const rows = tableBody.querySelectorAll('tr');
        let visibleCount = 0;

        rows.forEach(row => {
          const text = row.textContent.toLowerCase();
          const matches = text.includes(query);
          row.style.display = matches ? '' : 'none';
          if (matches) visibleCount++;
        });

        const countBadge = document.getElementById('table-run-count');
        if (countBadge) {
          countBadge.textContent = `${visibleCount} Runs Tracked`;
        }
      });
    }

    // 5. Table Action Buttons (Inspect)
    const inspectButtons = document.querySelectorAll('.btn-table-action');
    inspectButtons.forEach(btn => {
      btn.addEventListener('click', function (e) {
        const row = e.target.closest('tr');
        const wfId = row ? row.querySelector('code')?.textContent || 'Workflow' : 'Workflow';
        window.showToast(`Inspecting execution traces and locator diff for ${wfId}`, 'info');
      });
    });

    // 6. Navigation items click simulation
    const navLinks = document.querySelectorAll('.sidebar-nav .nav-link');
    navLinks.forEach(link => {
      link.addEventListener('click', function (e) {
        e.preventDefault();
        navLinks.forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        const label = link.querySelector('.nav-label')?.textContent || 'Section';
        window.showToast(`Switched view to ${label}`, 'info');
      });
    });

    // 7. Search input in navbar
    const navSearch = document.getElementById('nav-search-input');
    if (navSearch) {
      navSearch.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') {
          window.showToast(`Locator index queried: "${navSearch.value}"`, 'info');
        }
      });
    }

    // 8. User profile click
    const userProfile = document.getElementById('user-profile-menu');
    if (userProfile) {
      userProfile.addEventListener('click', function () {
        window.showToast('User: Test Engineer (RPA Suite Admin)', 'info');
      });
    }
  });
})();
