# Azure AZ-104 Microsoft Learn Complete Book Builder

This project builds Azure AZ-104 study content from official Microsoft Learn sources, then generates multiple book variants (verbatim, chapter tests, scenario tests, and exam-style tests) in `MD`, `TXT`, and `EPUB`.

Repository name: `az104-mslearn-complete-book-builder`

## What This Project Produces

After a run, a timestamped folder is created under `output/`, for example:

`output/20260504_225156/`

That folder contains:

- `manifest.json`: discovered Azure AZ-104 learning paths, modules, and units.
- `unit_content.jsonl`: fetched unit text content.
- `official_pages.jsonl`: fetched Azure AZ-104 official related pages.
- `coverage_report.json`: source coverage summary.
- `book/`: all generated books and test books.

## Install

```bash
cd az104-mslearn-complete-book-builder
python -m pip install -e .
```

Recommended extras:

```bash
python -m pip install -e .[epub,dev]
```

## Certification

Microsoft Certified: Azure Administrator Associate

Demonstrate key skills to configure, manage, secure, and administer key professional functions in Microsoft Azure.

## Build The Main Verbatim Book

Run the full fetch/build pipeline:

```bash
az104-tool \
  --input-url "https://learn.microsoft.com/en-us/training/courses/az-104t00" \
  --out-dir output \
  --title "AZ-104 Microsoft Learn Complete Study Book"
```

Or:

```bash
python run_az104_book.py --out-dir output
```

Main book files:

- `AZ-104_Microsoft_Learn_Verbatim.md`
- `AZ-104_Microsoft_Learn_Verbatim.txt`
- `AZ-104_Microsoft_Learn_Verbatim.epub`

## Test Book Generators

These scripts read the latest output book and generate additional test books:

- `python generate_az104_test_book.py`
- `python generate_az104_scenario_test_book.py`
- `python generate_az104_examstyle_chapter_test_book.py`

## Book Types, Question Counts, And Styles

### 1) Chapter Test Book

Files:

- `AZ-104_Chapter_Test_Book.md`
- `AZ-104_Chapter_Test_Book.txt`
- `AZ-104_Chapter_Test_Book.epub`
- `AZ-104_Chapter_Test_Book_Coverage.json`

Purpose:

- Broad chapter-by-chapter recall checks from the source text.
- Best for high-volume coverage and memory reinforcement after you read the verbatim book.
- Every question is grounded to extracted chapter statements and includes source-line explanation.

Question count behavior:

- Variable count per chapter.
- At least 15 questions per chapter.
- If a chapter has more extracted facts, it generates more so coverage is not capped.

Exact counts for the included snapshot `output/20260504_225156/`:

- Chapters: `29`
- Total questions: `2946`
- Question style: section-grounded chapter MCQ format (single-answer recall style)

### 2) Scenario Test Book

Files:

- `AZ-104_Scenario_Test_Book.md`
- `AZ-104_Scenario_Test_Book.txt`
- `AZ-104_Scenario_Test_Book.epub`
- `AZ-104_Scenario_Test_Book_Coverage.json`

Purpose:

- Scenario/case-style practice based on source content.
- Best for practicing grouped case flow and linked questions under shared context.
- Uses case studies with multiple linked questions and source-grounded explanations.

Question count behavior:

- Variable by chapter/fact extraction.
- Includes case-study style grouping and linked questions.

Exact counts for the included snapshot `output/20260504_225156/`:

- Chapters: `29`
- Total case studies: `604`
- Total questions: `2946`
- Question style: case-study linked questions (`Case Study N` + `Q1..Qn`)

### 3) Exam-Style Chapter Test Book (Non-Scenario)

Files:

- `AZ-104_ExamStyle_Chapter_Test_Book.md`
- `AZ-104_ExamStyle_Chapter_Test_Book.txt`
- `AZ-104_ExamStyle_Chapter_Test_Book.epub`
- `AZ-104_ExamStyle_Chapter_Test_Book_Coverage.json`

Purpose:

- Chapter-based exam-style practice without scenario blocks.
- Best for mixed exam-style item practice without case-study scenario framing.
- Uses operational tradeoff constraints and mixed item types while staying chapter-grounded.

Question count behavior:

- Variable count per chapter.
- Uses `max(15, facts_available)` per chapter.

Item styles in this book:

- `Single best answer`
- `Choose TWO`
- `Sequence`
- `True/False combination`

Style distribution is automatic and mixed throughout each chapter.

Exact counts for the included snapshot `output/20260504_225156/`:

- Chapters: `29`
- Total questions: `4360`
- `Single best answer`: `1100`
- `Choose TWO`: `1092`
- `Sequence`: `1088`
- `True/False combination`: `1080`

## Source Grounding Rules For Answers And Explanations

All generated test books are built to keep answer/explanation grounding in source content:

- Correct answers are mapped to extracted statements from the matching chapter.
- Explanations include quoted source lines (`> ...`) from the chapter content.
- Coverage files summarize chapter-level extraction and question totals.

## Current Output Snapshot Included In Repository

This repository includes a full output snapshot at:

`output/20260504_225156/`

including all generated books and coverage files with original folder structure.

## Notes

- Content source is official Microsoft Learn Azure AZ-104 related material fetched at generation time.
- Always review Microsoft Learn terms before redistribution.

## Run Tests

```bash
python -m pytest -q
```
