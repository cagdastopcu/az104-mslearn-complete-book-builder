from __future__ import annotations

import html
import random
import re
import json
import tempfile
import zipfile
from hashlib import sha1
from pathlib import Path
from typing import NamedTuple


GENERIC_HEADINGS = {
    "introduction",
    "summary",
    "summary and resources",
    "learn more",
    "module assessment",
    "check your knowledge",
    "prerequisites",
    "learning objectives",
}

NOISE_PATTERNS = [
    r"^skip to ",
    r"^read in english$",
    r"^feedback$",
    r"^back to top$",
    r"^ask learn$",
    r"^this page contains limited or dynamic content",
]

AZ_KEYWORDS = [
    "azure",
    "entra",
    "rbac",
    "subscription",
    "resource",
    "policy",
    "storage",
    "blob",
    "vm",
    "virtual machine",
    "network",
    "dns",
    "load balancer",
    "application gateway",
    "container",
    "app service",
    "monitor",
    "backup",
    "site recovery",
    "bicep",
    "arm template",
]

STEM_TEMPLATES = [
    "In the chapter area '{subtitle}', which statement appears in the section '{section}'?",
    "You are reviewing '{subtitle}'. Which option is explicitly stated under '{section}'?",
    "For AZ-104 study in '{subtitle}', which statement belongs to the section '{section}'?",
    "Which statement is listed in the section '{section}' for the chapter topic '{subtitle}'?",
    "Based on the section '{section}' in '{subtitle}', which statement is correct?",
]


class Fact(NamedTuple):
    text: str
    section: str


