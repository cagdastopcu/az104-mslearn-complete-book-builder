from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

from .logging_utils import configure_logging

LOGGER = logging.getLogger(__name__)

DEFAULT_AZ104_URL = "https://learn.microsoft.com/en-us/training/courses/az-104t00"


def _timestamp_folder() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def run_pipeline(
    input_url: str,
    out_dir: Path,
    locale: str,
    title: str,
    discover_delay: float,
    fetch_delay: float,
    fetch_retries: int,
    fetch_backoff: float,
    official_link_jumps: int,
    official_max_connected_pages: int,
) -> dict[str, Path]:
    from .book import build_all_formats
    from .catalog import discover_manifest
    from .fetcher import fetch_from_manifest, fetch_pages
    from .io_utils import load_jsonl, save_json, save_jsonl, save_manifest
    from .official_pages import collect_official_pages

    run_dir = out_dir / _timestamp_folder()
    run_dir.mkdir(parents=True, exist_ok=True)

    manifest = discover_manifest(input_url=input_url, locale=locale, delay_sec=discover_delay)
    manifest_path = run_dir / "manifest.json"
    save_manifest(manifest_path, manifest)
    LOGGER.info("Manifest written: %s", manifest_path)

    content_rows, errors = fetch_from_manifest(
        manifest=manifest.to_dict(),
        delay_sec=fetch_delay,
        retries=fetch_retries,
        backoff_sec=fetch_backoff,
    )
    content_path = run_dir / "unit_content.jsonl"
    save_jsonl(content_path, content_rows)
    LOGGER.info("Unit content written: %s", content_path)

    official_urls = collect_official_pages(
        manifest.to_dict(),
        input_url,
        link_jumps=official_link_jumps,
        max_connected_pages=official_max_connected_pages,
    )
    official_rows, official_errors = fetch_pages(
        urls=official_urls,
        delay_sec=fetch_delay,
        retries=fetch_retries,
        backoff_sec=fetch_backoff,
    )
    official_path = run_dir / "official_pages.jsonl"
    with official_path.open("w", encoding="utf-8") as handle:
        for row in official_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    LOGGER.info("Official pages written: %s", official_path)

    if errors:
        error_path = run_dir / "fetch_errors.log"
        error_path.write_text("\n".join(errors), encoding="utf-8")
        LOGGER.warning("Fetch errors logged: %s", error_path)

    if official_errors:
        official_error_path = run_dir / "official_pages_errors.log"
        official_error_path.write_text("\n".join(official_errors), encoding="utf-8")
        LOGGER.warning("Official page fetch errors logged: %s", official_error_path)

    coverage = {
        "source_url": input_url,
        "course_title": manifest.course_title,
        "expected_units": sum(len(m.units) for lp in manifest.learning_paths for m in lp.modules),
        "fetched_unit_rows": len(content_rows),
        "successful_unit_rows": sum(1 for r in content_rows if r.success),
        "official_pages_expected": len(official_urls),
        "official_pages_fetched": len(official_rows),
        "official_pages_successful": sum(1 for r in official_rows if r.get("success")),
        "official_link_jumps": official_link_jumps,
        "official_max_connected_pages": official_max_connected_pages,
    }
    coverage_path = run_dir / "coverage_report.json"
    save_json(coverage_path, coverage)
    LOGGER.info("Coverage report written: %s", coverage_path)

    book_dir = run_dir / "book"
    outputs = build_all_formats(
        manifest=manifest.to_dict(),
        content_rows=load_jsonl(content_path),
        official_pages=official_rows,
        out_dir=book_dir,
        title=title,
    )
    LOGGER.info("Book output directory: %s", book_dir)
    outputs["manifest"] = manifest_path
    outputs["content"] = content_path
    outputs["official_pages"] = official_path
    outputs["coverage_report"] = coverage_path
    return outputs


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="az104-tool",
        description="Single-run AZ-104 Microsoft Learn book generator.",
    )
    parser.add_argument("--input-url", default=DEFAULT_AZ104_URL, help="Microsoft Learn source URL.")
    parser.add_argument("--out-dir", default="output", help="Base output directory.")
    parser.add_argument("--locale", default="en-us", help="Catalog API locale.")
    parser.add_argument("--title", default="AZ-104 Microsoft Learn Verbatim", help="Book title.")
    parser.add_argument("--discover-delay", type=float, default=0.35, help="Delay between catalog requests.")
    parser.add_argument("--fetch-delay", type=float, default=0.6, help="Delay between unit page requests.")
    parser.add_argument("--fetch-retries", type=int, default=3, help="Retries per unit fetch.")
    parser.add_argument("--fetch-backoff", type=float, default=1.0, help="Backoff multiplier for retries.")
    parser.add_argument(
        "--official-link-jumps",
        type=int,
        default=2,
        help="How many link hops to follow from official seed pages when discovering related AZ-104 pages.",
    )
    parser.add_argument(
        "--official-max-connected-pages",
        type=int,
        default=120,
        help="Maximum number of additional connected official pages to include.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logs.")
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    configure_logging(verbose=args.verbose)

    outputs = run_pipeline(
        input_url=args.input_url,
        out_dir=Path(args.out_dir),
        locale=args.locale,
        title=args.title,
        discover_delay=args.discover_delay,
        fetch_delay=args.fetch_delay,
        fetch_retries=args.fetch_retries,
        fetch_backoff=args.fetch_backoff,
        official_link_jumps=args.official_link_jumps,
        official_max_connected_pages=args.official_max_connected_pages,
    )

    LOGGER.info("Completed. Files created:")
    for key, path in outputs.items():
        LOGGER.info("%s: %s", key, path)


if __name__ == "__main__":
    main()
