"""SSO login flow for Curtin University."""

from __future__ import annotations

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

LITEC_URL = "https://litec.curtin.edu.au/outline.cfm"


def login(page: Page, username: str, password: str, timeout: int = 30000) -> None:
    """Log in to Curtin's ForgeRock SSO via the LITEC redirect.

    Flow: LITEC -> SSO username -> SSO password -> redirect back to LITEC.
    """
    print(f"Navigating to {LITEC_URL} ...")
    page.goto(LITEC_URL, wait_until="networkidle", timeout=timeout)

    # --- Username step ---
    # ForgeRock SSO uses input[name='callback_1'] for both username and password
    try:
        page.wait_for_selector("input[name='callback_1']", timeout=timeout)
    except PlaywrightTimeout:
        print(f"  Current URL: {page.url}")
        print(f"  Page title: {page.title()}")
        msg = "Could not find username field on SSO page. Run without --headless to debug."
        raise SystemExit(msg)

    print("  Entering username...")
    page.fill("input[name='callback_1']", username)
    page.click("button[type='submit']")
    page.wait_for_timeout(3000)

    # --- Password step ---
    try:
        page.wait_for_selector("input[type='password']", timeout=timeout)
    except PlaywrightTimeout:
        print(f"  Current URL: {page.url}")
        msg = "Could not find password field. Run without --headless to debug."
        raise SystemExit(msg)

    print("  Entering password...")
    page.fill("input[type='password']", password)
    page.click("button[type='submit']")
    page.wait_for_timeout(5000)
    page.wait_for_load_state("networkidle", timeout=timeout)

    # --- Verify login success ---
    if "curtin.edu.au" not in page.url:
        print(f"  Current URL: {page.url}")
        msg = "Login may have failed — not redirected back to Curtin. Check credentials."
        raise SystemExit(msg)

    print("  Login successful!")
