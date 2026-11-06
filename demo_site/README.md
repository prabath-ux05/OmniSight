# OmniSight Controlled Test Target (Demo Site)

A dashboard-style web portal under `demo_site/` serving as a controlled System Under Test (SUT) for OmniSight's **Browser Automation Agent**, **Multimodal Vision Engine**, and **Self-Healing Pipeline**.

---

## 🎯 Purpose & Features

- **Controlled SUT**: Provides an isolated test environment with zero external dependencies.
- **Stable Locators**: All critical UI elements feature persistent `id`, `class`, and `data-testid` attributes.
- **Clean Baseline**: The default state renders cleanly without layout overflow, broken images, or missing elements.
- **Deterministic Defect Injection**: Includes reproducible defects that can be triggered via UI controls or URL query parameters.

---

## 🚀 Quick Start (Local Run Instructions)

You can run the demo site using any standard local HTTP server or open `index.html` directly:

### Option 1: Python Built-in HTTP Server (Recommended)
```bash
# From the repository root:
python -m http.server 8080 --directory demo_site
```
Then open in your browser:
```text
http://127.0.0.1:8080
```

### Option 2: Node http-server (if installed)
```bash
npx serve demo_site -l 8080
```

### Option 3: Direct File Opening
Double-click `demo_site/index.html` or open it directly in Google Chrome / Edge / Firefox.

---

## 🧪 Reproducible Defects & Control Modes

The site supports 3 primary deterministic UI defects:

| Defect Name | Target Element ID | Injected Behavior | Clean Baseline State |
| :--- | :--- | :--- | :--- |
| **1. Layout Overflow** | `#card-active-jobs` | Injects an unconstrained 500-character string and breaks card width constraints (`min-width: 980px`), forcing horizontal grid blowout. | Neat truncation and responsive grid layout. |
| **2. Missing Visible Element** | `#btn-trigger-self-heal` | Completely removes the primary CTA button from the DOM layout (`display: none`, opacity 0, unclickable). | Vibrant, high-contrast, fully clickable action button. |
| **3. Broken Image Asset** | `#service-topology-image` | Changes `src` to an unreachable 404 path, exposing error fallback box. | Renders vector topology illustration (`system-topology.svg`). |

### Triggering Defects via URL Query Parameters

You can load specific defect states directly without clicking UI controls:

- **Clean Baseline**: `http://127.0.0.1:8080/?state=clean`
- **Layout Overflow only**: `http://127.0.0.1:8080/?defect=overflow`
- **Missing Element only**: `http://127.0.0.1:8080/?defect=missing`
- **Broken Image only**: `http://127.0.0.1:8080/?defect=image`
- **All 3 Defects Active**: `http://127.0.0.1:8080/?defects=all`
- **Combinations**: `http://127.0.0.1:8080/?defects=overflow,missing`

### Triggering Defects Programmatically in JavaScript / Playwright

The page exposes `window.OmniSightDefects`:

```javascript
// Check state
window.OmniSightDefects.getState(); // { overflow: false, missingElement: false, brokenImage: false }

// Inject individual defects
window.OmniSightDefects.setOverflow(true);
window.OmniSightDefects.setMissingElement(true);
window.OmniSightDefects.setBrokenImage(true);

// Reset to clean
window.OmniSightDefects.resetAll();
```

---

## 📌 Stable Selector Reference for Agent Testing

| Component | Selector | Notes |
| :--- | :--- | :--- |
| **Defect Dock** | `#defect-control-dock` | Test harness control drawer |
| **Overflow Toggle** | `#toggle-defect-overflow` | Checkbox input |
| **Missing Toggle** | `#toggle-defect-missing-element` | Checkbox input |
| **Broken Image Toggle**| `#toggle-defect-broken-image` | Checkbox input |
| **Reset Button** | `#btn-reset-defects` | Button |
| **Primary CTA Button** | `#btn-trigger-self-heal` | Primary action button (Defect 2 target) |
| **Secondary Button** | `#btn-export-telemetry` | Secondary button |
| **Active Jobs Card** | `#card-active-jobs` | KPI Card (Defect 1 target) |
| **Active Jobs Subtext**| `#metric-active-jobs-subtext` | Overflow string container |
| **Topology Card** | `#service-topology-card` | Visual section card |
| **Topology Image** | `#service-topology-image` | `<img>` tag (Defect 3 target) |
| **Data Table** | `#workflow-runs-table` | Telemetry runs table |
| **Table Filter** | `#table-filter-input` | Search input |
