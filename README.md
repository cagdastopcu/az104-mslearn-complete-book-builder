# Azure AZ-104 Microsoft Learn Complete Book Builder

Build a full Azure AZ-104 study package directly from official Microsoft Learn content, then generate multiple exam-practice books with source-grounded answers and explanations.

## Why This Project Exists

Most Azure AZ-104 prep material has one of these problems: outdated content, weak traceability, or shallow question quality. This project addresses that by:

- Pulling current official Microsoft Learn Azure AZ-104 learning content.
- Building a verbatim reference book for direct study.
- Generating high-volume chapter tests and exam-style question sets.
- Keeping answers and explanations tied to extracted source statements.

## Certification Target

`Microsoft Certified: Azure Administrator Associate`

Demonstrate key skills to configure, manage, secure, and administer key professional functions in Microsoft Azure.

## What You Get

After running the pipeline and generators, you get:

- `AZ-104_Microsoft_Learn_Verbatim` in `MD`, `TXT`, `EPUB`
- `AZ-104_Chapter_Test_Book` in `MD`, `TXT`, `EPUB` + coverage JSON
- `AZ-104_Scenario_Test_Book` in `MD`, `TXT`, `EPUB` + coverage JSON
- `AZ-104_ExamStyle_Chapter_Test_Book` (non-scenario) in `MD`, `TXT`, `EPUB` + coverage JSON

## One-Command Build (Main Book)

```bash
az104-tool \
  --input-url "https://learn.microsoft.com/en-us/training/courses/az-104t00" \
  --out-dir output \
  --title "Azure AZ-104 Microsoft Learn Complete Study Book"
```

Alternative:

```bash
python run_az104_book.py --out-dir output
```

## Generate Test Books

```bash
python generate_az104_test_book.py
python generate_az104_scenario_test_book.py
python generate_az104_examstyle_chapter_test_book.py
```

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

## Grounding And Integrity Rules

- Questions are generated from extracted chapter facts.
- Correct answers are selected from that same chapter-grounded fact set.
- Explanations cite supporting source lines from the verbatim content.
- Coverage JSON files provide extraction and generation counts for auditability.

## Install

```bash
cd az104-mslearn-complete-book-builder
python -m pip install -e .
```

Recommended:

```bash
python -m pip install -e .[epub,dev]
```

## Test

```bash
python -m pytest -q
```

## Notes

- Source content is official Microsoft Learn Azure AZ-104 related material fetched at run time.
- This project is designed for study acceleration, not as a guarantee of exam pass.
- Review Microsoft Learn terms before redistribution.
