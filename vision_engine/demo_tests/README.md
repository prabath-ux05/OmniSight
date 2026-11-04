
# Vision Engine Live Validation

## Purpose

This directory contains a controlled local webpage used to validate the
OmniSight Vision Engine with the Gemini Vision-Language Model provider.

The demo includes three scenarios:

- Clean page: expected to produce no findings.
- Text overflow: expected to produce a `layout_overflow` finding.
- Broken image: expected to produce a `broken_image` finding.

**Note:** This is a controlled test fixture, not the team's actual demo website.

## Prerequisites

- Python 3.12
- Project virtual environment activated
- Gemini API key configured as `GEMINI_API_KEY` in the root `.env` file
- Playwright and Chromium installed

Install Playwright if necessary:

```powershell
python -m pip install playwright
python -m playwright install chromium
```

## Capture browser evidence

From the repository root:

```powershell
python -m vision_engine.demo_tests.capture_evidence
```

The command creates screenshots and HTML snapshots in `evidence/`.

## Run live Gemini validation

Run combined screenshot and DOM tests:

```powershell
python -m vision_engine.demo_tests.run_gemini_tests
```

Run DOM-only timeout diagnostics:

```powershell
python -m vision_engine.demo_tests.run_dom_timeout_check
```

The diagnostic uses a 60-second configured request timeout.

## Benchmark reports

The following JSON reports are generated:

- `evidence/live_validation_results.json`
- `evidence/dom_timeout_check_results.json`

They record detection results, findings, and response times.

## Validation notes

The Gemini provider was tested with the `gemini-3.5-flash-lite` model.

The controlled test cases demonstrated:

- Clean-page recognition.
- Screenshot-based overflow detection.
- DOM-based overflow detection after prompt improvement.
- Screenshot-based and DOM-based broken-image detection.

Live API response times can vary. Results represent individual test runs,
not statistically established performance benchmarks.

## Security

Never commit the root `.env` file or expose Gemini API keys in test reports.
