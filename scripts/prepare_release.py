"""Check release source and repair deterministic test setup and waits."""

from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    for name in [
        "README.md",
        "project.json",
        "app/service.py",
        "app/advanced.py",
        "localdesk/vault.py",
        "run.py",
        "web/app.js",
    ]:
        if not (ROOT / name).is_file():
            raise ValueError("Required source is absent: " + name)

    path = ROOT / "tests/test_upgrade.py"
    text = path.read_text(encoding="utf-8")
    old = ["with sqlite3.connect(p) as db:", "with sqlite3.connect(q) as db:"]
    if any(value in text for value in old):
        if any(text.count(value) != 1 for value in old):
            raise ValueError("Review the changed database regression test.")
        text = text.replace(
            "import sqlite3\n", "import sqlite3\nfrom contextlib import closing\n"
        )
        text = text.replace(old[0], "with closing(sqlite3.connect(p)) as db, db:")
        text = text.replace(old[1], "with closing(sqlite3.connect(q)) as db, db:")
        path.write_text(text, encoding="utf-8")

    path = ROOT / "scripts/browser_check.py"
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "from playwright.sync_api import sync_playwright\n",
        "from playwright.sync_api import sync_playwright, expect\n",
    )
    old = """                checked(
                    "Batch recovery marks all five copies",
                    "5" in page.locator(".stat-value").last.inner_text(),
                )"""
    new = """                # Each file has its own job. A hidden job bar can be an
                # intermediate state, so wait for the final rendered batch result.
                expect(page.locator(".stat-value").last).to_have_text(
                    "5", timeout=30000
                )
                expect(
                    page.locator("[data-inspection]").filter(has_text="Copy created")
                ).to_have_count(5, timeout=30000)
                checked("Batch recovery marks all five copies")"""
    if old in text:
        if text.count(old) != 1:
            raise ValueError("Review the changed batch browser check.")
        text = text.replace(old, new)
    elif "intermediate state, so wait for the final rendered batch result" not in text:
        raise ValueError("The batch browser check has changed.")
    marker = '    config = json.loads((ROOT / "project.json").read_text())\n'
    if '"docs/browser-report.json").unlink' not in text:
        if marker not in text:
            raise ValueError("The browser-check setup has changed.")
        text = text.replace(
            marker,
            marker
            + '    (ROOT / "docs/browser-report.json").unlink(missing_ok=True)\n',
            1,
        )
    path.write_text(text, encoding="utf-8")
    shutil.rmtree(ROOT / "_runtime", ignore_errors=True)
    print("Source checked. Browser checks wait for all completed copies.")


if __name__ == "__main__":
    main()
