"""Playwright browser pool — thread-safe, each thread gets its own browser context.
Avoids asyncio conflicts by using subprocess isolation for Playwright."""

import logging
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from config import RATE_LIMIT_SLEEP

log = logging.getLogger(__name__)

_lock = threading.Lock()
_local = threading.local()


def _get_pw():
    """Get thread-local playwright + browser instance."""
    if not hasattr(_local, "pw") or _local.pw is None:
        from playwright.sync_api import sync_playwright
        _local.pw = sync_playwright().start()
        _local.browser = _local.pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-extensions",
            ],
        )
        log.info("Browser launched for thread %s", threading.current_thread().name)
    return _local.pw, _local.browser


def fetch_page(url: str, wait_selector: str = None, wait_ms: int = 3000) -> str:
    """Fetch a page with full Chrome, return HTML. Thread-safe."""
    _, browser = _get_pw()
    ctx = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ),
        java_script_enabled=True,
        bypass_csp=True,
    )
    ctx.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        window.chrome = {runtime: {}};
    """)
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        if wait_selector:
            try:
                page.wait_for_selector(wait_selector, timeout=10000)
            except Exception:
                pass
        page.wait_for_timeout(wait_ms)
        html = page.content()
    finally:
        page.close()
        ctx.close()
    time.sleep(RATE_LIMIT_SLEEP)
    return html


def shutdown():
    """Cleanup — called from main thread. Each thread should ideally clean up its own."""
    if hasattr(_local, "browser") and _local.browser:
        try:
            _local.browser.close()
        except Exception:
            pass
    if hasattr(_local, "pw") and _local.pw:
        try:
            _local.pw.stop()
        except Exception:
            pass
