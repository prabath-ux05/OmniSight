# OmniSight Vision Engine

The Vision Engine is the OmniSight component responsible for analyzing
website screenshot and DOM evidence and returning structured UI defect
findings.

The implementation includes deterministic mock detection, DOM-based
heuristics, a Gemini Vision-Language Model provider, evidence validation,
screenshot cropping, evaluation utilities, and after-repair verification.

## Responsibilities

- Represent inspection inputs and structured findings.
- Validate screenshot and DOM evidence.
- Detect selected UI defects using DOM heuristics and VLM analysis.
- Support deterministic mock detection for repeatable tests.
- Localize visual findings with bounding boxes when available.
- Support full-screenshot and cropped-screenshot analysis.
- Parse and validate model responses.
- Evaluate findings and verify after-repair results.
- Keep provider credentials out of source control.

## Main components

### 1. Input and finding models

File: `models.py`

The Vision Engine uses Pydantic models to represent inspection inputs,
bounding boxes, evidence references, and defect findings.

`VisionInput` supports:

- Inspection run ID and page URL.
- Optional screenshot evidence.
- Optional DOM snapshot evidence.
- An optional single crop box or multiple crop boxes.

Crop configuration requires screenshot evidence. A single crop box and
multiple crop boxes cannot be supplied together.

`BoundingBox` represents an image region using its position and dimensions.

`VisionFinding` represents a potential UI defect with structured
information such as category, severity, confidence, description,
optional selector, evidence references, and detection source.

Supported finding categories include:

- `layout_overflow`
- `missing_visible_element`
- `broken_image`

The shared team contract remains authoritative for integration.

### 2. Evidence validation

File: `evidence_validator.py`

The evidence validator checks supplied evidence paths, including whether
they exist, refer to files, and can be opened for reading.

File-level validation does not by itself prove that image contents or
HTML are semantically correct.

### 3. Detection providers

Directory: `detection/`

The Vision Engine includes multiple detection approaches.

- `mock_detector.py`: deterministic sample findings for repeatable tests.
- `dom_detector.py`: static HTML/DOM heuristics for selected issues.
- `gemini_provider.py`: Gemini-backed screenshot and DOM analysis.
- `vlm_interface.py`: provider interface for vision-language detection.

The mock detector does not inspect image pixels or perform AI inference.
DOM heuristics inspect HTML evidence and are limited to the rules they
implement. Gemini results are model-generated and must be validated.

### 4. Prompting and response parsing

Directory: `prompting/` and the detection response parser.

The VLM prompt defines the defect-analysis instructions and expected
structured response. The parser converts model output into validated
finding objects and handles malformed or unusable responses.

### 5. Screenshot processing

File: `image_processing.py`

Screenshot processing supports cropping an image using a bounding box
and configurable padding. The crop operation returns both the cropped
image and its original screenshot origin.

The Gemini provider supports:

- Full-image analysis.
- Single-crop analysis.
- Multiple-crop analysis.

For cropped analysis, returned bounding-box coordinates are translated
back to the original screenshot coordinate system.

Multiple crops can require multiple model requests. Their performance
and output quality should be evaluated against full-image analysis.

### 6. Evaluation

File: `evaluation.py`

The evaluation utilities compare detected findings with expected findings
and calculate:

- True positives.
- False positives.
- False negatives.
- Precision.
- Recall.
- F1 score.

Matching uses the finding category and, when supplied, the expected
selector. Evaluation results depend on the quality of the expected
findings used as the reference.

### 7. After-repair verification

File: `verification.py`

The verification functionality compares findings before and after a
repair and reports one of these outcomes:

- `resolved`
- `partially_resolved`
- `unresolved`
- `unverifiable`

Regression tests cover mixed-severity findings and verification outcomes.

## Demo and evidence validation

Directory: `demo_tests/`

The controlled local demo includes clean-page, text-overflow, and
broken-image scenarios.

Capture evidence:

    python -m vision_engine.demo_tests.capture_evidence

Run live Gemini validation:

    python -m vision_engine.demo_tests.run_gemini_tests

Run DOM timeout diagnostics:

    python -m vision_engine.demo_tests.run_dom_timeout_check

Run the full-image versus crop-mode benchmark:

    python -m vision_engine.demo_tests.benchmark_crop_modes

See `demo_tests/README.md` for prerequisites, benchmark measurements,
report locations, and limitations.

## Testing

Run all project tests from the repository root:

    python -m pytest -v

Run only Vision Engine tests:

    python -m pytest vision_engine/tests -v

Always use the current test output when reporting the test count.

## Current development status

Implemented:

- Input, finding, evidence-reference, and bounding-box models.
- Evidence-file validation.
- Deterministic mock detection.
- Static DOM defect heuristics.
- Gemini VLM provider integration.
- Prompting and structured response parsing.
- Screenshot cropping and coordinate translation.
- Single-crop and multiple-crop input support.
- Finding evaluation utilities.
- After-repair verification.
- Automated tests and controlled live-validation scripts.

Further work and team coordination:

- Validate against the team's actual demo website.
- Coordinate shared input and output contracts with the Browser Agent
  and Backend teams.
- Continue evaluating detection quality, false positives, and missed
  defects on additional examples.
- Review model usage, reliability, and performance before making
  production-level claims.

## Development guidelines

- Work on the assigned feature branch.
- Do not redefine shared schemas without team agreement.
- Keep mock findings distinguishable from DOM- and VLM-generated findings.
- Validate model output and handle provider errors.
- Never commit credentials or API keys.
- Run tests before committing.
- Submit changes for team review; do not merge into `main` independently.

## Limitations

DOM detection is limited to implemented heuristics. VLM findings can
contain false positives or missed defects and require validation.
The crop benchmark uses a small controlled fixture and does not establish
general model accuracy, API cost savings, or production performance.

The Vision Engine identifies and verifies findings; it does not itself
implement the complete browser repair and RPA workflow.
