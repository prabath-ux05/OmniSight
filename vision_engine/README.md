
# OmniSight Vision Engine

The Vision Engine is the OmniSight module responsible for representing UI inspection inputs, validating evidence-file paths, and producing structured defect findings.

The current implementation uses a deterministic mock detector. Real screenshot and DOM analysis using a vision-language model is planned but has not yet been implemented.

## 🎯 Responsibilities

- Represent the evidence supplied for a UI inspection run.
- Validate supplied screenshot and DOM snapshot files.
- Produce structured findings using a predictable mock detector.
- Keep finding categories, severity, confidence, and evidence references consistent.
- Provide tests for valid inputs, invalid evidence, and mock behavior.
- Prepare for future integration with an approved vision-language model.

## 📁 Module Structure

```text
vision_engine/
├── detection/
│   └── mock_detector.py
├── tests/
│   ├── test_evidence_validator.py
│   └── test_mock_detector.py
├── models.py
├── evidence_validator.py
└── README.md
```

## 🧩 Current Components

### 1. Input and finding models

File: `models.py`

`VisionInput` represents the data supplied for an inspection run:

- `run_id`: Identifier for the inspection run.
- `url`: URL of the page being inspected.
- `screenshot_path`: Optional path to screenshot evidence.
- `dom_snapshot_path`: Optional path to DOM snapshot evidence.

At least one evidence path must be provided.

`VisionFinding` represents a potential UI defect and includes:

- `finding_id`
- `category`
- `severity`
- `confidence`
- `description`
- `selector` (optional)
- `evidence`
- `source`

The current supported categories are:

- `layout_overflow`
- `missing_visible_element`
- `broken_image`

Severity values currently include `low`, `medium`, `high`, and `critical`. Confidence is constrained to the range from `0.0` to `1.0`.

These interfaces are the current implementation and should be coordinated with the team before being treated as the final shared contract.

### 2. Evidence validation

File: `evidence_validator.py`

The `validate_evidence()` function checks supplied evidence paths.

It checks whether each supplied path:

1. Exists.
2. Points to a file rather than a directory.
3. Can be opened for reading.

The validator returns a list of error messages. An empty list indicates that the supplied evidence passed these file-level checks.

If one evidence file is invalid but another is usable, the validator can accept the available evidence while reporting the invalid path.

**Limitation:** This validation does not confirm that a screenshot contains valid image data or that a DOM snapshot contains valid HTML.

### 3. Mock detector

File: `detection/mock_detector.py`

The `detect_mock()` function:

1. Receives a `VisionInput`.
2. Validates its evidence paths.
3. Raises a `ValueError` if evidence validation fails.
4. Returns predictable sample findings when validation succeeds.

The current mock findings illustrate `layout_overflow` and `broken_image` categories.

**Important:** These are sample findings, not verified defects. The mock detector does not inspect image pixels, parse DOM content, or perform actual AI inference.

### 4. Tests

Directory: `tests/`

The existing tests cover:

- Valid screenshot evidence.
- Valid DOM snapshot evidence.
- Missing evidence files.
- Directories supplied instead of files.
- Partial acceptance when one evidence file remains usable.
- Predictable mock findings.
- Evidence-reference preservation.
- Input validation.
- Deterministic mock output.
- Evidence validation failures.

Run the tests to verify the current implementation rather than relying on a previously reported test count.

## ⚙️ Setup and Testing

Run these commands from the repository root with the project's virtual environment activated.

### Run all project tests

```powershell
python -m pytest -v
```

### Run only Vision Engine tests

```powershell
python -m pytest vision_engine/tests -v
```

### Check working-tree changes

```powershell
git status
git diff --check
git diff
```

## 📌 Current Development Status

- [x] Initial input and finding models.
- [x] Deterministic mock detector.
- [x] Evidence-file validation.
- [x] Evidence validation integrated into mock detection.
- [x] Initial tests for evidence handling and mock behavior.
- [ ] Clean-page mock scenario with zero findings.
- [ ] Additional tests for malformed inputs and unsupported categories.
- [ ] Final agreement on shared input/output contracts.
- [ ] Vision-language model provider interface.
- [ ] Prompt design and structured response parsing.
- [ ] Real screenshot and DOM content analysis.
- [ ] Tests for malformed model responses, provider failures, and timeouts.
- [ ] Integration with the Browser Agent and Backend.

## 🗺️ Next Steps

1. Verify the current tests and document the actual results.
2. Coordinate the clean-page mock scenario with the team.
3. Add tests for the agreed clean and defect scenarios.
4. Improve error handling and structured-output validation.
5. Confirm the approved model provider and credential availability.
6. Implement real VLM inference only when the required access is authorized.
7. Test against controlled examples and document false positives and missed defects.
8. Coordinate integration and submit the feature branch for team review.

