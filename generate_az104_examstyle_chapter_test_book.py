from __future__ import annotations

import html
import json
import random
import re
from hashlib import sha1
from pathlib import Path
from typing import NamedTuple
from itertools import permutations


MIN_QUESTIONS_PER_CHAPTER = 15

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

STEM_VARIANTS = [
    "Which statement is correct based on the chapter guidance?",
    "Which option is the best answer?",
    "Which choice most accurately reflects the documented approach?",
    "Which statement should the administrator select?",
    "Which option aligns best with the guidance?",
]

ITEM_STYLES = ("single_best", "choose_two", "sequence", "true_false_combo")

TRADEOFF_CONSTRAINTS = [
    "Constraint: Minimize operational risk while keeping administration simple.",
    "Constraint: Preserve least privilege and avoid broad-impact changes.",
    "Constraint: Keep the solution supportable and aligned with documented guidance.",
    "Constraint: Favor predictable operations over ad-hoc shortcuts.",
    "Constraint: Balance speed of change with governance and recoverability.",
]

STOP_WORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "by",
    "is",
    "are",
    "be",
    "that",
    "this",
    "as",
    "at",
    "from",
    "you",
    "your",
    "it",
    "can",
}


class Fact(NamedTuple):
    text: str
    section: str


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


def _is_heading_like_fact(text: str) -> bool:
    # Drop short title-like fragments (common source of low-quality options).
    if text.endswith("."):
        return False
    words = re.findall(r"[A-Za-z0-9]+", text)
    if len(words) <= 8 and len(text) <= 70:
        return True
    return False


def _is_command_like_fact(text: str) -> bool:
    return bool(
        re.search(
            r"(?:^|\s)(az\s+|Get-|Set-|New-|templateFile=|--\w+|\$\w+|watch\s+-d|ssh\s+-t)",
            text,
        )
    )


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
    for start in module_indices:
        end = min([b for b in boundaries if b > start], default=len(lines))
        title = lines[start].lstrip("# ").strip()
        chapters.append((title, lines[start:end]))

    if official_index is not None:
        chapters.append(("AZ-104 Official Pages", lines[official_index:]))

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
    return " / ".join(picks) if picks else fallback_title


def _extract_facts(chapter_lines: list[str]) -> list[Fact]:
    facts: list[Fact] = []
    seen: set[str] = set()
    current_section = "General"

    def add_fact(text: str, section: str) -> None:
        text = _clean_line(text)
        if _is_noise(text) or _is_metadata(text) or _is_generic_text(text):
            return
        if _is_heading_like_fact(text) or _is_command_like_fact(text):
            return
        if text.endswith("?") or text.endswith(":"):
            return
        if len(text) < 30 or len(text) > 220:
            return
        if not _looks_relevant(text):
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
            for sentence in re.split(r"(?<=[\.\!\?])\s+", stripped):
                add_fact(sentence, current_section)

    return facts


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOP_WORDS and len(w) > 2}


def _pick_distractors(target: Fact, pool: list[Fact], rng: random.Random) -> list[Fact]:
    target_tokens = _tokenize(target.text)
    scored: list[tuple[int, Fact]] = []
    for fact in pool:
        overlap = len(target_tokens & _tokenize(fact.text))
        section_bonus = 1 if fact.section != target.section else 0
        scored.append((overlap * 10 + section_bonus, fact))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [f for _, f in scored[:18]]
    if len(top) < 3:
        top = [f for _, f in scored]
    if len(top) >= 3:
        return rng.sample(top, 3)
    return (top + pool)[:3]


def _build_header(chapter_question_no: int, subtitle: str, target: Fact) -> list[str]:
    lines: list[str] = []
    lines.append(f"### Question {chapter_question_no}")
    lines.append(f"**Focus area:** {subtitle}")
    lines.append(f"**Reference section:** {target.section}")
    lines.append(f"**{TRADEOFF_CONSTRAINTS[chapter_question_no % len(TRADEOFF_CONSTRAINTS)]}**")
    lines.append("")
    return lines


def _render_options(options: list[str]) -> list[str]:
    labels = ["A", "B", "C", "D", "E"]
    rendered: list[str] = []
    for i, opt in enumerate(options):
        rendered.append(f"- {labels[i]}. {opt}")
    return rendered


