
import json
import time
from pathlib import Path

from vision_engine.models import VisionInput
from vision_engine.detection.gemini_provider import GeminiVLMDetector

BASE_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE_DIR / "evidence"

TESTS = [
    ("clean", "screenshot_only", "clean", None),
    ("clean", "dom_only", None, "clean"),
    ("overflow", "screenshot_only", "overflow", None),
    ("overflow", "dom_only", None, "overflow"),
    ("broken_image", "screenshot_only", "broken_image", None),
    ("broken_image", "dom_only", None, "broken_image"),
]

EXPECTED_CATEGORIES = {
    "clean": None,
    "overflow": "layout_overflow",
    "broken_image": "broken_image",
}

detector = GeminiVLMDetector()
results = []

print("\nLIVE GEMINI EVIDENCE VALIDATION")
print("=" * 65)

for scenario, mode, screenshot_name, dom_name in TESTS:

    print("\n" + "=" * 65)
    print(f"SCENARIO: {scenario.upper()} | MODE: {mode.upper()}")
    print("=" * 65)

    screenshot_path = (
        str(EVIDENCE_DIR / f"{screenshot_name}.png")
        if screenshot_name else None
    )

    dom_path = (
        str(EVIDENCE_DIR / f"{dom_name}.html")
        if dom_name else None
    )

    input_data = VisionInput(
        run_id=f"day1-{scenario}-{mode}",
        url=(BASE_DIR / "demo_site.html").as_uri(),
        screenshot_path=screenshot_path,
        dom_snapshot_path=dom_path,
    )

    start_time = time.perf_counter()

    try:
        findings = detector.detect(input_data)

        elapsed = time.perf_counter() - start_time

        finding_data = [
            finding.model_dump(mode="json")
            for finding in findings
        ]

        found_categories = sorted({
            finding.category for finding in findings
        })

        expected = EXPECTED_CATEGORIES[scenario]

        if expected is None:
            matched = len(findings) == 0
            unexpected = found_categories
        else:
            matched = expected in found_categories
            unexpected = [
                category for category in found_categories
                if category != expected
            ]

        result = {
            "scenario": scenario,
            "evidence_mode": mode,
            "status": "success",
            "expected_category": expected,
            "found_categories": found_categories,
            "total_findings": len(findings),
            "matched_expectation": matched,
            "unexpected_categories": unexpected,
            "response_time_seconds": round(elapsed, 3),
            "findings": finding_data,
        }

        print(f"Findings: {len(findings)}")
        print(f"Categories: {found_categories}")
        print(f"Response time: {elapsed:.3f} seconds")
        print(f"Expected result matched: {matched}")

        for finding in findings:
            print(finding.model_dump_json(indent=2))

    except Exception as exc:
        elapsed = time.perf_counter() - start_time

        result = {
            "scenario": scenario,
            "evidence_mode": mode,
            "status": "error",
            "response_time_seconds": round(elapsed, 3),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

        print(f"TEST ERROR: {type(exc).__name__}: {exc}")
        print(f"Response time: {elapsed:.3f} seconds")

    results.append(result)


# Save complete results as JSON.
report_path = EVIDENCE_DIR / "live_validation_results.json"
report_path.parent.mkdir(parents=True, exist_ok=True)

report = {
    "model": "gemini-3.5-flash-lite",
    "test_type": "live Gemini screenshot-only and DOM-only validation",
    "total_tests": len(results),
    "successful_requests": sum(
        item["status"] == "success" for item in results
    ),
    "failed_requests": sum(
        item["status"] == "error" for item in results
    ),
    "matched_expectations": sum(
        item.get("matched_expectation", False) for item in results
    ),
    "results": results,
}

report_path.write_text(
    json.dumps(report, indent=2),
    encoding="utf-8",
)

print("\n" + "=" * 65)
print("FINAL SUMMARY")
print("=" * 65)

for item in results:
    if item["status"] == "error":
        status = "ERROR"
    else:
        status = (
            "MATCH"
            if item["matched_expectation"]
            else "MISMATCH"
        )

    print(
        f'{item["scenario"]:12} | '
        f'{item["evidence_mode"]:16} | '
        f'{status:8} | '
        f'{item["response_time_seconds"]:.3f}s'
    )

print("\nSuccessful requests:", report["successful_requests"])
print("Failed requests:", report["failed_requests"])
print("Matched expectations:", report["matched_expectations"])
print(f"\nJSON report saved at:\n{report_path}")
