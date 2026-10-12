
# OmniSight Vision Engine

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