def _format_question(
    chapter_question_no: int,
    subtitle: str,
    target: Fact,
    facts: list[Fact],
    distractors: list[Fact],
    rng: random.Random,
) -> str:
    out = _build_header(chapter_question_no, subtitle, target)
    style = ITEM_STYLES[(chapter_question_no - 1) % len(ITEM_STYLES)]

    if style == "choose_two" and len(facts) >= 5:
        same_section = [f for f in facts if f != target and f.section == target.section]
        second_correct = same_section[0] if same_section else facts[1]
        pool = [f for f in facts if f not in (target, second_correct)]
        if len(pool) < 3:
            style = "single_best"
        else:
            wrong = rng.sample(pool, 3)
            option_texts = [target.text, second_correct.text, *(w.text for w in wrong)]
            labels = ["A", "B", "C", "D", "E"]
            indices = list(range(len(option_texts)))
            rng.shuffle(indices)
            shuffled = [option_texts[i] for i in indices]
            label_map = {i: labels[pos] for pos, i in enumerate(indices)}
            ans_labels = sorted([label_map[0], label_map[1]])
            out.append("**Item type:** Choose TWO.")
            out.append("Select the two options that best satisfy the requirement.")
            out.append("")
            out.extend(_render_options(shuffled))
            out.append("")
            out.append(f"**Correct answer: {ans_labels[0]}, {ans_labels[1]}**")
            out.append(
                f"**Explanation:** The two correct options come from the target section '{target.section}'."
            )
            out.append(f"> {target.text}")
            out.append(f"> {second_correct.text}")
            out.append("")
            return "\n".join(out)

    if style == "sequence" and len(facts) >= 6:
        pool = [f for f in facts if f != target]
        seq_facts = [target, *rng.sample(pool, 3)]
        display = seq_facts[:]
        rng.shuffle(display)
        position = {f.text: i for i, f in enumerate(facts)}
        ordered_nums = sorted(range(1, 5), key=lambda n: position.get(display[n - 1].text, 999999))
        correct = " -> ".join(str(n) for n in ordered_nums)
        # Build three unique wrong orders.
        wrong_orders = []
        for perm in permutations([1, 2, 3, 4]):
            cand = " -> ".join(str(x) for x in perm)
            if cand == correct:
                continue
            wrong_orders.append(cand)
            if len(wrong_orders) >= 12:
                break
        rng.shuffle(wrong_orders)
        options = [correct, *wrong_orders[:3]]
        rng.shuffle(options)
        labels = ["A", "B", "C", "D"]
        ans = labels[options.index(correct)]
        out.append("**Item type:** Sequence.")
        out.append("Arrange the following steps in the best order to match the documented flow.")
        out.append("")
        for i, fact in enumerate(display, start=1):
            out.append(f"Step {i}: {fact.text}")
        out.append("")
        out.extend(_render_options(options))
        out.append("")
        out.append(f"**Correct answer: {ans}**")
        out.append("**Explanation:** The correct sequence follows the chapter's progression for related steps.")
        out.append(f"> {display[ordered_nums[0]-1].text}")
        out.append(f"> {display[ordered_nums[1]-1].text}")
        out.append("")
        return "\n".join(out)

    if style == "true_false_combo" and len(facts) >= 4:
        s1 = target
        alt = [f for f in facts if f != target and f.section != target.section]
        s2 = alt[0] if alt else facts[1]
        out.append("**Item type:** True/False combination.")
        out.append("For the target section context, evaluate the statements:")
        out.append(f"I. {s1.text}")
        out.append(f"II. {s2.text}")
        out.append("")
        out.append("A. Both statements are true in the target section context.")
        out.append("B. Statement I is true and Statement II is false in the target section context.")
        out.append("C. Statement I is false and Statement II is true in the target section context.")
        out.append("D. Both statements are false in the target section context.")
        out.append("")
        out.append("**Correct answer: B**")
        out.append(
            f"**Explanation:** Statement I is a direct statement from section '{target.section}'. "
            "Statement II is from a different section and is not the best fit for this section context."
        )
        out.append(f"> {s1.text}")
        out.append("")
        return "\n".join(out)

    # Default single-best-answer item.
    stem = STEM_VARIANTS[chapter_question_no % len(STEM_VARIANTS)]
    options = [target.text, *(d.text for d in distractors)]
    rng.shuffle(options)
    labels = ["A", "B", "C", "D"]
    answer_label = labels[options.index(target.text)]
    out.append("**Item type:** Single best answer.")
    out.append(stem)
    out.append("")
    out.extend(_render_options(options))
    out.append("")
    out.append(f"**Correct answer: {answer_label}**")
    out.append(
        f"**Explanation:** The correct option matches a source statement under section label '{target.section}' in this chapter."
    )
    out.append(f"> {target.text}")
    out.append("")
    return "\n".join(out)


