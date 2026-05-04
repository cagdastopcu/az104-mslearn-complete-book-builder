from az104_refactored_tool.official_pages import collect_official_pages


def test_collect_official_pages_includes_extras_and_dedupes(monkeypatch) -> None:
    monkeypatch.setattr(
        "az104_refactored_tool.official_pages._study_guide_doc_links",
        lambda _url: [
            "https://learn.microsoft.com/en-us/azure/storage/",
            "https://learn.microsoft.com/en-us/azure/storage/",
        ],
    )

    manifest = {
        "learning_paths": [
            {
                "url": "https://learn.microsoft.com/en-us/training/paths/az-104-manage-identities-governance/?WT.mc_id=api_CatalogApi",
                "modules": [
                    {
                        "url": "https://learn.microsoft.com/en-us/training/modules/intro-to-azure-cloud-shell/?WT.mc_id=api_CatalogApi"
                    }
                ],
            }
        ]
    }
    urls = collect_official_pages(manifest, "https://learn.microsoft.com/en-us/training/courses/az-104t00")
    assert "https://learn.microsoft.com/en-us/training/courses/az-104t00" in urls
    assert "https://learn.microsoft.com/en-us/training/paths/az-104-manage-identities-governance" in urls
    assert "https://learn.microsoft.com/en-us/training/modules/intro-to-azure-cloud-shell" in urls
    assert "https://learn.microsoft.com/en-us/credentials/certifications/azure-administrator" in urls
    assert "https://learn.microsoft.com/en-us/credentials/certifications/resources/study-guides/az-104" in urls
    assert "https://learn.microsoft.com/en-us/azure/storage" in urls
    assert len(urls) == len(set(urls))
