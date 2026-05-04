from __future__ import annotations

import logging
from collections import deque
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)

AZ104_EXTRA_OFFICIAL_PAGES = [
    "https://learn.microsoft.com/en-us/credentials/certifications/azure-administrator/",
    "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/az-104",
]

STUDY_GUIDE_DOC_LINK_LABELS = {
    "Azure documentation",
    "Microsoft Entra ID",
    "Azure Policy",
    "Azure Storage",
    "Azure Storage Explorer",
    "Azure Blob Storage",
    "ARM templates",
    "Azure Container Instances",
    "Azure Container Apps",
    "App Service",
    "Azure DNS",
    "Azure Bastion",
    "Application Gateway",
    "Azure Monitor",
    "Network Watcher",
    "Azure Site Recovery",
    "Azure Backup service",
}

ALLOWED_PREFIXES = (
    "https://learn.microsoft.com/en-us/training/",
    "https://learn.microsoft.com/en-us/credentials/certifications/",
    "https://learn.microsoft.com/en-us/azure/",
)

AZ104_RELEVANT_KEYWORDS = {
    "az-104",
    "azure",
    "entra",
    "active-directory",
    "policy",
    "storage",
    "blob",
    "backup",
    "site-recovery",
    "monitor",
    "network",
    "network-watcher",
    "bastion",
    "dns",
    "load-balancer",
    "application-gateway",
    "resource-manager",
    "bicep",
    "rbac",
    "app-service",
    "container",
    "virtual-machine",
    "vm",
}

HTML_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def strip_query_fragment(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")).rstrip("/")


def _to_absolute(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return "https://learn.microsoft.com" + href
    return "https://learn.microsoft.com/" + href.lstrip("/")


def _is_candidate_official_link(url: str) -> bool:
    if not any(url.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        return False
    lowered = url.lower()
    if "?" in lowered:
        lowered = lowered.split("?", 1)[0]
    return any(keyword in lowered for keyword in AZ104_RELEVANT_KEYWORDS)


def _study_guide_doc_links(study_guide_url: str) -> list[str]:
    try:
        response = requests.get(study_guide_url, headers=HTML_HEADERS, timeout=20)
        response.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("Could not fetch study guide page for doc link extraction: %s", exc)
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        label = " ".join(anchor.get_text(" ", strip=True).split())
        if label not in STUDY_GUIDE_DOC_LINK_LABELS:
            continue
        abs_url = strip_query_fragment(_to_absolute(anchor["href"]))
        if abs_url in seen:
            continue
        seen.add(abs_url)
        links.append(abs_url)
    return links


def _crawl_connected_links(
    seed_urls: list[str],
    already_seen: set[str],
    max_jumps: int,
    max_discovered: int,
) -> list[str]:
    if max_jumps <= 0 or max_discovered <= 0:
        return []

    discovered: list[str] = []
    visited: set[str] = set(already_seen)
    queue = deque((url, 0) for url in seed_urls)

    while queue and len(discovered) < max_discovered:
        current, depth = queue.popleft()
        if depth >= max_jumps:
            continue
        try:
            response = requests.get(current, headers=HTML_HEADERS, timeout=20)
            response.raise_for_status()
        except Exception:  # noqa: BLE001
            continue

        soup = BeautifulSoup(response.text, "html.parser")
        for anchor in soup.find_all("a", href=True):
            raw_href = anchor["href"].strip()
            if not raw_href:
                continue
            next_url = strip_query_fragment(_to_absolute(raw_href))
            if not _is_candidate_official_link(next_url):
                continue
            if next_url in visited:
                continue
            visited.add(next_url)
            discovered.append(next_url)
            if len(discovered) >= max_discovered:
                break
            queue.append((next_url, depth + 1))
    return discovered


def collect_official_pages(
    manifest: dict,
    source_url: str,
    link_jumps: int = 1,
    max_connected_pages: int = 150,
) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def add(url: str) -> None:
        clean = strip_query_fragment(url)
        if not clean:
            return
        if clean in seen:
            return
        seen.add(clean)
        urls.append(clean)

    add(source_url)
    crawl_seeds: list[str] = [strip_query_fragment(source_url)]
    for lp in manifest.get("learning_paths", []):
        add(lp.get("url", ""))
        crawl_seeds.append(strip_query_fragment(lp.get("url", "")))
        for module in lp.get("modules", []):
            add(module.get("url", ""))

    for extra in AZ104_EXTRA_OFFICIAL_PAGES:
        add(extra)
        crawl_seeds.append(strip_query_fragment(extra))

    # Include official documentation links referenced directly by the AZ-104 study guide.
    study_guide_url = "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/az-104"
    for doc_link in _study_guide_doc_links(study_guide_url):
        add(doc_link)

    # Follow connected official links to improve coverage of related AZ-104 pages.
    linked = _crawl_connected_links(
        seed_urls=[u for u in crawl_seeds if u],
        already_seen=seen,
        max_jumps=link_jumps,
        max_discovered=max_connected_pages,
    )
    for linked_url in linked:
        add(linked_url)
    return urls
