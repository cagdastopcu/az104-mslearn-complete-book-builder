# Architecture

## Overview

The project has two major flows:

- Main pipeline: discover -> fetch -> normalize -> build main book.
- Test-book generation: parse main book -> extract facts -> generate question books.

## Module Responsibilities

`src/az104_refactored_tool/cli.py`:

- CLI argument parsing.
- Pipeline orchestration.
- Output run-folder creation (`output/YYYYMMDD_HHMMSS`).

`src/az104_refactored_tool/catalog.py`:

- Microsoft Learn catalog discovery for course, learning paths, modules, and units.
- Manifest model creation.

`src/az104_refactored_tool/fetcher.py`:

- HTTP fetch with retries and backoff.
- HTML parsing and content extraction.
- Text normalization:
- mojibake repair
- UI noise removal
- duplicate-line reduction

`src/az104_refactored_tool/official_pages.py`:

- Discovery of additional official AZ-104 related pages.
- Link-jump crawling with relevance filtering.

`src/az104_refactored_tool/book.py`:

- Main `MD` and `TXT` rendering.
- EPUB creation for the main study book.
- EPUB normalization for deterministic archives.

`src/az104_refactored_tool/io_utils.py`:

- JSON/JSONL and manifest read-write helpers.

`src/az104_refactored_tool/models.py`:

- Typed models for manifest and content structures.

`generate_az104_test_book.py`:

- Chapter-based MCQ generator from main verbatim book.

`generate_az104_scenario_test_book.py`:

- Scenario/case-study style question generator.

`generate_az104_examstyle_chapter_test_book.py`:

- Non-scenario exam-style mixed-item question generator.

## Data Flow

1. `cli.run_pipeline` creates a timestamped run folder.
2. `catalog.discover_manifest` produces structured learning metadata.
3. `fetcher.fetch_from_manifest` fetches unit pages and normalizes content.
4. `official_pages.collect_official_pages` resolves related official pages.
5. `fetcher.fetch_pages` fetches official pages and normalizes content.
6. `book.build_all_formats` renders main books (`.md`, `.txt`, `.epub`).
7. Generator scripts parse the main `.md` and create test-book variants.

## Determinism Model

Determinism is intentionally enforced for generated outputs:

- Question generation uses deterministic seeding per chapter.
- EPUB files are normalized:
- fixed ZIP metadata timestamps
- normalized `EPUB/content.opf` `dcterms:modified`

This prevents meaningless binary churn between identical runs.

## Quality Guards

- Encoding-repair logic protects against common UTF-8/Latin-1 corruption.
- Noise-pattern filtering removes non-study UI content from extracted text.
- Coverage JSONs record question/fact generation counts.
- Tests enforce critical invariants.
