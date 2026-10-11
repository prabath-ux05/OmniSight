
# OmniSight Vision Engine

## Purpose

The Vision Engine is responsible for analyzing website screenshots
and identifying potential user-interface (UI) defects.

## Responsibilities

- Screenshot validation and image processing.
- Vision-language model integration.
- Prompt engineering for visual defect analysis.
- Structured defect report generation.
- Model response validation.
- Testing and evaluation of detection results.

## Planned Defect Categories

- Overlapping elements.
- Misaligned elements.
- Clipped or hidden content.
- Incorrect spacing.
- Broken visual layouts.

## Planned Inputs

- Website screenshots.
- Relevant HTML or DOM context, when available.
- Viewport information, when available.

## Planned Outputs

- Defect type and description.
- Severity.
- Affected element.
- Visual evidence.
- Suggested repair.
- Bounding-box coordinates, when supported.

## Directory Structure

- detection/: detection-related implementation.
- prompting/: visual analysis prompts.
- tests/: automated tests.
- __init__.py: Python package initialization.

## Development Status

Initial development. Functional implementation, model integration,
and evaluation will be completed incrementally.

## Team Integration

The input and output interfaces will be agreed upon with the
Browser Agent, Self-Healing, and Backend module owners.
