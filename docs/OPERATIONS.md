# Operations Runbook

## Environment

- Python `>=3.10`
- Recommended install:
- `python -m pip install -e .[epub,dev]`

## Standard Workflow

1. Build or refresh the main AZ-104 verbatim book:

```bash
az104-tool \
  --input-url "https://learn.microsoft.com/en-us/training/courses/az-104t00" \
  --out-dir output \
  --official-link-jumps 2 \
  --official-max-connected-pages 150
```

2. Generate all test books from the latest output folder:

```bash
python generate_az104_test_book.py
python generate_az104_scenario_test_book.py
python generate_az104_examstyle_chapter_test_book.py
```

3. Validate code and output generation:

```bash
python -m pytest -q
python -m compileall -q src tests run_az104_book.py generate_az104_test_book.py generate_az104_scenario_test_book.py generate_az104_examstyle_chapter_test_book.py
```

## Output Artifacts

Inside each run folder (`output/YYYYMMDD_HHMMSS`):

- `manifest.json`
- `unit_content.jsonl`
- `official_pages.jsonl`
- `coverage_report.json`
- `book/`

Inside `book/`:

- `AZ-104_Microsoft_Learn_Verbatim.{md,txt,epub}`
- `AZ-104_Chapter_Test_Book.{md,txt,epub}`
- `AZ-104_Scenario_Test_Book.{md,txt,epub}`
- `AZ-104_ExamStyle_Chapter_Test_Book.{md,txt,epub}`
- `*_Coverage.json` files for generated test books

## Troubleshooting

EPUB missing:

- Install optional dependency:
- `python -m pip install -e .[epub]`

Too few official related pages:

- Increase:
- `--official-link-jumps`
- `--official-max-connected-pages`

Network or throttling failures:

- Increase:
- `--fetch-retries`
- `--fetch-backoff`
- `--fetch-delay`

Unexpected website UI text in output:

- Update noise patterns in:
- `src/az104_refactored_tool/fetcher.py`
- Regenerate outputs.

## Quality Verification Checklist

- `pytest` is green.
- No `FETCH ERROR` lines in generated book files.
- Coverage JSON totals match parsed question totals.
- Repeated generation keeps EPUB hashes stable.

## Safe Release Checklist

1. Run full tests and compile checks.
2. Regenerate outputs intended for commit.
3. Confirm `git status` contains only expected changes.
4. Commit with a scoped message.
5. Push `main` and verify remote state.
