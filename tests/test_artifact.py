from pathlib import Path

from screenshots.screenshot_manager import ScreenshotManager


def test_run_directory_creation():
    run_dir = ScreenshotManager.create_run_directory(
        "sample_run"
    )

    assert Path(run_dir).is_dir()