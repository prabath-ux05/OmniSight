from pathlib import Path


class DOMCapture:

    @staticmethod
    def save_dom_snapshot(
        page,
        run_id: str,
        artifact_root: str = "artifacts",
        stage: str = None,
        viewport: str = None,
    ) -> str:

        run_dir = Path(artifact_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{stage}_dom_{viewport}.html" if (stage and viewport) else (f"dom_{viewport}.html" if viewport else "dom.html")
        dom_path = run_dir / filename

        html_content = page.content()

        with open(dom_path, "w", encoding="utf-8") as file:
            file.write(html_content)

        legacy_path = run_dir / "dom.html"
        if viewport and (viewport == "desktop" or not legacy_path.exists()):
            with open(legacy_path, "w", encoding="utf-8") as file:
                file.write(html_content)

        return str(dom_path)

