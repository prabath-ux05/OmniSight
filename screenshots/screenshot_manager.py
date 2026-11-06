
"""
Screenshot Management

Features:
- Create run-based artifact directories
- Capture before and after screenshots
- Verify screenshot files
- Read screenshot dimensions
- Save screenshot metadata
- Maintain backward compatibility
"""

from pathlib import Path
from datetime import datetime, timezone
import json
import struct


class ScreenshotManager:

    @staticmethod
    def create_run_directory(
        run_id: str,
        artifact_root: str = "artifacts"
    ) -> Path:

        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id is required")

        # Prevent run IDs from escaping the artifact directory
        if (
            run_id in (".", "..")
            or Path(run_id).name != run_id
            or "/" in run_id
            or "\\" in run_id
            or ":" in run_id
        ):
            raise ValueError("Invalid run_id")

        run_dir = Path(artifact_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        return run_dir

    @staticmethod
    def get_screenshot_dimensions(
        screenshot_path: str
    ) -> dict:

        path = Path(screenshot_path)

        if not path.is_file():
            raise FileNotFoundError(
                "Screenshot file not found"
            )

        with open(path, "rb") as file:
            header = file.read(24)

        if (
            len(header) < 24
            or header[:8] != b"\x89PNG\r\n\x1a\n"
            or header[12:16] != b"IHDR"
        ):
            raise ValueError("Invalid PNG screenshot")

        width, height = struct.unpack(
            ">II",
            header[16:24]
        )

        return {
            "width": width,
            "height": height
        }

    @staticmethod
    def save_screenshot(
        page,
        run_id: str,
        artifact_root: str = "artifacts",
        stage: str = "before"
    ) -> str:

        # Only allow known capture stages
        if stage not in ("before", "after"):
            raise ValueError(
                "stage must be 'before' or 'after'"
            )

        run_dir = ScreenshotManager.create_run_directory(
            run_id,
            artifact_root
        )

        screenshot_path = run_dir / f"{stage}.png"

        # Capture full-page screenshot
        page.screenshot(
            path=str(screenshot_path),
            full_page=True
        )

        # Verify screenshot file
        if not screenshot_path.is_file():
            raise FileNotFoundError(
                "Screenshot file was not created"
            )

        if screenshot_path.stat().st_size == 0:
            raise ValueError(
                "Screenshot file is empty"
            )

        dimensions = (
            ScreenshotManager.get_screenshot_dimensions(
                str(screenshot_path)
            )
        )

        metadata = {
            "run_id": run_id,
            "stage": stage,
            "url": page.url,
            "page_title": page.title(),
            "captured_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "screenshot_path": str(screenshot_path),
            "screenshot_width": dimensions["width"],
            "screenshot_height": dimensions["height"],
            "full_page": True,
            "viewport": page.viewport_size
        }

        metadata_path = (
            run_dir / f"{stage}_metadata.json"
        )

        with open(
            metadata_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                metadata,
                file,
                indent=4,
                ensure_ascii=False
            )

        return str(screenshot_path)