def _normalize_epub_archive(epub_path: Path) -> None:
    timestamp = (2000, 1, 1, 0, 0, 0)
    fixed_modified = "2000-01-01T00:00:00Z"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".epub", dir=str(epub_path.parent)) as tmp:
        temp_path = Path(tmp.name)

    try:
        with zipfile.ZipFile(epub_path, "r") as source, zipfile.ZipFile(temp_path, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename.lower().endswith("content.opf"):
                    opf = data.decode("utf-8", errors="replace")
                    opf = re.sub(
                        r"(<meta\s+property=\"dcterms:modified\">)([^<]+)(</meta>)",
                        rf"\g<1>{fixed_modified}\g<3>",
                        opf,
                        flags=re.IGNORECASE,
                    )
                    data = opf.encode("utf-8")
                normalized = zipfile.ZipInfo(filename=info.filename, date_time=timestamp)
                normalized.compress_type = info.compress_type
                normalized.external_attr = info.external_attr
                normalized.comment = info.comment
                normalized.create_system = 0
                normalized.extra = b""
                target.writestr(normalized, data, compress_type=info.compress_type)
        temp_path.replace(epub_path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _safe_filename(text: str) -> str:
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"[^A-Za-z0-9_.-]", "", text)
    return text or "book"


def _latest_output_dir(project_root: Path) -> Path:
    output_root = project_root / "output"
    runs = [p for p in output_root.iterdir() if p.is_dir()]
    if not runs:
        raise FileNotFoundError("No output run folders were found.")
    return sorted(runs, key=lambda p: p.name)[-1]


def _clean_line(line: str) -> str:
    line = re.sub(r"\s+", " ", line).strip()
    line = re.sub(r"^[#>\-\*\d\.\)\s]+", "", line).strip()
    return line


def _is_noise(text: str) -> bool:
    lowered = text.lower().strip()
    if not lowered:
        return True
    for pat in NOISE_PATTERNS:
        if re.match(pat, lowered):
            return True
    return False


def _looks_relevant(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in AZ_KEYWORDS)


def _has_action_or_definition(text: str) -> bool:
    lowered = text.lower()
    verbs = [
        " is ",
        " are ",
        " can ",
        " should ",
        " must ",
        " use ",
        " using ",
        " configure ",
        " create ",
        " manage ",
        " deploy ",
        " implement ",
        " monitor ",
        " backup ",
        " restore ",
        " supports ",
        " provides ",
        " allows ",
    ]
    padded = f" {lowered} "
    return any(v in padded for v in verbs)


def _is_metadata(text: str) -> bool:
    lowered = text.lower()
    if "http://" in lowered or "https://" in lowered:
        return True
    if "wt.mc_id" in lowered:
        return True
    if re.search(r"\b(unit|module|learning path)\s+url\b", lowered):
        return True
    if lowered.startswith("uid:") or lowered.startswith("source url:"):
        return True
    return False


def _is_generic_text(text: str) -> bool:
    lowered = text.lower()
    generic_starts = (
        "this module",
        "in this module",
        "introduction",
        "summary",
        "learn more",
        "check your knowledge",
    )
    if lowered.startswith(generic_starts):
        return True
    return False


def _split_chapters(book_text: str) -> list[tuple[str, list[str]]]:
    lines = book_text.splitlines()
    module_indices: list[int] = []
    official_index: int | None = None

    for i, line in enumerate(lines):
        if re.match(r"^### Module \d+\.\d+:", line):
            module_indices.append(i)
        if line.strip() == "## AZ-104 Official Pages":
            official_index = i

    if not module_indices:
        raise ValueError("No module chapter headings were found.")

    boundaries = module_indices[:]
    if official_index is not None:
        boundaries.append(official_index)
    boundaries.append(len(lines))

    chapters: list[tuple[str, list[str]]] = []

    # Module chapters.
    for idx, start in enumerate(module_indices):
        next_starts = [b for b in boundaries if b > start]
        end = min(next_starts) if next_starts else len(lines)
        title = lines[start].lstrip("# ").strip()
        chapters.append((title, lines[start:end]))

    # Official pages chapter as the final chapter, if present.
    if official_index is not None:
        end = len(lines)
        chapters.append(("AZ-104 Official Pages", lines[official_index:end]))

    return chapters


def _chapter_subtitle(chapter_lines: list[str], fallback_title: str) -> str:
    picks: list[str] = []
    for raw in chapter_lines:
        if not raw.startswith("## "):
            continue
        txt = _clean_line(raw)
        low = txt.lower()
        if low in GENERIC_HEADINGS:
            continue
        if len(txt) < 6:
            continue
        picks.append(txt)
        if len(picks) == 3:
            break
    if picks:
        return " / ".join(picks)
    return fallback_title


def _extract_facts(chapter_lines: list[str]) -> list[Fact]:
    facts: list[Fact] = []
    seen: set[str] = set()
    current_section = "General"

    def add_fact(text: str, section: str) -> None:
        text = _clean_line(text)
        if _is_noise(text):
            return
        if _is_metadata(text):
            return
        if _is_generic_text(text):
            return
        if text.endswith("?"):
            return
        if text.endswith(":"):
            return
        if len(text) < 25 or len(text) > 220:
            return
        if not _looks_relevant(text):
            return
        if not _has_action_or_definition(text):
            return
        key = text.lower()
        if key in seen:
            return
        seen.add(key)
        facts.append(Fact(text=text, section=section))

    for line in chapter_lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = _clean_line(stripped)
            continue
        if stripped.startswith("### ") and not re.match(r"^### Module \d+\.\d+:", stripped):
            current_section = _clean_line(stripped)
            continue
        if stripped.startswith("## ") or stripped.startswith("### "):
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            add_fact(stripped, current_section)
            continue
        if len(stripped) > 45 and not stripped.startswith("```"):
            sentences = re.split(r"(?<=[\.\!\?])\s+", stripped)
            for sent in sentences:
                add_fact(sent, current_section)

    if len(facts) >= 4:
        return facts

    # Relaxed fallback to avoid dropping short/sparse chapters.
    relaxed: list[Fact] = []
    seen_relaxed: set[str] = set()
    current_section = "General"
    for line in chapter_lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            current_section = _clean_line(stripped)
            continue
        if stripped.startswith("### ") and not re.match(r"^### Module \d+\.\d+:", stripped):
            current_section = _clean_line(stripped)
            continue
        text = _clean_line(stripped)
        if not text:
            continue
        if _is_noise(text) or _is_metadata(text):
            continue
        if len(text) < 25 or len(text) > 220:
            continue
        key = text.lower()
        if key in seen_relaxed:
            continue
        seen_relaxed.add(key)
        relaxed.append(Fact(text=text, section=current_section))

    return relaxed


def _format_question_block(
    qn: int,
    subtitle: str,
    section: str,
    correct: Fact,
    distractors: list[Fact],
    rng: random.Random,
) -> str:
    stem = STEM_TEMPLATES[qn % len(STEM_TEMPLATES)].format(subtitle=subtitle, section=section)
    options = [correct.text, *(d.text for d in distractors)]
    rng.shuffle(options)
    answer_index = options.index(correct.text)
    labels = ["A", "B", "C", "D"]
    answer_label = labels[answer_index]

    out: list[str] = []
    out.append(f"### Question {qn}")
    out.append(stem)
    out.append("")
    for i, opt in enumerate(options):
        out.append(f"- {labels[i]}. {opt}")
    out.append("")
    out.append(f"**Correct answer: {answer_label}**")
    out.append(
        f"**Explanation:** The correct option matches a source statement under section label '{section}' in this chapter."
    )
    out.append(f"> {correct.text}")
    out.append("")
    return "\n".join(out)


def _markdown_to_plain_text(md_text: str) -> str:
    lines: list[str] = []
    for raw in md_text.splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^\-\s+", "", line)
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        lines.append(line)
    return "\n".join(lines).strip() + "\n"


def _markdown_to_simple_html(md_text: str) -> str:
    out: list[str] = []
    in_ul = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for raw in md_text.splitlines():
        line = raw.strip()
        if not line:
            close_ul()
            continue

        if line.startswith("### "):
            close_ul()
            out.append(f"<h3>{html.escape(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            close_ul()
            out.append(f"<h2>{html.escape(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            close_ul()
            out.append(f"<h1>{html.escape(line[2:])}</h1>")
            continue
        if line.startswith("- "):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{html.escape(line[2:])}</li>")
            continue

        close_ul()
        line = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html.escape(line))
        out.append(f"<p>{line}</p>")

    close_ul()
    return "\n".join(out)


def _write_test_book_formats(md_path: Path) -> dict[str, Path]:
    md_text = md_path.read_text(encoding="utf-8")
    txt_path = md_path.with_suffix(".txt")
    epub_path = md_path.with_suffix(".epub")

    txt_path.write_text(_markdown_to_plain_text(md_text), encoding="utf-8")

    written: dict[str, Path] = {"md": md_path, "txt": txt_path}
    try:
        from ebooklib import epub

        book = epub.EpubBook()
        base_name = _safe_filename(md_path.stem).lower()
        book.set_identifier(base_name)
        book.set_title(md_path.stem.replace("_", " "))
        book.set_language("en")
        book.add_author("AZ-104 Test Book Generator")

        style = epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content=(
                "body{font-family:Georgia,serif;line-height:1.6;margin:1em 1.4em;}"
                "h1{color:#0078D4;}h2{color:#005a9e;}h3{color:#333;}p{margin:.45em 0;}"
                "li{margin:.2em 0;}strong{font-weight:700;}"
            ),
        )
        book.add_item(style)

        chapter = epub.EpubHtml(title=md_path.stem, file_name="ch001.xhtml", lang="en")
        chapter.content = _markdown_to_simple_html(md_text)
        chapter.add_item(style)
        book.add_item(chapter)

        book.toc = (chapter,)
        book.spine = ["nav", chapter]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        epub.write_epub(str(epub_path), book)
        _normalize_epub_archive(epub_path)
        written["epub"] = epub_path
    except Exception:
        # Keep md/txt even if EPUB package is not available in current environment.
        pass

    return written


def build_test_book(source_md: Path, output_md: Path) -> None:
    text = source_md.read_text(encoding="utf-8")
    chapters = _split_chapters(text)

    lines: list[str] = []
    lines.append("# AZ-104 Chapter Test Book")
    lines.append("")
    lines.append(
        "This test book is generated only from the latest AZ-104 source book content. "
        "Each chapter contains at least 15 multiple-choice questions with answer keys and explanations. "
        "If a chapter has more extracted facts, additional questions are generated so every fact is covered."
    )
    lines.append("")
    coverage_rows: list[dict[str, object]] = []

    for chapter_idx, (title, chapter_lines) in enumerate(chapters, start=1):
        subtitle = _chapter_subtitle(chapter_lines, title)
        facts = _extract_facts(chapter_lines)
        if len(facts) < 4:
            continue

        # Deterministic shuffle per chapter for stable output across runs.
        seed = int(sha1(f"{chapter_idx}:{title}".encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        rng.shuffle(facts)

        lines.append(f"## Chapter {chapter_idx}: {title}")
        lines.append("")
        lines.append(f"**Subtitle:** {subtitle}")
        lines.append("")

        question_count = max(15, len(facts))
        for qn in range(1, question_count + 1):
            correct_idx = (qn - 1) % len(facts)
            correct = facts[correct_idx]

            # Prefer distractors from other sections so only one option fits the section context.
            pool = [f for i, f in enumerate(facts) if i != correct_idx and f.section != correct.section]
            if len(pool) < 3:
                pool = [f for i, f in enumerate(facts) if i != correct_idx]
            if len(pool) < 3:
                # In extremely short chapters, re-use nearby lines.
                pool = facts[:]
            distractors = rng.sample(pool, k=3) if len(pool) >= 3 else (pool + facts)[:3]

            block = _format_question_block(
                qn=qn,
                subtitle=subtitle,
                section=correct.section,
                correct=correct,
                distractors=distractors,
                rng=rng,
            )
            lines.append(block)

        coverage_rows.append(
            {
                "chapter_index": chapter_idx,
                "chapter_title": title,
                "facts_extracted": len(facts),
                "questions_generated": question_count,
                "all_facts_covered": question_count >= len(facts),
            }
        )

    output_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    coverage_path = output_md.with_name("AZ-104_Chapter_Test_Book_Coverage.json")
    coverage_summary = {
        "chapters_written": len(coverage_rows),
        "total_facts_extracted": sum(int(r["facts_extracted"]) for r in coverage_rows),
        "total_questions_generated": sum(int(r["questions_generated"]) for r in coverage_rows),
        "all_chapters_cover_all_facts": all(bool(r["all_facts_covered"]) for r in coverage_rows),
        "chapters": coverage_rows,
    }
    coverage_path.write_text(json.dumps(coverage_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_test_book_formats(output_md)


def main() -> None:
    project_root = Path(__file__).resolve().parent
    run_dir = _latest_output_dir(project_root)
    source_md = run_dir / "book" / "AZ-104_Microsoft_Learn_Verbatim.md"
    if not source_md.exists():
        raise FileNotFoundError(f"Source book not found: {source_md}")

    output_md = run_dir / "book" / "AZ-104_Chapter_Test_Book.md"
    build_test_book(source_md=source_md, output_md=output_md)
    print(f"Created: {output_md}")


if __name__ == "__main__":
    main()
