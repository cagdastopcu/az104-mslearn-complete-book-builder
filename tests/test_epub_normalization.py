from __future__ import annotations

import zipfile
from pathlib import Path

from az104_refactored_tool.book import _normalize_epub_archive


def _write_sample_epub(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        mimetype = zipfile.ZipInfo("mimetype", date_time=(2026, 5, 5, 10, 15, 0))
        mimetype.compress_type = zipfile.ZIP_STORED
        zf.writestr(mimetype, b"application/epub+zip", compress_type=zipfile.ZIP_STORED)

        chapter = zipfile.ZipInfo("OEBPS/ch001.xhtml", date_time=(2026, 5, 5, 10, 17, 0))
        chapter.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(chapter, b"<html><body><p>Sample</p></body></html>", compress_type=zipfile.ZIP_DEFLATED)


def test_epub_normalization_is_idempotent(tmp_path: Path) -> None:
    epub_path = tmp_path / "sample.epub"
    _write_sample_epub(epub_path)

    _normalize_epub_archive(epub_path)
    first = epub_path.read_bytes()

    _normalize_epub_archive(epub_path)
    second = epub_path.read_bytes()

    assert first == second

