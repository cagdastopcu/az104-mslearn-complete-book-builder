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

## Exact Metrics (Current Included Snapshot)

Reference snapshot: `output/20260504_225156/`

Chapter count in source book:

- `29` chapters

Question totals:

- `AZ-104_Chapter_Test_Book`: `2946` questions
- `AZ-104_Scenario_Test_Book`: `2946` questions across `604` case studies
- `AZ-104_ExamStyle_Chapter_Test_Book` (non-scenario): `4360` questions

Exam-style type distribution (`AZ-104_ExamStyle_Chapter_Test_Book`):

- `Single best answer`: `1100`
- `Choose TWO`: `1092`
- `Sequence`: `1088`
- `True/False combination`: `1080`

## Exam-Style Quality Model

The non-scenario exam-style book is intentionally built to feel closer to real Azure AZ-104 thinking pressure:

- Best-answer-under-constraints wording (not only pure fact recall).
- Mixed item styles in each chapter.
- Operational tradeoff emphasis (cost, manageability, risk, speed, and governance choices).
- Variable question volume per chapter using `max(15, facts_available)`.

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
