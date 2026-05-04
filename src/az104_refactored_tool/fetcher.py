from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

import requests
from bs4 import BeautifulSoup

from .models import UnitContent

LOGGER = logging.getLogger(__name__)

CONTENT_SELECTORS = [
    "div.unit-inner-section",
    "div#unit-inner-section",
    "section.unit-inner-section",
    "main",
    "article",
]

REMOVE_SELECTORS = [
    "nav",
    "header",
    "footer",
    "aside",
    "script",
    "style",
    "noscript",
    "div.feedback-section",
    "div.action-container",
    "div.locale-selector",
    "button",
    "form",
    "svg",
]

NOISE_LINE_PATTERNS = [
    r"^Skip to main content$",
    r"^Module Assessment Results$",
    r"^Assess your understanding of this module\..*",
    r"^Choose the Azure account that's right for you\..*",
    r"^Get started with Azure$",
    r"^Read in English$",
    r"^Feedback$",
    r"^Back to top$",
    r"^Ask Learn$",
    r"^Light\s+Dark\s+High contrast$",
    r"^Would you like to request an achievement code\?$",
    r"^Achievement Code$",
    r"^Loading\.\.\.$",
    r"^Previous$",
    r"^Next$",
    r"^Sign in$",
    r"^-\s+Module$",
    r"^-\s+Learning Path$",
    r"^-\s+Level\b.*$",
    r"^-\s+Skill\b.*$",
    r"^-\s+Role\b.*$",
    r"^-\s+Introduction\s+min$",
    r"^-\s+Summary\s+min$",
    r"^-\s+Summary and resources\s+min$",
    r"^-\s+Module assessment\s+min$",
    r"^-\s+\d+\s+minutes?$",
    r"^In this unit$",
    r"^In this module$",
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


MOJIBAKE_MARKERS = ("â", "Ã", "\ufffd", "\x80", "\x99", "\x9c", "\x9d")


def _mojibake_score(text: str) -> int:
    return sum(text.count(marker) for marker in MOJIBAKE_MARKERS)


def _repair_mojibake(text: str) -> str:
    """Fix common UTF-8->Latin-1/CP1252 decode corruption."""
    if _mojibake_score(text) == 0:
        return text

    best = text
    best_score = _mojibake_score(best)

    for source_encoding in ("latin-1", "cp1252"):
        try:
            candidate = text.encode(source_encoding).decode("utf-8")
        except UnicodeError:
            continue
        score = _mojibake_score(candidate)
        if score < best_score:
            best = candidate
            best_score = score

    return best


def _response_to_html(response: requests.Response) -> str:
    """Decode HTML deterministically to avoid requests' charset guess issues."""
    content = response.content
    if not content:
        return ""
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return response.text


def _extract_title(soup: BeautifulSoup, fallback: str) -> str:
    if soup.title and soup.title.string:
        return soup.title.string.strip().split(" | ")[0].strip()
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    return fallback


def _extract_content_text(soup: BeautifulSoup) -> str:
    for selector in REMOVE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

    content_root = None
    for selector in CONTENT_SELECTORS:
        content_root = soup.select_one(selector)
        if content_root:
            break
    if not content_root:
        content_root = soup.find("main") or soup.find("body")
    if not content_root:
        return ""

    lines: list[str] = []
    for node in content_root.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "pre", "code", "blockquote", "td", "th"]
    ):
        text = node.get_text(separator=" ", strip=True)
        if not text:
            continue
        if node.name in ("h1", "h2"):
            lines.append(f"\n## {text}\n")
        elif node.name in ("h3", "h4", "h5", "h6"):
            lines.append(f"\n### {text}\n")
        elif node.name == "li":
            lines.append(f"  - {text}")
        elif node.name in ("pre", "code"):
            lines.append(f"\n    {text}\n")
        elif node.name == "blockquote":
            lines.append(f"  > {text}")
        else:
            lines.append(text)

    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def _extract_fallback_text(soup: BeautifulSoup) -> str:
    for selector in REMOVE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()
    root = soup.find("main") or soup.find("article") or soup.find("body")
    if not root:
        return ""
    raw = root.get_text(separator="\n", strip=True)
    return re.sub(r"\n{3,}", "\n\n", raw).strip()


