"""Unit outline PDF download logic via the OutSystems Outlines Hub."""

from __future__ import annotations

import re
from pathlib import Path

from playwright.sync_api import ElementHandle, Frame, Page

from outline_dl.interactive import pick_items


def download_outlines(
    page: Page,
    unit_codes: list[str],
    output_dir: Path,
    campus: str = "Bentley Perth Campus",
    overwrite: bool = False,
    interactive: bool = False,
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
            _download_one(page, code, output_dir, campus, overwrite, interactive, timeout)
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
    page: Page,
    code: str,
    output_dir: Path,
    campus: str,
    overwrite: bool,
    interactive: bool,
    timeout: int,
) -> None:
    """Download a single unit outline PDF."""
    iframe = _get_iframe(page)

    # --- Step 1: Search for the unit and get versions ---
    versions = _search_unit_versions(page, iframe, code, timeout)
    if not versions:
        raise RuntimeError(f"No matching unit found for {code}")

    # --- Step 2: Pick version(s) ---
    if interactive and len(versions) > 1:
        version_texts = [text for text, _ in versions]
        selected = pick_items("Select version", version_texts, default_indices=[0])
        if not selected:
            print("  Skipped.")
            return
        versions = [versions[i] for i in selected]
    else:
        # Auto-select: latest version (first in list, already sorted)
        versions = [versions[0]]

    for version_text, version_opt in versions:
        print(f"  Version: {version_text}")
        version_opt.click()

        # --- Step 3: Wait for availabilities to load ---
        print("  Waiting for availabilities...")
        page.wait_for_timeout(8000)

        # --- Step 4: Get and pick availabilities ---
        # Re-acquire iframe in case it changed
        iframe = _get_iframe(page)
        all_availabilities = _get_all_availabilities(iframe)
        if not all_availabilities:
            print("  No availabilities found.")
            _clear_selection(iframe)
            page.wait_for_timeout(2000)
            continue

        if interactive:
            # Show all availabilities, pre-select campus-matching ones
            avail_texts = [text for text, _ in all_availabilities]
            default_sel = _default_availability_indices(avail_texts, campus)
            selected = pick_items("Select availabilities", avail_texts, default_sel)
            if not selected:
                print("  Skipped.")
                _clear_selection(iframe)
                page.wait_for_timeout(2000)
                continue
            chosen = [all_availabilities[i] for i in selected]
        else:
            # Auto-select based on campus filter
            chosen = _filter_availabilities(all_availabilities, campus)
            if not chosen:
                raise RuntimeError(
                    f"No availabilities for {code} (campus: {campus})"
                )

        # --- Step 5: Download each selected availability ---
        for avail_text, avail_opt in chosen:
            _download_availability(
                page, iframe, code, avail_text, avail_opt,
                output_dir, overwrite, timeout,
            )

        # --- Clear selection for next unit ---
        _clear_selection(iframe)
        page.wait_for_timeout(2000)


def _search_unit_versions(
    page: Page, iframe: Frame, code: str, timeout: int
) -> list[tuple[str, ElementHandle]]:
    """Search for a unit code and return all matching versions, latest first."""
    toggle = iframe.query_selector(".vscomp-toggle-button")
    if not toggle:
        raise RuntimeError("Could not find unit dropdown")
    toggle.click()
    page.wait_for_timeout(500)

    search = iframe.query_selector("input.vscomp-search-input")
    if not search:
        raise RuntimeError("Could not find search input in unit dropdown")
    search.fill(code)
    page.wait_for_timeout(2000)

    dropboxes = iframe.query_selector_all(".vscomp-dropbox-wrapper")
    if not dropboxes:
        raise RuntimeError("Could not find dropdown options container")

    unit_dropbox = dropboxes[0]
    options = unit_dropbox.query_selector_all(".vscomp-option")

    found: list[tuple[int, str, ElementHandle]] = []
    for opt in options:
        is_hidden = iframe.evaluate("el => el.classList.contains('hide')", opt)
        if is_hidden:
            continue
        tooltip = opt.query_selector(".vscomp-option-text")
        text = tooltip.get_attribute("data-tooltip") if tooltip else ""
        if not text or code not in text:
            continue
        version_match = re.search(r"\[V\.(\d+)\]", text)
        version = int(version_match.group(1)) if version_match else 0
        found.append((version, text, opt))

    # Sort by version descending (latest first)
    found.sort(key=lambda x: x[0], reverse=True)
    return [(text, opt) for _, text, opt in found]


