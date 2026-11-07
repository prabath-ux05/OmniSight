"""Compare full-image, single-crop, and multi-crop Gemini analysis."""

import json
import time
from io import BytesIO
from pathlib import Path

from PIL import Image

from vision_engine.models import VisionInput, BoundingBox
from vision_engine.image_processing import crop_screenshot_with_origin
from vision_engine.detection.gemini_provider import GeminiVLMDetector


BASE_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE_DIR / "evidence"
REPORT_PATH = EVIDENCE_DIR / "crop_comparison_results.json"

SCENARIOS = {
    "overflow": "layout_overflow",
    "broken_image": "broken_image",
}

# Approximate regions for the two defect screenshots.
# Coordinates are based on the 1365 x 900 captured screenshots.
DEFECT_CROP = BoundingBox(
    x=0, y=140, width=900, height=450
)

# A separate page-heading/context region for multi-crop testing.
CONTEXT_CROP = BoundingBox(
    x=0, y=0, width=1365, height=120
)

MODES = [
    ("full_image", None),
    ("single_crop", "single"),
    ("multi_crop", "multiple"),
]


def get_crop_payload_size(screenshot_path, boxes):
    """Estimate the combined PNG payload size of the selected crops."""
    total = 0

    for box in boxes:
        cropped_image, _ = crop_screenshot_with_origin(
            str(screenshot_path), box
        )

        with BytesIO() as buffer:
            cropped_image.save(buffer, format="PNG")
            total += len(buffer.getvalue())

    return total


def run_benchmark():
    detector = GeminiVLMDetector()
    results = []

    print("\nOMNISIGHT CROP MODE BENCHMARK")
    print("=" * 65)
    print("This test makes live Gemini API requests.")
    print("Existing validation reports will not be modified.")

    for scenario, expected_category in SCENARIOS.items():
        screenshot_path = EVIDENCE_DIR / f"{scenario}.png"

        if not screenshot_path.exists():
            print(f"Missing screenshot: {screenshot_path}")
            continue

        original_payload_size = screenshot_path.stat().st_size

        for mode, crop_type in MODES:
            print("\n" + "-" * 65)
            print(f"Scenario: {scenario} | Mode: {mode}")
            print("-" * 65)

            input_arguments = {
                "run_id": f"crop-benchmark-{scenario}-{mode}",
                "url": (BASE_DIR / "demo_site.html").as_uri(),
                "screenshot_path": str(screenshot_path),
            }

            if crop_type == "single":
                input_arguments["crop_box"] = DEFECT_CROP

                payload_size = get_crop_payload_size(
                    screenshot_path, [DEFECT_CROP]
                )
                planned_requests = 1

            elif crop_type == "multiple":
                input_arguments["crop_boxes"] = [
                    DEFECT_CROP,
                    CONTEXT_CROP,
                ]

                payload_size = get_crop_payload_size(
                    screenshot_path,
                    [DEFECT_CROP, CONTEXT_CROP],
                )
                planned_requests = 2

            else:
                payload_size = original_payload_size
                planned_requests = 1

            start_time = time.perf_counter()

            try:
                vision_input = VisionInput(**input_arguments)
                findings = detector.detect(vision_input)

                elapsed = time.perf_counter() - start_time

                finding_data = [
                    finding.model_dump(mode="json")
                    for finding in findings
                ]

                categories = sorted({
                    finding.category for finding in findings
                })

                matched = expected_category in categories

                result = {
                    "scenario": scenario,
                    "mode": mode,
                    "status": "success",
                    "expected_category": expected_category,
                    "found_categories": categories,
                    "expected_category_detected": matched,
                    "total_findings": len(findings),
                    "duplicate_category_findings": max(
                        0,
                        len(findings) - len(categories),
                    ),
                    "response_time_seconds": round(elapsed, 3),
                    "planned_image_requests": planned_requests,
                    "original_png_bytes": original_payload_size,
                    "analyzed_png_payload_bytes": payload_size,
                    "findings": finding_data,
                }

                print(f"Expected category: {expected_category}")
                print(f"Found categories: {categories}")
                print(f"Findings: {len(findings)}")
                print(f"Expected defect detected: {matched}")
                print(f"Elapsed time: {elapsed:.3f} seconds")
                print(f"Planned image requests: {planned_requests}")
                print(f"Original PNG bytes: {original_payload_size}")
                print(f"Analyzed PNG payload bytes: {payload_size}")

            except Exception as exc:
                elapsed = time.perf_counter() - start_time

                result = {
                    "scenario": scenario,
                    "mode": mode,
                    "status": "error",
                    "expected_category": expected_category,
                    "response_time_seconds": round(elapsed, 3),
                    "planned_image_requests": planned_requests,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }

                print(f"ERROR: {type(exc).__name__}: {exc}")

            results.append(result)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "model": "gemini-3.5-flash-lite",
        "test_type": (
            "Full-image vs single-crop vs multi-crop comparison"
        ),
        "crop_coordinates": {
            "defect_region": DEFECT_CROP.model_dump(mode="json"),
            "context_region": CONTEXT_CROP.model_dump(mode="json"),
        },
        "total_runs": len(results),
        "successful_runs": sum(
            item["status"] == "success" for item in results
        ),
        "failed_runs": sum(
            item["status"] == "error" for item in results
        ),
        "expected_defects_detected": sum(
            item.get("expected_category_detected", False)
            for item in results
        ),
        "results": results,
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 65)
    print("BENCHMARK SUMMARY")
    print("=" * 65)

    for item in results:
        if item["status"] == "error":
            status = "ERROR"
        else:
            status = (
                "MATCH"
                if item["expected_category_detected"]
                else "MISMATCH"
            )

        print(
            f'{item["scenario"]:12} | '
            f'{item["mode"]:12} | '
            f'{status:8} | '
            f'{item["response_time_seconds"]:.3f}s'
        )

    print("\nSuccessful runs:", report["successful_runs"])
    print("Failed runs:", report["failed_runs"])
    print(
        "Expected defects detected:",
        report["expected_defects_detected"],
    )
    print(f"\nReport saved to:\n{REPORT_PATH}")


if __name__ == "__main__":
    run_benchmark()