## 🔒 Development Guidelines

- Do not redefine shared schemas without team agreement.
- Keep mock findings clearly distinguishable from VLM-generated findings.
- Do not claim that mock output represents actual visual detection.
- Never commit credentials or API keys.
- Test changes before committing.
- Work on the assigned feature branch and follow the team's pull request process.
- Do not merge into `main` without approval.

## ⚠️ Limitations

The current implementation validates evidence-file accessibility and returns mock findings. It does not yet detect real UI defects, localize elements with bounding boxes, generate repairs, or execute repaired scripts.

Any future model integration must validate model output, handle provider errors, and preserve the agreed finding schema.
## 1. Purpose

The Vision Engine is responsible for analyzing website screenshots and
available DOM evidence to identify potential user-interface (UI) defects.

The initial implementation will use a deterministic mock detector.
Real Vision-Language Model (VLM) integration will be added in a later phase.

## 2. Responsibilities

- Define a clear input and output interface for the Vision Engine.
- Validate incoming screenshot and DOM evidence.
- Implement a deterministic mock detector for initial development.
- Identify potential UI defects using the agreed defect categories.
- Return structured findings with severity, confidence, descriptions,
  and evidence references.
- Validate finding data and handle invalid inputs or errors.
- Write automated tests for successful and failure cases.
- Prepare the interface for future VLM integration.
- Coordinate interface requirements with the Browser Agent and Backend teams.

## 3. Planned Defect Categories

The following are initial examples and must be confirmed against the
team's agreed schema:

- Layout overflow.
- Missing visible elements.
- Broken images.
- Overlapping elements.
- Misaligned elements.
- Clipped or hidden content.
- Incorrect spacing.

The final category names must match the shared team contract.

## 4. Input Evidence

The engine is expected to receive:

- Website screenshots captured by the Browser Agent.
- DOM evidence or snapshots, when available and agreed upon.
- Relevant evidence paths and metadata provided by the existing interface.

The implementation must use the actual Browser Agent output format.
It must not assume that unavailable evidence exists.

## 5. Structured Findings

Each finding should follow the team's agreed schema and may include:

- Finding ID.
- Defect category.
- Severity.
- Confidence score.
- Defect description.
- Optional affected-element selector.
- Evidence references.
- Additional fields only when agreed upon by the team.

Field names, allowed categories, and validation rules must remain
consistent with the shared interface.

## 6. Development Plan

### Week 1: Foundation and Mock Detection

- Inspect the existing repository and interfaces.
- Establish the Vision Engine input and output contract.
- Implement a deterministic mock detector.
- Add initial automated tests.
- Verify that the module imports and returns structured mock findings.

### Week 2: Validation and VLM Preparation

- Refine defect categories and output validation.
- Prepare a minimal VLM provider interface.
- Develop prompts and response parsing.
- Test malformed inputs and failure cases.

### Week 3: VLM Integration and Pipeline Testing

- Integrate the team-approved VLM provider if access is available.
- Test using controlled website screenshots.
- Evaluate false positives, missed defects, and limitations.
- Keep the mock implementation usable for testing.

### Week 4: Reliability and Handover

- Run relevant automated and integration tests.
- Confirm compatibility with the Browser Agent and Backend.
- Document setup, configuration, limitations, and test results.
- Prepare the changes for team review and integration.

## 7. Directory Structure

- detection/: Defect detection implementation.
- prompting/: Prompts and VLM response-processing logic.
- tests/: Vision Engine automated tests.
- __init__.py: Python package initialization.

## 8. Current Development Status

Current progress:

- Initial Vision Engine README created.
- Python development environment and project dependencies installed.

Not yet implemented or verified:

- Vision Engine input and output interface.
- Deterministic mock detector.
- Finding validation.
- Automated Vision Engine tests.
- Real VLM integration.

These items will be implemented and verified incrementally.
This section must be updated as actual progress is made.

## 9. Team Integration

### Browser Agent

- Agree on the screenshot and DOM evidence format.
- Confirm how evidence paths and relevant metadata are passed.
- Test against actual browser-captured evidence when available.

### Backend

- Agree on the structured finding schema.
- Confirm the engine's invocation interface.
- Keep field names, categories, confidence, and evidence references consistent.

### Team Lead

- Confirm shared contracts and defect categories.
- Confirm the VLM provider before real model integration.
- Request approval before shared-schema changes.

## 10. Development Rules

- Work only on the assigned feature/vision-engine branch.
- Inspect existing code before modifying interfaces.
- Make small, testable changes.
- Run relevant tests and report actual results.
- Do not commit credentials or secrets.
- Do not claim mock or real-model functionality works until verified.
- Keep mock behavior clearly distinguishable from real model output.
- Submit changes for review; do not merge into main independently.
