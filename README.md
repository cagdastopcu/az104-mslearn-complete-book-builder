# AZ-104 Microsoft Learn Complete Book Builder

This project is a command-line tool that collects official AZ-104 Microsoft Learn content and builds a complete study book in multiple formats.

Repository name: `az104-mslearn-complete-book-builder`

## What It Does

- Pulls the latest AZ-104 course structure from Microsoft Learn.
- Fetches all unit pages in official order.
- Fetches related official AZ-104 pages (course, learning paths, certification page, study guide, and linked documentation pages from the study guide).
- Generates a single book in `TXT`, `Markdown`, and `EPUB` formats.
- Writes a coverage report so you can verify completeness.

## Install

```bash
cd az104-mslearn-complete-book-builder
python -m pip install -e .
```

Optional dependencies for EPUB and tests:

```bash
python -m pip install -e .[epub,dev]
```

## Usage

Run everything in one command:

```bash
az104-tool \
  --input-url "https://learn.microsoft.com/en-us/training/courses/az-104t00" \
  --out-dir output \
  --title "AZ-104 Microsoft Learn Complete Study Book"
```

Or run the wrapper script:

```bash
python run_az104_book.py --out-dir output
```

Each run creates a timestamped folder under `output/` with:

- `manifest.json`
- `unit_content.jsonl`
- `official_pages.jsonl`
- `coverage_report.json`
- `fetch_errors.log` (only if there are failures)
- `book/*.txt`
- `book/*.md`
- `book/*.epub` (if `ebooklib` is installed)

## Notes

- The tool is designed for full AZ-104 coverage from official Microsoft Learn sources.
- Always review Microsoft Learn terms of use before redistributing content.

## Run Tests

```bash
python -m pytest -q
```
