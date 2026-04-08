"""Unit outline PDF download logic via the OutSystems Outlines Hub."""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import ElementHandle, Frame, Page


def download_outlines(
    page: Page,
    unit_codes: list[str],
    output_dir: Path,
    campus: str = "Bentley Perth Campus",
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
            _download_one(page, code, output_dir, campus, timeout)
            results[code] = "ok"
        except Exception as e:
            print(f"  Error: {e}")
            results[code] = str(e)

    return results


def _get_iframe(page: Page) -> Frame:
    """Get the OutSystems iframe."""
    for f in page.frames:
        if "outsystems" in f.url:
            return f
    raise RuntimeError("OutSystems iframe not found")


def _download_one(
    page: Page, code: str, output_dir: Path, campus: str, timeout: int
) -> None:
    """Download a single unit outline PDF."""
    iframe = _get_iframe(page)

    # --- Step 1: Select the unit from the first dropdown ---
    _select_unit(page, iframe, code, timeout)

    # --- Step 2: Wait for availabilities to load ---
    print("  Waiting for availabilities...")
    page.wait_for_timeout(8000)

    # --- Step 3: Pick matching availabilities ---
    availabilities = _get_matching_availabilities(iframe, campus)
    if not availabilities:
        raise RuntimeError(f"No availabilities found for {code} (campus: {campus})")

    for avail_text, avail_opt in availabilities:
        print(f"  Availability: {avail_text}")

        # Open the availability dropdown and click the option
        avail_eles = iframe.query_selector_all(".vscomp-ele")
        if len(avail_eles) >= 2:
            avail_toggle = avail_eles[1].query_selector(".vscomp-toggle-button")
            if avail_toggle:
                avail_toggle.click()
                page.wait_for_timeout(1000)

        avail_opt.click()

        # Wait for outline to load
        print("  Waiting for outline to load...")
        page.wait_for_timeout(10000)

        download_btn = iframe.query_selector("button:has-text('Download')")
        if not download_btn:
            print("  Warning: No Download button found, skipping this availability")
            continue

        print("  Downloading PDF...")
        with page.expect_download(timeout=timeout) as download_info:
            download_btn.click()
        download = download_info.value

        filename = download.suggested_filename or f"{code}.pdf"
        dest = output_dir / filename
        download.save_as(dest)
        print(f"  Saved: {dest}")

    # --- Clear selection for next unit ---
    _clear_selection(iframe)
    page.wait_for_timeout(2000)


def _select_unit(page: Page, iframe: Frame, code: str, timeout: int) -> None:
    """Search for and select a unit code from the first vscomp dropdown."""
    # Click the first dropdown toggle to open it
    toggle = iframe.query_selector(".vscomp-toggle-button")
    if not toggle:
        raise RuntimeError("Could not find unit dropdown")
    toggle.click()
    page.wait_for_timeout(500)

    # Type the unit code into the search box
    search = iframe.query_selector("input.vscomp-search-input")
    if not search:
        raise RuntimeError("Could not find search input in unit dropdown")
    search.fill(code)
    page.wait_for_timeout(2000)

    # Find matching options (pick the one with the highest version [V.X])
    dropboxes = iframe.query_selector_all(".vscomp-dropbox-wrapper")
    if not dropboxes:
        raise RuntimeError("Could not find dropdown options container")

    unit_dropbox = dropboxes[0]
    options = unit_dropbox.query_selector_all(".vscomp-option")

    best_option = None
    best_version = -1
    for opt in options:
        is_hidden = iframe.evaluate(
            "el => el.classList.contains('hide')", opt
        )
        if is_hidden:
            continue
        tooltip = opt.query_selector(".vscomp-option-text")
        text = tooltip.get_attribute("data-tooltip") if tooltip else ""
        if not text or code not in text:
            continue
        # Extract version number from [V.X]
        version_match = re.search(r"\[V\.(\d+)\]", text)
        version = int(version_match.group(1)) if version_match else 0
        if version > best_version:
            best_version = version
            best_option = opt

    if not best_option:
        raise RuntimeError(f"No matching unit found for {code}")

    tooltip = best_option.query_selector(".vscomp-option-text")
    text = tooltip.get_attribute("data-tooltip") if tooltip else code
    print(f"  Selected: {text}")
    best_option.click()


def _get_matching_availabilities(
    iframe: Frame, campus: str
) -> list[tuple[str, ElementHandle]]:
    """Get matching availabilities, filtered by campus, sorted by latest first.

    Returns list of (text, element) tuples.
    """
    dropboxes = iframe.query_selector_all(".vscomp-dropbox-wrapper")
    if len(dropboxes) < 2:
        raise RuntimeError("Availability dropdown not found")

    avail_dropbox = dropboxes[1]
    options = avail_dropbox.query_selector_all(".vscomp-option")

    if not options:
        raise RuntimeError("No availability options found")

    is_all = campus.lower() == "all"

    # Collect and parse all matching availabilities
    parsed: list[tuple[int, int, str, ElementHandle]] = []
    for opt in options:
        tooltip = opt.query_selector(".vscomp-option-text")
        text = tooltip.get_attribute("data-tooltip") if tooltip else ""
        if not text:
            continue

        # Filter by campus (unless "all")
        if not is_all and campus.lower() not in text.lower():
            continue

        # Parse: "2026 Semester 1, [Internal] Bentley Perth Campus"
        year_match = re.search(r"(\d{4})", text)
        year = int(year_match.group(1)) if year_match else 0

        period_match = re.search(r"(?:Semester|Trimester)\s+(\d+)", text)
        period_num = int(period_match.group(1)) if period_match else 0

        parsed.append((year, period_num, text, opt))

    # Sort by year desc, then period desc (latest first)
    parsed.sort(key=lambda x: (x[0], x[1]), reverse=True)

    if is_all:
        # Return all, but only the latest year+period combo per campus
        return [(text, opt) for _, _, text, opt in parsed]

    # For a specific campus, return just the best (latest) one
    if parsed:
        _, _, text, opt = parsed[0]
        return [(text, opt)]

    return []


def _clear_selection(iframe: Frame) -> None:
    """Clear the unit selection to prepare for the next unit."""
    clear_btns = iframe.query_selector_all(".vscomp-clear-button")
    # Clear in reverse order (availability first, then unit)
    for btn in reversed(clear_btns):
        try:
            if btn.is_visible():
                btn.click()
        except Exception:
            pass