def _is_noise_line(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    for pattern in NOISE_LINE_PATTERNS:
        if re.match(pattern, text, flags=re.IGNORECASE):
            return True
    return False


def _normalize_content(content: str) -> str:
    content = _repair_mojibake(content)
    content = content.replace("\xa0", " ")
    raw_lines = [ln.rstrip() for ln in content.splitlines()]

    cleaned: list[str] = []
    prev_norm = ""
    for line in raw_lines:
        line = re.sub(r"\s+", " ", line).strip()
        if not line:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if _is_noise_line(line):
            continue
        norm = line.lower()
        # Remove immediate duplicates caused by mirrored UI regions.
        if norm == prev_norm:
            continue
        prev_norm = norm
        cleaned.append(line)

    text = "\n".join(cleaned).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def _request_with_retry(
    session: requests.Session,
    url: str,
    retries: int,
    base_backoff_sec: float,
) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = session.get(url, headers=HEADERS, timeout=20)
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_error = exc
            if attempt == retries:
                break
            sleep_time = base_backoff_sec * attempt
            LOGGER.warning("Request failed (%s/%s) for %s: %s", attempt, retries, url, exc)
            time.sleep(sleep_time)
    raise RuntimeError(f"Failed to fetch after {retries} attempts: {url} | {last_error}")


def fetch_from_manifest(
    manifest: dict[str, Any],
    delay_sec: float = 0.6,
    retries: int = 3,
    backoff_sec: float = 1.0,
) -> tuple[list[UnitContent], list[str]]:
    session = requests.Session()
    results: list[UnitContent] = []
    errors: list[str] = []

    for learning_path in manifest.get("learning_paths", []):
        lp_idx = learning_path["index"]
        for module in learning_path.get("modules", []):
            mod_idx = module["index"]
            mod_title = module["title"]
            units = module.get("units", [])
            for unit in units:
                unit_idx = unit["index"]
                unit_url = unit["url"]
                unit_title = unit["title"]
                LOGGER.info(
                    "Fetching LP %s / Module %s (%s) / Unit %s: %s",
                    lp_idx,
                    mod_idx,
                    mod_title,
                    unit_idx,
                    unit_title,
                )
                fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                try:
                    response = _request_with_retry(
                        session=session,
                        url=unit_url,
                        retries=retries,
                        base_backoff_sec=backoff_sec,
                    )
                    html = _response_to_html(response)
                    soup = BeautifulSoup(html, "html.parser")
                    extracted_title = _extract_title(soup, unit_title)
                    content = _extract_content_text(soup)
                    if not content:
                        raise RuntimeError("No extractable content found")
                    content = _normalize_content(content)
                    if not content:
                        raise RuntimeError("No extractable content found after normalization")

                    results.append(
                        UnitContent(
                            learning_path_index=lp_idx,
                            module_index=mod_idx,
                            unit_index=unit_idx,
                            unit_uid=unit["uid"],
                            unit_title=unit_title,
                            url=unit_url,
                            fetched_at_utc=fetched_at,
                            success=True,
                            extracted_title=extracted_title,
                            content=content,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    error_message = str(exc)
                    errors.append(f"{unit_url} | {error_message}")
                    results.append(
                        UnitContent(
                            learning_path_index=lp_idx,
                            module_index=mod_idx,
                            unit_index=unit_idx,
                            unit_uid=unit["uid"],
                            unit_title=unit_title,
                            url=unit_url,
                            fetched_at_utc=fetched_at,
                            success=False,
                            extracted_title=unit_title,
                            content="",
                            error=error_message,
                        )
                    )
                time.sleep(delay_sec)

    return results, errors


def fetch_pages(
    urls: list[str],
    delay_sec: float = 0.6,
    retries: int = 3,
    backoff_sec: float = 1.0,
) -> tuple[list[dict[str, Any]], list[str]]:
    session = requests.Session()
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for i, url in enumerate(urls, start=1):
        LOGGER.info("Fetching official page %s/%s: %s", i, len(urls), url)
        fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            response = _request_with_retry(
                session=session,
                url=url,
                retries=retries,
                base_backoff_sec=backoff_sec,
            )
            html = _response_to_html(response)
            soup = BeautifulSoup(html, "html.parser")
            title = _extract_title(soup, url)
            content = _extract_content_text(soup)
            if not content:
                content = _extract_fallback_text(soup)
            content = _normalize_content(content)
            if not content:
                content = (
                    "This page contains limited or dynamic content in the current session. "
                    "See the official URL for interactive or sign-in-gated details."
                )
            results.append(
                {
                    "page_index": i,
                    "url": url,
                    "fetched_at_utc": fetched_at,
                    "success": True,
                    "extracted_title": title,
                    "content": content,
                    "error": None,
                }
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc)
            errors.append(f"{url} | {message}")
            results.append(
                {
                    "page_index": i,
                    "url": url,
                    "fetched_at_utc": fetched_at,
                    "success": False,
                    "extracted_title": url,
                    "content": "",
                    "error": message,
                }
            )
        time.sleep(delay_sec)

    return results, errors
