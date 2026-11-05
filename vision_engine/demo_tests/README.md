# Vision Engine Live Validation

## Purpose

This directory contains a controlled local webpage used to validate the
OmniSight Vision Engine with the Gemini Vision-Language Model provider.

The demo includes three scenarios:

- Clean page: expected to produce no findings.
- Text overflow: expected to produce a layout_overflow finding.
- Broken image: expected to produce a broken_image finding.

**Note:** This is a controlled test fixture, not the team's actual demo website.

## Prerequisites

- Python 3.12
- Project virtual environment activated
- Gemini API key configured as GEMINI_API_KEY in the root .env file
- Playwright and Chromium installed

Install Playwright if necessary:

    python -m pip install playwright
    python -m playwright install chromium

## Capture browser evidence

From the repository root:

    python -m vision_engine.demo_tests.capture_evidence

The command creates screenshots and HTML snapshots in evidence/.

## Run live Gemini validation

Run screenshot-only and DOM-only tests:

    python -m vision_engine.demo_tests.run_gemini_tests

Run DOM-only timeout diagnostics:

    python -m vision_engine.demo_tests.run_dom_timeout_check

The diagnostic uses a 60-second configured request timeout.

## Benchmark reports

The following JSON reports are generated:

- evidence/live_validation_results.json
- evidence/dom_timeout_check_results.json

They record detection results, findings, and response times.

## Screenshot cropping benchmark

Screenshot cropping was evaluated locally using bounding boxes returned
by Gemini during screenshot-only validation. The crop operation used
the default 20-pixel padding.

| Scenario | Original PNG | Cropped PNG | Payload reduction |
|---|---:|---:|---:|
| Overflow | 17,157 bytes | 1,406 bytes | 91.81% |
| Broken image | 17,792 bytes | 1,768 bytes | 90.06% |

Both original screenshots were 1365 x 900 pixels.

These measurements demonstrate reduced PNG payload sizes for the two
tested examples. They do not establish equivalent reductions in API cost,
token usage, or response time. The benchmark used model-reported bounding
boxes and is not a statistical performance evaluation.

## Verification

The Vision Engine includes after-repair verification support with
the following outcomes:

- resolved: no matching finding remains.
- partially_resolved: all matching findings have lower severity.
- unresolved: at least one matching finding remains at the original
  severity or a higher severity.
- unverifiable: the after-repair evidence cannot be validated.

Regression tests cover mixed-severity findings to ensure a repair is
not marked partially resolved when a finding remains at the original
severity.

## Validation notes

The Gemini provider was tested with the gemini-3.5-flash-lite model.

The latest six-test live validation run reported:

- 6 successful requests and 0 failed requests.
- All 3 screenshot-only scenarios matched expectations.
- All 3 DOM-only scenarios matched expectations.
- Clean-page recognition, overflow detection, and broken-image detection
  succeeded in both evidence modes.

The latest run's response times ranged from 4.913 to 103.730 seconds.
Live API response times can vary; these results represent individual
requests, not statistically established performance benchmarks.

The Vision Engine test suite passed 101 tests after the verification
improvement.

The controlled local fixture does not replace validation against the
team's actual demo website. That requires the team's demo URL and
suitable access.

## Security

Never commit the root .env file or expose Gemini API keys in test reports.