def _markdown_to_plain_text(md_text: str) -> str:
    lines: list[str] = []
    for raw in md_text.splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            line = re.sub(r"^#+\s*", "", line)
        line = re.sub(r"^\-\s+", "", line)
        line = re.sub(r"^\>\s+", "", line)
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
        if line.startswith("> "):
            out.append(f"<blockquote>{html.escape(line[2:])}</blockquote>")
            continue
        line = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html.escape(line))
        out.append(f"<p>{line}</p>")

    close_ul()
    return "\n".join(out)


def _write_formats(md_path: Path) -> dict[str, Path]:
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
        book.add_author("AZ-104 Exam-Style Test Book Generator")

        style = epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content=(
                "body{font-family:Georgia,serif;line-height:1.6;margin:1em 1.4em;}"
                "h1{color:#0078D4;}h2{color:#005a9e;}h3{color:#333;}p{margin:.45em 0;}"
                "li{margin:.2em 0;}strong{font-weight:700;}blockquote{color:#444;}"
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
        written["epub"] = epub_path
    except Exception:
        pass

    return written


def build_examstyle_book(source_md: Path, out_md: Path) -> None:
    source = source_md.read_text(encoding="utf-8")
    chapters = _split_chapters(source)

    lines: list[str] = []
    lines.append("# AZ-104 Exam-Style Chapter Test Book")
    lines.append("")
    lines.append(
        "This chapter-based book contains exam-style MCQs generated from the AZ-104 source book. "
        "Each chapter includes 15 non-scenario exam-style questions with answer and source-grounded explanation."
    )
    lines.append("")

    coverage_rows: list[dict[str, object]] = []

    for chapter_idx, (title, chapter_lines) in enumerate(chapters, start=1):
        facts = _extract_facts(chapter_lines)
        if len(facts) < 4:
            continue
        subtitle = _chapter_subtitle(chapter_lines, title)

        seed = int(sha1(f"examstyle:{chapter_idx}:{title}".encode("utf-8")).hexdigest(), 16) % (2**32)
        rng = random.Random(seed)
        facts = facts[:]
        rng.shuffle(facts)

        lines.append(f"## Chapter {chapter_idx}: {title}")
        lines.append("")
        lines.append(f"**Subtitle:** {subtitle}")
        lines.append("")

        question_count = max(MIN_QUESTIONS_PER_CHAPTER, len(facts))
        targets = [facts[i % len(facts)] for i in range(question_count)]
        for qn, target in enumerate(targets, start=1):
            pool = [f for f in facts if f != target]
            distractors = _pick_distractors(target, pool, rng)
            lines.append(
                _format_question(
                    chapter_question_no=qn,
                    subtitle=subtitle,
                    target=target,
                    facts=facts,
                    distractors=distractors,
                    rng=rng,
                )
            )

        coverage_rows.append(
            {
                "chapter_index": chapter_idx,
                "chapter_title": title,
                "facts_available": len(facts),
                "questions_generated": question_count,
            }
        )

    out_md.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    coverage_path = out_md.with_name("AZ-104_ExamStyle_Chapter_Test_Book_Coverage.json")
    coverage_path.write_text(
        json.dumps(
            {
                "chapters_written": len(coverage_rows),
                "min_questions_per_chapter": MIN_QUESTIONS_PER_CHAPTER,
                "total_questions_generated": sum(int(r["questions_generated"]) for r in coverage_rows),
                "chapters": coverage_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_formats(out_md)


def main() -> None:
    project_root = Path(__file__).resolve().parent
    run_dir = _latest_output_dir(project_root)
    source_md = run_dir / "book" / "AZ-104_Microsoft_Learn_Verbatim.md"
    if not source_md.exists():
        raise FileNotFoundError(f"Source book not found: {source_md}")

    out_md = run_dir / "book" / "AZ-104_ExamStyle_Chapter_Test_Book.md"
    build_examstyle_book(source_md, out_md)
    print(f"Created: {out_md}")


if __name__ == "__main__":
    main()
