from __future__ import annotations

import html
import logging
import re
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)


def _safe_filename(text: str) -> str:
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"[^A-Za-z0-9_.-]", "", text)
    return text or "book"


def _unit_map(content_rows: list[dict[str, Any]]) -> dict[tuple[int, int, int], dict[str, Any]]:
    mapping: dict[tuple[int, int, int], dict[str, Any]] = {}
    for row in content_rows:
        key = (row["learning_path_index"], row["module_index"], row["unit_index"])
        mapping[key] = row
    return mapping


def build_txt_book(manifest: dict[str, Any], content_rows: list[dict[str, Any]], output_path: Path, title: str) -> None:
    by_index = _unit_map(content_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write("=" * 72 + "\n")
        handle.write(f"{title}\n")
        handle.write(f"Source URL: {manifest['source_url']}\n")
        handle.write(f"Generated (manifest UTC): {manifest['generated_at_utc']}\n")
        handle.write("=" * 72 + "\n\n")
        for lp in manifest["learning_paths"]:
            handle.write("#" * 72 + "\n")
            handle.write(f"Learning Path {lp['index']}: {lp['title']}\n")
            handle.write("#" * 72 + "\n\n")
            for module in lp["modules"]:
                handle.write("-" * 72 + "\n")
                handle.write(f"Module {lp['index']}.{module['index']}: {module['title']}\n")
                handle.write(f"URL: {module['url']}\n")
                handle.write("-" * 72 + "\n\n")
                for unit in module["units"]:
                    key = (lp["index"], module["index"], unit["index"])
                    row = by_index.get(key)
                    handle.write(f"[{lp['index']}.{module['index']}.{unit['index']}] {unit['title']}\n")
                    handle.write(f"URL: {unit['url']}\n")
                    if not row or not row.get("success"):
                        error = row.get("error", "missing content row") if row else "missing content row"
                        handle.write(f"[FETCH ERROR] {error}\n\n")
                        continue
                    handle.write(row["content"] + "\n\n")


def build_markdown_book(
    manifest: dict[str, Any], content_rows: list[dict[str, Any]], output_path: Path, title: str
) -> None:
    by_index = _unit_map(content_rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        handle.write(f"# {title}\n\n")
        handle.write(f"- Source URL: `{manifest['source_url']}`\n")
        handle.write(f"- Generated (manifest UTC): `{manifest['generated_at_utc']}`\n\n")
        for lp in manifest["learning_paths"]:
            handle.write(f"## Learning Path {lp['index']}: {lp['title']}\n\n")
            for module in lp["modules"]:
                handle.write(f"### Module {lp['index']}.{module['index']}: {module['title']}\n\n")
                handle.write(f"Module URL: {module['url']}\n\n")
                for unit in module["units"]:
                    key = (lp["index"], module["index"], unit["index"])
                    row = by_index.get(key)
                    handle.write(f"#### Unit {lp['index']}.{module['index']}.{unit['index']}: {unit['title']}\n\n")
                    handle.write(f"Unit URL: {unit['url']}\n\n")
                    if not row or not row.get("success"):
                        error = row.get("error", "missing content row") if row else "missing content row"
                        handle.write(f"`FETCH ERROR: {error}`\n\n")
                        continue
                    handle.write(row["content"] + "\n\n")


def append_official_pages_txt(output_path: Path, pages: list[dict[str, Any]]) -> None:
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write("\n" + "=" * 72 + "\n")
        handle.write("AZ-104 OFFICIAL PAGES (COURSE/PATH/CERT/STUDY GUIDE)\n")
        handle.write("=" * 72 + "\n\n")
        for page in pages:
            handle.write("-" * 72 + "\n")
            handle.write(f"[OFFICIAL PAGE {page['page_index']}] {page['extracted_title']}\n")
            handle.write(f"URL: {page['url']}\n")
            handle.write("-" * 72 + "\n")
            if not page.get("success"):
                handle.write(f"[FETCH ERROR] {page.get('error', 'unknown error')}\n\n")
                continue
            handle.write(page["content"] + "\n\n")


def append_official_pages_markdown(output_path: Path, pages: list[dict[str, Any]]) -> None:
    with output_path.open("a", encoding="utf-8") as handle:
        handle.write("\n## AZ-104 Official Pages\n\n")
        for page in pages:
            handle.write(f"### {page['page_index']}. {page['extracted_title']}\n\n")
            handle.write(f"URL: {page['url']}\n\n")
            if not page.get("success"):
                handle.write(f"`FETCH ERROR: {page.get('error', 'unknown error')}`\n\n")
                continue
            handle.write(page["content"] + "\n\n")


def build_epub_book(
    manifest: dict[str, Any],
    content_rows: list[dict[str, Any]],
    output_path: Path,
    title: str,
    official_pages: list[dict[str, Any]] | None = None,
) -> bool:
    try:
        from ebooklib import epub
    except ImportError:
        LOGGER.warning("EPUB not generated because ebooklib is not installed.")
        return False

    by_index = _unit_map(content_rows)
    book = epub.EpubBook()
    book.set_identifier(_safe_filename(title).lower())
    book.set_title(title)
    book.set_language("en")
    book.add_author("Microsoft Learn")

    style = epub.EpubItem(
        uid="style",
        file_name="style/main.css",
        media_type="text/css",
        content=(
            "body{font-family:Georgia,serif;line-height:1.6;margin:1em 1.4em;}"
            "h1{color:#0078D4;}h2{color:#005a9e;}h3{color:#333;}p{margin:.45em 0;}"
            "code{background:#f3f3f3;padding:2px 4px;}"
        ),
    )
    book.add_item(style)

    spine = ["nav"]
    toc = []
    chapters = []

    chapter_no = 1
    for lp in manifest["learning_paths"]:
        for module in lp["modules"]:
            module_title = f"LP {lp['index']} M{module['index']} - {module['title']}"
            html_parts = [f"<h1>{html.escape(module_title)}</h1>", f"<p>{html.escape(module['url'])}</p>"]
            for unit in module["units"]:
                key = (lp["index"], module["index"], unit["index"])
                row = by_index.get(key)
                unit_header = f"Unit {lp['index']}.{module['index']}.{unit['index']} - {unit['title']}"
                html_parts.append(f"<h2>{html.escape(unit_header)}</h2>")
                html_parts.append(f"<p>{html.escape(unit['url'])}</p>")
                if not row or not row.get("success"):
                    error = row.get("error", "missing content row") if row else "missing content row"
                    html_parts.append(f"<p><strong>FETCH ERROR:</strong> {html.escape(error)}</p>")
                    continue
                for line in row["content"].split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("## "):
                        html_parts.append(f"<h3>{html.escape(line[3:])}</h3>")
                    elif line.startswith("### "):
                        html_parts.append(f"<h4>{html.escape(line[4:])}</h4>")
                    elif line.startswith("  - "):
                        html_parts.append(f"<li>{html.escape(line[4:])}</li>")
                    elif line.startswith("    "):
                        html_parts.append(f"<pre><code>{html.escape(line.strip())}</code></pre>")
                    else:
                        html_parts.append(f"<p>{html.escape(line)}</p>")

            chapter = epub.EpubHtml(title=module_title, file_name=f"ch{chapter_no:03d}.xhtml", lang="en")
            # Let ebooklib provide HTML shell; we only provide body content.
            chapter.content = "\n".join(html_parts)
            chapter.add_item(style)
            book.add_item(chapter)
            chapters.append(chapter)
            spine.append(chapter)
            toc.append(chapter)
            chapter_no += 1

    if official_pages:
        extra_parts = ["<h1>AZ-104 Official Pages</h1>"]
        for page in official_pages:
            extra_parts.append(f"<h2>{html.escape(page['extracted_title'])}</h2>")
            extra_parts.append(f"<p>{html.escape(page['url'])}</p>")
            if not page.get("success"):
                extra_parts.append(f"<p><strong>FETCH ERROR:</strong> {html.escape(page.get('error', 'unknown error'))}</p>")
                continue
            for line in page["content"].split("\n"):
                line = line.strip()
                if not line:
                    continue
                if line.startswith("## "):
                    extra_parts.append(f"<h3>{html.escape(line[3:])}</h3>")
                elif line.startswith("### "):
                    extra_parts.append(f"<h4>{html.escape(line[4:])}</h4>")
                elif line.startswith("  - "):
                    extra_parts.append(f"<li>{html.escape(line[4:])}</li>")
                elif line.startswith("    "):
                    extra_parts.append(f"<pre><code>{html.escape(line.strip())}</code></pre>")
                else:
                    extra_parts.append(f"<p>{html.escape(line)}</p>")

        extra = epub.EpubHtml(title="AZ-104 Official Pages", file_name=f"ch{chapter_no:03d}.xhtml", lang="en")
        extra.content = "\n".join(extra_parts)
        extra.add_item(style)
        book.add_item(extra)
        chapters.append(extra)
        spine.append(extra)
        toc.append(extra)

    book.toc = tuple(toc)
    book.spine = spine
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(output_path), book)
    return True


def build_all_formats(
    manifest: dict[str, Any],
    content_rows: list[dict[str, Any]],
    official_pages: list[dict[str, Any]],
    out_dir: Path,
    title: str,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = _safe_filename(title)
    txt_path = out_dir / f"{base_name}.txt"
    md_path = out_dir / f"{base_name}.md"
    epub_path = out_dir / f"{base_name}.epub"

    build_txt_book(manifest, content_rows, txt_path, title)
    build_markdown_book(manifest, content_rows, md_path, title)
    append_official_pages_txt(txt_path, official_pages)
    append_official_pages_markdown(md_path, official_pages)
    written = {"txt": txt_path, "md": md_path}

    try:
        if build_epub_book(manifest, content_rows, epub_path, title, official_pages=official_pages):
            written["epub"] = epub_path
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("EPUB generation failed: %s", exc)
    return written
