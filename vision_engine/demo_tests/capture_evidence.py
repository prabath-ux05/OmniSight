
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
HTML_FILE = BASE_DIR / "demo_site.html"
OUTPUT_DIR = BASE_DIR / "evidence"

OUTPUT_DIR.mkdir(exist_ok=True)

scenarios = [
    "clean",
    "overflow",
    "broken_image",
]

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)

    for scenario in scenarios:
        page = browser.new_page(
            viewport={"width": 1365, "height": 900}
        )

        console_errors = []
        page.on("pageerror", lambda error: console_errors.append(str(error)))

        page.goto(HTML_FILE.as_uri(), wait_until="load")

        if scenario == "clean":
            page.locator("section").nth(1).evaluate(
                "(element) => element.remove()"
            )
            page.locator("section").nth(1).evaluate(
                "(element) => element.remove()"
            )

        elif scenario == "overflow":
            page.locator("section").nth(0).evaluate(
                "(element) => element.remove()"
            )
            page.locator("section").nth(1).evaluate(
                "(element) => element.remove()"
            )

        elif scenario == "broken_image":
            page.locator("section").nth(0).evaluate(
                "(element) => element.remove()"
            )
            page.locator("section").nth(0).evaluate(
                "(element) => element.remove()"
            )

        screenshot_path = OUTPUT_DIR / f"{scenario}.png"
        dom_path = OUTPUT_DIR / f"{scenario}.html"

        page.screenshot(
            path=str(screenshot_path),
            full_page=True
        )

        dom_path.write_text(
            page.content(),
            encoding="utf-8"
        )

        print(f"\nScenario: {scenario}")
        print(f"Screenshot: {screenshot_path}")
        print(f"DOM: {dom_path}")
        print(f"Page errors: {console_errors}")

        if scenario == "broken_image":
            image_status = page.locator("img").evaluate(
                "(image) => ({complete: image.complete, naturalWidth: image.naturalWidth})"
            )
            print(f"Broken image status: {image_status}")

        page.close()

    browser.close()

print("\nAll evidence captured successfully.")
