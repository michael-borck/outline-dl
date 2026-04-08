"""CLI argument parsing."""

import argparse
from importlib.metadata import version
from pathlib import Path

REPO_URL = "https://github.com/michael-borck/outline-dl"


def build_parser() -> argparse.ArgumentParser:
    ver = version("outline-dl")
    parser = argparse.ArgumentParser(
        prog="outline-dl",
        description="Download unit outline PDFs from Curtin LITEC",
        epilog=f"Project: {REPO_URL}",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {ver} — {REPO_URL}",
    )
    parser.add_argument(
        "units",
        nargs="*",
        help="Unit codes to download (e.g. COMP1000 ISAD1000)",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        help="File containing unit codes (one per line or comma-separated)",
    )
    parser.add_argument("-u", "--username", help="Curtin username")
    parser.add_argument("-p", "--password", help="Curtin password")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("outlines"),
        help="Output directory for PDFs (default: ./outlines/)",
    )
    parser.add_argument(
        "-c",
        "--campus",
        default="Bentley Perth Campus",
        help=(
            "Campus to filter availabilities by (default: 'Bentley Perth Campus'). "
            "Use 'all' to download for all campuses."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download even if the PDF already exists in the output directory",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Show the browser window (default: headless)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30000,
        help="Navigation timeout in milliseconds (default: 30000)",
    )
    return parser
