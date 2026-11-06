Browser Agent Setup Guide
Overview
The Browser Agent is responsible for:

Browser navigation
Screenshot capture
DOM snapshot collection
Metadata collection
Console error collection
Timeout and failure handling
Installation
Create Virtual Environment
python -m venv .venv
Windows:

.venv\Scripts\Activate.ps1
Linux/macOS:

source .venv/bin/activate
Install Dependencies
pip install -r requirements.txt
Install Playwright
python -m playwright install chromium
Running Tests
pytest tests -v
Browser Agent Evidence
Generated artifacts:

artifacts/
└── <run_id>/
    ├── before.png
    └── dom.html
Evidence Fields
run_id
url
page_title
captured_at
viewport
screenshot_path
dom_snapshot_path
console_errors
page_errors
status
error
Example Usage
from navigation.navigator import BrowserNavigator

navigator = BrowserNavigator()

result = navigator.navigate(
    "https://example.com",
    "sample_run"
)

print(result)
Troubleshooting
Browser Not Found
python -m playwright install chromium
Dependency Issues
pip install -r requirements.txt
Test Execution
pytest tests -v