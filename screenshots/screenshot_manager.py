
"""
Screenshot Management

Responsibilities:
- Create artifact directories
- Capture full-page screenshots
- Verify screenshot files
- Capture screenshot dimensions
- Save screenshot metadata
- Return saved screenshot path
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

        run_dir = Path(artifact_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        return run_dir

    @staticmethod
    def get_screenshot_dimensions(screenshot_path: str) -> dict:
        """
        Read the actual width and height from a PNG file.
        """

        path = Path(screenshot_path)

        if not path.exists():
            raise FileNotFoundError("Screenshot file not found")

        with open(path, "rb") as file:
            header = file.read(24)

        if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            raise ValueError("Invalid PNG screenshot")

        width, height = struct.unpack(">II", header[16:24])

        return {
            "width": width,
            "height": height
        }

    @staticmethod
    def save_screenshot(
        page,
        run_id: str,
        artifact_root: str = "artifacts"
    ) -> str:

        run_dir = ScreenshotManager.create_run_directory(
            run_id,
            artifact_root
        )

        screenshot_path = run_dir / "before.png"

        # Capture full-page screenshot
        page.screenshot(
            path=str(screenshot_path),
            full_page=True
        )

        # Verify screenshot creation
        if not screenshot_path.exists():
            raise FileNotFoundError(
                "Screenshot file was not created"
            )

        if screenshot_path.stat().st_size == 0:
            raise ValueError("Screenshot file is empty")

        # Get actual screenshot dimensions
        dimensions = ScreenshotManager.get_screenshot_dimensions(
            str(screenshot_path)
        )

        # Collect page metadata
        metadata = {
            "run_id": run_id,
            "url": page.url,
            "page_title": page.title(),
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "screenshot_path": str(screenshot_path),
            "screenshot_width": dimensions["width"],
            "screenshot_height": dimensions["height"],
            "full_page": True,
            "viewport": page.viewport_size
        }

        # Save metadata as JSON
        metadata_path = run_dir / "before_metadata.json"

        with open(metadata_path, "w", encoding="utf-8") as file:
            json.dump(
                metadata,
                file,
                indent=4,
                ensure_ascii=False
            )

        return str(screenshot_path)
