# Azure AZ-104 Microsoft Learn Complete Book Builder

Build a complete Azure AZ-104 study package from official Microsoft Learn content and generate chapter-based exam practice books with source-grounded answers.

Repository slug: `az104-mslearn-complete-book-builder`

## Certification

`Microsoft Certified: Azure Administrator Associate`

Demonstrate key skills to configure, manage, secure, and administer key professional functions in Microsoft Azure.

## What This Project Does

- Discovers Azure AZ-104 learning paths, modules, and units from Microsoft Learn.
- Fetches and normalizes unit and related official-page content.
- Builds the main verbatim study book in `MD`, `TXT`, and `EPUB`.
- Generates three additional test books:
- `AZ-104_Chapter_Test_Book`
- `AZ-104_Scenario_Test_Book`
- `AZ-104_ExamStyle_Chapter_Test_Book` (non-scenario)
- Produces coverage JSON files for auditability and quality checks.

## Installation

```bash
cd az104-mslearn-complete-book-builder
python -m pip install -e .
```

Recommended extras:

```bash
python -m pip install -e .[epub,dev]
```

## Quick Start

Run the full fetch + build pipeline:

```bash
az104-tool \
  --input-url "https://learn.microsoft.com/en-us/training/courses/az-104t00" \
  --out-dir output \
  --title "Azure AZ-104 Microsoft Learn Complete Study Book"
```

Alternative entrypoint:

```bash
python run_az104_book.py --out-dir output
```

Generate test books from the latest output run:

```bash
python generate_az104_test_book.py
python generate_az104_scenario_test_book.py
python generate_az104_examstyle_chapter_test_book.py
```

## CLI Options

`az104-tool` supports:

- `--input-url` (default: official AZ-104 course URL)
- `--out-dir` (default: `output`)
- `--locale` (default: `en-us`)
- `--title` (default: `AZ-104 Microsoft Learn Verbatim`)
- `--discover-delay` (catalog request delay)
- `--fetch-delay` (unit/page fetch delay)
- `--fetch-retries` (retry count per page)
- `--fetch-backoff` (retry backoff multiplier)
- `--official-link-jumps` (default: `2`)
- `--official-max-connected-pages` (default: `150`)
- `--verbose` (debug logging)

## Output Structure

Each run creates `output/YYYYMMDD_HHMMSS/` with:

- `manifest.json`: discovered learning structure.
- `unit_content.jsonl`: fetched unit content records.
- `official_pages.jsonl`: fetched related official-page content records.
- `coverage_report.json`: fetch/coverage summary.
- `book/`: all generated books and coverage files.

Main study book files:

- `AZ-104_Microsoft_Learn_Verbatim.md`
- `AZ-104_Microsoft_Learn_Verbatim.txt`
- `AZ-104_Microsoft_Learn_Verbatim.epub`

## Book Types

`AZ-104_Chapter_Test_Book`:

- Chapter-based MCQ practice.
- Variable question volume per chapter (`max(15, facts_available)` behavior in generation logic).

`AZ-104_Scenario_Test_Book`:

- Case-study style grouped questions.
- Chapter-grounded scenario context and linked Q/A blocks.

`AZ-104_ExamStyle_Chapter_Test_Book`:

- Non-scenario exam-style questions.
- Mixed item types:
- `Single best answer`
- `Choose TWO`
- `Sequence`
- `True/False combination`
- Constraint/tradeoff wording for more exam-like pressure.

## Quality and Grounding Guarantees

- Questions are generated from extracted chapter facts.
- Answers are selected from chapter-grounded statements.
- Explanations are tied back to source lines.
- Noise filtering removes common website UI text artifacts.
- EPUB normalization enforces deterministic outputs across repeated runs.

## Testing

Run all tests:

```bash
python -m pytest -q
```

Current test coverage includes:

- fetcher encoding and noise filtering behavior
- official-page discovery behavior
- exam-style fallback correctness behavior
- EPUB normalization idempotence
- catalog utility behavior

## Documentation Map

- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Operations and runbook: [docs/OPERATIONS.md](docs/OPERATIONS.md)

## Notes

- Source content is fetched from official Microsoft Learn Azure AZ-104 related pages at run time.
- This project supports study preparation and does not guarantee exam outcomes.
- Review Microsoft Learn terms before redistribution of generated content.
