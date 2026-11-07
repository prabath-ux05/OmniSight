
import json
import time
from pathlib import Path

from vision_engine.models import VisionInput
from vision_engine.detection.gemini_provider import GeminiVLMDetector

BASE_DIR = Path(__file__).resolve().parent
EVIDENCE_DIR = BASE_DIR / "evidence"

# Use 60 seconds for this diagnostic only.
detector = GeminiVLMDetector(timeout_seconds=60.0)

results = []

for scenario in ["clean", "overflow"]:
    print("\n" + "=" * 60)
    print(f"DOM-ONLY TIMEOUT CHECK: {scenario.upper()}")
    print("=" * 60)

    dom_path = EVIDENCE_DIR / f"{scenario}.html"

    input_data = VisionInput(
        run_id=f"day1-{scenario}-dom-timeout-check",
        url=(BASE_DIR / "demo_site.html").as_uri(),
        dom_snapshot_path=str(dom_path),
    )

    start = time.perf_counter()

    try:
        findings = detector.detect(input_data)
        elapsed = time.perf_counter() - start

        result = {
            "scenario": scenario,
            "status": "success",
            "response_time_seconds": round(elapsed, 3),
            "findings": [
                finding.model_dump(mode="json")
                for finding in findings
            ],
        }

        print(f"Findings: {len(findings)}")
        print(f"Response time: {elapsed:.3f} seconds")

        for finding in findings:
            print(finding.model_dump_json(indent=2))

    except Exception as exc:
        elapsed = time.perf_counter() - start

        result = {
            "scenario": scenario,
            "status": "error",
            "response_time_seconds": round(elapsed, 3),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }

        print(f"Error: {type(exc).__name__}: {exc}")
        print(f"Response time: {elapsed:.3f} seconds")

    results.append(result)

report_path = EVIDENCE_DIR / "dom_timeout_check_results.json"

report_path.write_text(
    json.dumps(results, indent=2),
    encoding="utf-8",
)

print("\n" + "=" * 60)
print("DOM TIMEOUT CHECK COMPLETED")
print("=" * 60)
print(f"Results saved to: {report_path}")
