from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from .models import LearningPathEntry, Manifest, ModuleEntry, UnitEntry

LOGGER = logging.getLogger(__name__)

CATALOG_API = "https://learn.microsoft.com/api/catalog/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}

HTML_HEADERS = {
    "User-Agent": DEFAULT_HEADERS["User-Agent"],
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def normalize_learn_url(url: str) -> str:
    return url.replace("https://learn.microsoft.com/learn/", "https://learn.microsoft.com/en-us/training/")


def slug_from_uid(uid: str) -> str:
    return uid.split(".")[-1]


def strip_query_and_fragment(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")).rstrip("/")


def _discover_unit_urls_from_module_page(session: requests.Session, module_url: str) -> list[str]:
    clean_module_url = strip_query_and_fragment(module_url)
    module_slug = clean_module_url.rstrip("/").split("/")[-1]
    response = session.get(clean_module_url + "/", headers=HTML_HEADERS, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    found: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href:
            continue

        full_url = ""
        if re.match(r"^\d+-[a-z0-9][a-z0-9-]*$", href, flags=re.IGNORECASE):
            full_url = f"{clean_module_url}/{href}"
        elif href.startswith("/") and f"/training/modules/{module_slug}/" in href:
            full_url = "https://learn.microsoft.com" + href
        elif href.startswith("http") and f"/training/modules/{module_slug}/" in href:
            full_url = href

        if not full_url:
            continue
        full_url = strip_query_and_fragment(full_url)
        if full_url in seen:
            continue
        seen.add(full_url)
        found.append(full_url)
    return found


def uid_from_training_url(url: str) -> tuple[str, str]:
    path = urlparse(url).path
    checks: list[tuple[str, str]] = [
        (r"training/courses/([^/]+)", "course"),
        (r"training/paths/([^/]+)", "learningPath"),
        (r"training/modules/([^/]+)", "module"),
    ]
    for pattern, kind in checks:
        match = re.search(pattern, path)
        if not match:
            continue
        slug = match.group(1)
        if kind == "course":
            return f"course.{slug}", kind
        return f"learn.{slug}", kind
    raise ValueError(f"Unsupported Microsoft Learn URL format: {url}")


def detect_unit_kind(title: str) -> str:
    title_lower = title.lower()
    if "knowledge check" in title_lower:
        return "knowledge-check"
    if "exercise" in title_lower or "lab" in title_lower:
        return "exercise"
    if "introduction" in title_lower:
        return "introduction"
    if "summary" in title_lower:
        return "summary"
    return "content"


def _api_get(session: requests.Session, uid: str, locale: str) -> dict[str, Any]:
    response = session.get(
        CATALOG_API,
        params={"uid": uid, "locale": locale},
        headers=DEFAULT_HEADERS,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def _fetch_units_for_module(
    session: requests.Session, unit_uids: list[str], module_url: str, locale: str, delay_sec: float
) -> list[UnitEntry]:
    if not unit_uids:
        return []

    by_uid: dict[str, dict[str, Any]] = {}
    for i in range(0, len(unit_uids), 20):
        chunk = unit_uids[i : i + 20]
        data = _api_get(session, uid=",".join(chunk), locale=locale)
        for unit in data.get("units", []):
            by_uid[unit.get("uid", "")] = unit
        time.sleep(delay_sec)

    clean_module_url = strip_query_and_fragment(module_url)
    discovered_urls = _discover_unit_urls_from_module_page(session, clean_module_url)
    if discovered_urls:
        LOGGER.debug("Discovered %s unit URLs from module page: %s", len(discovered_urls), clean_module_url)

    result: list[UnitEntry] = []
    for index, unit_uid in enumerate(unit_uids, start=1):
        payload = by_uid.get(unit_uid, {})
        slug = slug_from_uid(unit_uid)
        unit_title = payload.get("title", slug)
        unit_url = discovered_urls[index - 1] if index - 1 < len(discovered_urls) else f"{clean_module_url}/{slug}"
        result.append(
            UnitEntry(
                index=index,
                uid=unit_uid,
                title=unit_title,
                url=unit_url,
                duration_minutes=payload.get("duration_in_minutes"),
                kind=detect_unit_kind(unit_title),
            )
        )
    return result


def _fetch_module(
    session: requests.Session, module_uid: str, index: int, locale: str, delay_sec: float
) -> ModuleEntry:
    data = _api_get(session, uid=module_uid, locale=locale)
    modules = data.get("modules", [])
    if not modules:
        raise RuntimeError(f"Module not found in catalog API: {module_uid}")
    module_payload = modules[0]
    module_url = normalize_learn_url(module_payload.get("url", ""))
    unit_entries = _fetch_units_for_module(
        session=session,
        unit_uids=module_payload.get("units", []),
        module_url=module_url,
        locale=locale,
        delay_sec=delay_sec,
    )
    return ModuleEntry(
        index=index,
        uid=module_uid,
        title=module_payload.get("title", module_uid),
        url=module_url,
        duration_minutes=module_payload.get("duration_in_minutes"),
        units=unit_entries,
    )


def _fetch_learning_path(
    session: requests.Session, learning_path_uid: str, index: int, locale: str, delay_sec: float
) -> LearningPathEntry:
    data = _api_get(session, uid=learning_path_uid, locale=locale)
    paths = data.get("learningPaths", [])
    if not paths:
        raise RuntimeError(f"Learning path not found in catalog API: {learning_path_uid}")
    path_payload = paths[0]
    module_uids: list[str] = path_payload.get("modules", [])
    modules: list[ModuleEntry] = []
    for mod_index, mod_uid in enumerate(module_uids, start=1):
        LOGGER.info("Fetching module %s (%s/%s)", mod_uid, mod_index, len(module_uids))
        modules.append(
            _fetch_module(
                session=session,
                module_uid=mod_uid,
                index=mod_index,
                locale=locale,
                delay_sec=delay_sec,
            )
        )
        time.sleep(delay_sec)

    return LearningPathEntry(
        index=index,
        uid=learning_path_uid,
        title=path_payload.get("title", learning_path_uid),
        url=normalize_learn_url(path_payload.get("url", "")),
        duration_minutes=path_payload.get("duration_in_minutes"),
        modules=modules,
    )


def discover_manifest(input_url: str, locale: str = "en-us", delay_sec: float = 0.35) -> Manifest:
    uid, source_type = uid_from_training_url(input_url)
    session = requests.Session()

    LOGGER.info("Source URL: %s", input_url)
    LOGGER.info("Detected source: %s (%s)", uid, source_type)

    learning_paths: list[LearningPathEntry] = []
    course_title = uid

    if source_type == "course":
        data = _api_get(session, uid=uid, locale=locale)
        courses = data.get("courses", [])
        if not courses:
            raise RuntimeError(f"Course not found in catalog API: {uid}")
        course = courses[0]
        course_title = course.get("title", uid)
        learning_path_uids = [x["uid"] for x in course.get("study_guide", []) if x.get("type") == "learningPath"]
        if not learning_path_uids:
            raise RuntimeError(f"No learning paths found under course study_guide: {uid}")
        for lp_index, lp_uid in enumerate(learning_path_uids, start=1):
            LOGGER.info("Fetching learning path %s (%s/%s)", lp_uid, lp_index, len(learning_path_uids))
            learning_paths.append(
                _fetch_learning_path(
                    session=session,
                    learning_path_uid=lp_uid,
                    index=lp_index,
                    locale=locale,
                    delay_sec=delay_sec,
                )
            )
            time.sleep(delay_sec)

    elif source_type == "learningPath":
        learning_paths.append(
            _fetch_learning_path(
                session=session,
                learning_path_uid=uid,
                index=1,
                locale=locale,
                delay_sec=delay_sec,
            )
        )
        course_title = learning_paths[0].title

    elif source_type == "module":
        module = _fetch_module(session=session, module_uid=uid, index=1, locale=locale, delay_sec=delay_sec)
        learning_paths.append(
            LearningPathEntry(
                index=1,
                uid=uid,
                title=module.title,
                url=module.url,
                duration_minutes=module.duration_minutes,
                modules=[module],
            )
        )
        course_title = module.title

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return Manifest(
        source_url=input_url,
        source_uid=uid,
        source_type=source_type,
        locale=locale,
        generated_at_utc=generated_at,
        course_title=course_title,
        learning_paths=learning_paths,
    )
