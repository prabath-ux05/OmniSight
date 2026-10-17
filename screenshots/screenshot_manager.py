"""
 Screenshot Management

Responsibilities:
- Create artifact directories
- Capture screenshots
- Return saved screenshot path
"""

from pathlib import Path


class ScreenshotManager:

    @staticmethod
    def create_run_directory(
        run_id: str,
        artifact_root: str = "artifacts"
    ) -> Path:

        run_dir = Path(artifact_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        return run_dir

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

        page.screenshot(
            path=str(screenshot_path),
            full_page=True
        )

        return str(screenshot_path)