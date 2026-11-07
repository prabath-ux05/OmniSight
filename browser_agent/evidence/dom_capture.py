from pathlib import Path


class DOMCapture:

    @staticmethod
    def save_dom_snapshot(
        page,
        run_id: str,
        artifact_root: str = "artifacts"
    ) -> str:

        run_dir = Path(artifact_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        dom_path = run_dir / "dom.html"

        html_content = page.content()

        with open(dom_path, "w", encoding="utf-8") as file:
            file.write(html_content)

        return str(dom_path)

