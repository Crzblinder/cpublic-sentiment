"""End-to-end smoke test for the web UI.

Starts the backend and frontend dev servers, then uses Playwright to verify
that the read-only pages (dashboard, cases, enterprises) render without errors
and that the backend API returns data. This keeps the test fast and avoids
waiting for embedding model downloads on first run.

To run the full analyze flow, seed the database first and ensure the embedding
model is cached (see backend/scripts/seed_data.py).
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

PYTHON = sys.executable
NODE = shutil.which("node") or "node"

BACKEND_PORT = 8000
FRONTEND_PORT = 5173

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(ROOT / ".playwright-browsers"))
os.environ.setdefault("OPENAI_API_KEY", "")


def find_chrome_executable() -> Path | None:
    """Locate the Chromium binary downloaded by Playwright."""
    browsers_path = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", Path.home() / ".cache" / "ms-playwright"))
    if sys.platform == "win32":
        candidates = list(browsers_path.rglob("chrome.exe"))
    else:
        candidates = [p for p in browsers_path.rglob("chrome") if p.is_file()]
    return candidates[0] if candidates else None


def wait_for_port(port: int, timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return
        except OSError:
            time.sleep(0.5)
    raise RuntimeError(f"Port {port} did not become ready within {timeout}s")


def run_backend_setup() -> None:
    subprocess.run([PYTHON, "scripts/init_db.py"], cwd=BACKEND_DIR, check=True)
    subprocess.run([PYTHON, "../e2e/seed_minimal.py"], cwd=BACKEND_DIR, check=True)


def start_backend() -> subprocess.Popen:
    proc = subprocess.Popen(
        [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=BACKEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**os.environ, "OPENAI_API_KEY": ""},
    )
    return proc


def start_frontend() -> subprocess.Popen:
    proc = subprocess.Popen(
        [NODE, "./node_modules/vite/bin/vite.js", "--host", "127.0.0.1"],
        cwd=FRONTEND_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def kill_proc(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], check=False)
        else:
            proc.terminate()
        proc.wait(timeout=10)


def test_core_pages() -> None:
    chrome = find_chrome_executable()
    if chrome is None:
        raise FileNotFoundError(
            "Playwright Chromium not found. "
            "Set PLAYWRIGHT_BROWSERS_PATH and run 'playwright install chromium'."
        )

    print(f"Using Python: {PYTHON}")
    print(f"Using Node: {NODE}")
    print(f"Using Chromium: {chrome}")

    print("Setting up local database...")
    run_backend_setup()

    print("Starting backend...")
    backend_proc = start_backend()
    print("Starting frontend...")
    frontend_proc = start_frontend()

    try:
        wait_for_port(BACKEND_PORT)
        print("Backend ready.")
        wait_for_port(FRONTEND_PORT)
        print("Frontend ready.")

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                executable_path=str(chrome),
            )
            page = browser.new_page()
            page.set_default_timeout(30_000)

            try:
                # Dashboard
                page.goto("http://127.0.0.1:5173/")
                page.wait_for_load_state("networkidle")
                assert "CPublic Sentiment" in page.content()
                page.wait_for_selector("text=累计分析事件")
                print("Dashboard loaded.")

                # Cases page
                page.click("text=案例库")
                page.wait_for_selector("text=风险案例库")
                page.wait_for_selector("table tbody tr")
                rows = page.locator("table tbody tr").count()
                assert rows > 0, "Expected cases to be listed"
                print(f"Cases page loaded with {rows} rows.")

                # Enterprises page
                page.click("text=企业画像")
                page.wait_for_selector("text=企业画像")
                page.wait_for_selector("table tbody tr")
                rows = page.locator("table tbody tr").count()
                assert rows > 0, "Expected enterprises to be listed"
                print(f"Enterprises page loaded with {rows} rows.")

                # Evaluation page (metrics only, no A/B run to avoid embeddings)
                page.click("text=效果评估")
                page.wait_for_selector("text=效果评估")
                page.wait_for_selector("text=准确率")
                print("Evaluation page loaded.")

                print("E2E smoke test passed.")
            except Exception:
                page.screenshot(path=str(ROOT / "e2e" / "failure.png"))
                raise
            finally:
                browser.close()
    finally:
        kill_proc(frontend_proc)
        kill_proc(backend_proc)


if __name__ == "__main__":
    test_core_pages()
