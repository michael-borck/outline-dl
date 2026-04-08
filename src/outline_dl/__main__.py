"""Entry point for outline-dl."""

from __future__ import annotations

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

from outline_dl.auth import login
from outline_dl.cli import build_parser
from outline_dl.config import resolve_credentials, resolve_unit_codes
from outline_dl.downloader import download_outlines


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    username, password = resolve_credentials(args.username, args.password)
    unit_codes = resolve_unit_codes(args.units or None, args.file)

    print(f"Will download outlines for: {', '.join(unit_codes)}")
    print(f"Output directory: {args.output_dir}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not args.visible)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        login(page, username, password, timeout=args.timeout)
        results = download_outlines(
            page, unit_codes, args.output_dir,
            campus=args.campus, timeout=args.timeout,
        )

        browser.close()

    # Summary
    print("\n=== Summary ===")
    ok = [c for c, s in results.items() if s == "ok"]
    failed = [(c, s) for c, s in results.items() if s != "ok"]

    if ok:
        print(f"  Downloaded: {', '.join(ok)}")
    if failed:
        print("  Failed:")
        for code, err in failed:
            print(f"    {code}: {err}")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
