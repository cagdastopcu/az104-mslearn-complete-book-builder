from az104_refactored_tool.catalog import normalize_learn_url, strip_query_and_fragment, uid_from_training_url


def test_uid_from_course_url() -> None:
    uid, kind = uid_from_training_url("https://learn.microsoft.com/en-us/training/courses/az-104t00")
    assert uid == "course.az-104t00"
    assert kind == "course"


def test_uid_from_learning_path_url() -> None:
    uid, kind = uid_from_training_url("https://learn.microsoft.com/en-us/training/paths/administer-infrastructure-resources-azure")
    assert uid == "learn.administer-infrastructure-resources-azure"
    assert kind == "learningPath"


def test_uid_from_module_url() -> None:
    uid, kind = uid_from_training_url("https://learn.microsoft.com/en-us/training/modules/configure-file-and-folder-backups")
    assert uid == "learn.configure-file-and-folder-backups"
    assert kind == "module"


def test_normalize_learn_url() -> None:
    assert (
        normalize_learn_url("https://learn.microsoft.com/learn/modules/sample-module")
        == "https://learn.microsoft.com/en-us/training/modules/sample-module"
    )


def test_strip_query_and_fragment() -> None:
    assert (
        strip_query_and_fragment(
            "https://learn.microsoft.com/en-us/training/modules/intro-to-azure-cloud-shell/?WT.mc_id=api_CatalogApi#section"
        )
        == "https://learn.microsoft.com/en-us/training/modules/intro-to-azure-cloud-shell"
    )
