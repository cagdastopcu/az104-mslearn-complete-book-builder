from __future__ import annotations

import logging
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


def strip_query_fragment(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", "")).rstrip("/")


def _to_absolute(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return "https://learn.microsoft.com" + href
    return "https://learn.microsoft.com/" + href.lstrip("/")


def _study_guide_doc_links(study_guide_url: str) -> list[str]:
    try:
        response = requests.get(study_guide_url, timeout=20)
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


def collect_official_pages(manifest: dict, source_url: str) -> list[str]:
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
    for lp in manifest.get("learning_paths", []):
        add(lp.get("url", ""))
        for module in lp.get("modules", []):
            add(module.get("url", ""))

    for extra in AZ104_EXTRA_OFFICIAL_PAGES:
        add(extra)

    # Include official documentation links referenced directly by the AZ-104 study guide.
    study_guide_url = "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/az-104"
    for doc_link in _study_guide_doc_links(study_guide_url):
        add(doc_link)
    return urls
