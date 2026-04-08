"""Unit outline PDF download logic."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Page

from outline_dl.auth import LITEC_URL


def download_outlines(
    page: Page,
    unit_codes: list[str],
    output_dir: Path,
    timeout: int = 30000,
) -> dict[str, str]:
    """Download PDF outlines for each unit code.

    Returns a dict of {unit_code: status} where status is 'ok' or an error message.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    results: dict[str, str] = {}

    for code in unit_codes:
        print(f"\n--- {code} ---")
        try:
            _download_one(page, code, output_dir, timeout)
            results[code] = "ok"
        except Exception as e:
            print(f"  Error: {e}")
            results[code] = str(e)

    return results


def _download_one(page: Page, code: str, output_dir: Path, timeout: int) -> None:
    """Download a single unit outline PDF."""
    # Navigate to the outline page for this unit
    # Try direct URL pattern first
    url = f"{LITEC_URL}?unitCode={code}"
    print(f"  Navigating to {url}")
    page.goto(url, wait_until="networkidle", timeout=timeout)

    # Check if we landed on a page with the unit outline
    # Look for a PDF download link/button
    pdf_link = _find_pdf_link(page, code, timeout)

    if pdf_link:
        # Use Playwright download handling
        dest = output_dir / f"{code}.pdf"
        print("  Downloading PDF...")
        with page.expect_download(timeout=timeout) as download_info:
            pdf_link.click()
        download = download_info.value
        download.save_as(dest)
        print(f"  Saved to {dest}")
    else:
        # Maybe the page itself is the outline - try printing to PDF
        # Or look for other download mechanisms
        _try_alternative_download(page, code, output_dir, timeout)


def _find_pdf_link(page: Page, code: str, timeout: int):  # type: ignore[no-untyped-def]
    """Find a PDF download link on the current page."""
    # Try various selectors for PDF download links
    selectors = [
        "a[href*='.pdf']",
        "a[href*='pdf']",
        "a:has-text('Download')",
        "a:has-text('PDF')",
        "a:has-text('Print')",
        "button:has-text('Download')",
        "button:has-text('PDF')",
        "a:has-text('Unit Outline')",
        f"a:has-text('{code}')",
    ]

    for sel in selectors:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                return el
        except Exception:
            continue

    return None


def _try_alternative_download(
    page: Page, code: str, output_dir: Path, timeout: int
) -> None:
    """Fallback: try to save the page content as PDF or find the outline another way."""
    # Check if there's a form to search for the unit
    search_input = page.query_selector(
        "input[name*='unit'], input[name*='Unit'], input[placeholder*='unit'], "
        "input[placeholder*='Unit'], input[name*='search'], input[type='search']"
    )
    if search_input:
        print(f"  Found search field, searching for {code}...")
        search_input.fill(code)
        page.keyboard.press("Enter")
        page.wait_for_load_state("networkidle", timeout=timeout)

        # Try finding PDF link again after search
        pdf_link = _find_pdf_link(page, code, timeout)
        if pdf_link:
            dest = output_dir / f"{code}.pdf"
            print("  Downloading PDF...")
            with page.expect_download(timeout=timeout) as download_info:
                pdf_link.click()
            download = download_info.value
            download.save_as(dest)
            print(f"  Saved to {dest}")
            return

    # Last resort: save page as PDF via CDP
    print("  No PDF link found, saving page as PDF...")
    dest = output_dir / f"{code}.pdf"
    page.pdf(path=str(dest))
    print(f"  Saved page as PDF to {dest}")