def _get_all_availabilities(
    iframe: Frame,
) -> list[tuple[str, ElementHandle]]:
    """Get all availabilities, sorted by year/period descending."""
    dropboxes = iframe.query_selector_all(".vscomp-dropbox-wrapper")
    if len(dropboxes) < 2:
        return []

    avail_dropbox = dropboxes[1]
    options = avail_dropbox.query_selector_all(".vscomp-option")

    parsed: list[tuple[int, int, str, ElementHandle]] = []
    for opt in options:
        tooltip = opt.query_selector(".vscomp-option-text")
        text = tooltip.get_attribute("data-tooltip") if tooltip else ""
        if not text:
            continue

        year_match = re.search(r"(\d{4})", text)
        year = int(year_match.group(1)) if year_match else 0

        period_match = re.search(r"(?:Semester|Trimester)\s+(\d+)", text)
        period_num = int(period_match.group(1)) if period_match else 0

        parsed.append((year, period_num, text, opt))

    parsed.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return [(text, opt) for _, _, text, opt in parsed]


def _default_availability_indices(texts: list[str], campus: str) -> list[int]:
    """Determine which availabilities should be pre-selected."""
    if campus.lower() == "all":
        return list(range(len(texts)))
    return [i for i, t in enumerate(texts) if campus.lower() in t.lower()]


def _filter_availabilities(
    availabilities: list[tuple[str, ElementHandle]],
    campus: str,
) -> list[tuple[str, ElementHandle]]:
    """Filter availabilities by campus (non-interactive mode)."""
    is_all = campus.lower() == "all"

    if is_all:
        return availabilities

    matching = [
        (text, opt) for text, opt in availabilities
        if campus.lower() in text.lower()
    ]
    # Return just the best (latest) one for the specific campus
    return matching[:1]


def _download_availability(
    page: Page,
    iframe: Frame,
    code: str,
    avail_text: str,
    avail_opt: ElementHandle,
    output_dir: Path,
    overwrite: bool,
    timeout: int,
) -> None:
    """Download a single availability's PDF."""
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
        return

    # Check if a file for this unit+availability already exists
    if not overwrite:
        existing = _find_existing(output_dir, code, avail_text)
        if existing:
            print(f"  Already exists: {existing} (use --overwrite to re-download)")
            return

    print("  Downloading PDF...")
    with page.expect_download(timeout=timeout) as download_info:
        download_btn.click()
    download = download_info.value

    filename = download.suggested_filename or f"{code}.pdf"
    dest = output_dir / filename

    download.save_as(dest)
    print(f"  Saved: {dest}")


def _find_existing(output_dir: Path, code: str, avail_text: str) -> Path | None:
    """Check if a PDF for this unit+availability already exists.

    Filenames follow the pattern:
    "COMP1000 Unix and C Programming Semester 1 2026 Bentley Perth Campus INT.pdf"
    """
    if not output_dir.exists():
        return None

    # Extract key parts from availability text for matching
    # e.g. "2026 Semester 1, [Internal] Bentley Perth Campus"
    year_match = re.search(r"(\d{4})", avail_text)
    period_match = re.search(r"(Semester|Trimester)\s+\d+", avail_text)
    year = year_match.group(1) if year_match else ""
    period = period_match.group(0) if period_match else ""

    for f in output_dir.glob(f"{code}*.pdf"):
        name = f.name
        if year and year in name and period and period in name:
            return f

    return None


def _clear_selection(iframe: Frame) -> None:
    """Clear the unit selection to prepare for the next unit."""
    clear_btns = iframe.query_selector_all(".vscomp-clear-button")
    for btn in reversed(clear_btns):
        try:
            if btn.is_visible():
                btn.click()
        except Exception:
            pass
