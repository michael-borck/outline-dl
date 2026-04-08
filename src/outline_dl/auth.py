"""SSO login flow for Curtin University."""

from __future__ import annotations

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

LITEC_URL = "https://litec.curtin.edu.au/outline.cfm"


def login(page: Page, username: str, password: str, timeout: int = 30000) -> None:
    """Log in to Curtin SSO via the LITEC redirect.

    The flow is:
    1. Navigate to LITEC -> redirects to SSO
    2. SSO shows username field, fill and submit
    3. SSO shows password field, fill and submit
    4. Redirects back to LITEC on success
    """
    print(f"Navigating to {LITEC_URL} ...")
    page.goto(LITEC_URL, wait_until="networkidle", timeout=timeout)

    # --- Username step ---
    # Try common SSO username field selectors
    username_sel = _find_first(
        page,
        [
            "input[name='UserName']",
            "input[name='username']",
            "input[name='loginfmt']",      # Microsoft SSO
            "input[type='email']",
            "input[id='username']",
            "input[id='userNameInput']",    # ADFS
        ],
        timeout=timeout,
    )
    if not username_sel:
        # Dump page info for debugging
        print(f"  Current URL: {page.url}")
        print(f"  Page title: {page.title()}")
        msg = "Could not find username field on SSO page. Run without --headless to debug."
        raise SystemExit(msg)

    print("  Found username field, entering credentials...")
    page.fill(username_sel, username)

    # Submit username
    _click_submit(page)
    page.wait_for_load_state("networkidle", timeout=timeout)

    # --- Password step ---
    password_sel = _find_first(
        page,
        [
            "input[name='Password']",
            "input[name='password']",
            "input[name='passwd']",         # Microsoft SSO
            "input[type='password']",
            "input[id='passwordInput']",    # ADFS
        ],
        timeout=timeout,
    )
    if not password_sel:
        print(f"  Current URL: {page.url}")
        print(f"  Page title: {page.title()}")
        msg = "Could not find password field on SSO page. Run without --headless to debug."
        raise SystemExit(msg)

    print("  Found password field, entering password...")
    page.fill(password_sel, password)

    # Submit password
    _click_submit(page)
    page.wait_for_load_state("networkidle", timeout=timeout)

    # --- Verify login success ---
    # After successful SSO, we should be back on litec.curtin.edu.au
    if "curtin.edu.au" not in page.url:
        # Check for "stay signed in" prompt (Microsoft SSO)
        try:
            stay_signed_in = page.wait_for_selector(
                "input[value='No'], input[value='Yes'], #idBtn_Back, #idSIButton9",
                timeout=5000,
            )
            if stay_signed_in:
                print("  Handling 'stay signed in' prompt...")
                stay_signed_in.click()
                page.wait_for_load_state("networkidle", timeout=timeout)
        except PlaywrightTimeout:
            pass

    if "curtin.edu.au" not in page.url:
        print(f"  Current URL: {page.url}")
        msg = "Login may have failed — not redirected back to Curtin. Check credentials."
        raise SystemExit(msg)

    print("  Login successful!")


def _find_first(page: Page, selectors: list[str], timeout: int = 10000) -> str | None:
    """Try multiple selectors, return the first one found."""
    # First do a quick check for any that are already visible
    for sel in selectors:
        if page.query_selector(sel):
            return sel

    # Wait a bit for any to appear
    for sel in selectors:
        try:
            page.wait_for_selector(sel, timeout=3000)
            return sel
        except PlaywrightTimeout:
            continue

    return None


def _click_submit(page: Page) -> None:
    """Click the submit/next button on the SSO form."""
    submit_selectors = [
        "input[type='submit']",
        "button[type='submit']",
        "#submitButton",
        "#idSIButton9",              # Microsoft SSO "Next"
        "span.submit",
        "button.btn-primary",
    ]
    for sel in submit_selectors:
        btn = page.query_selector(sel)
        if btn and btn.is_visible():
            btn.click()
            return

    # Fallback: press Enter
    page.keyboard.press("Enter")
