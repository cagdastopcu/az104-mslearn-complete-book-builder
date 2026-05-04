from types import SimpleNamespace

from az104_refactored_tool.fetcher import _normalize_content, _repair_mojibake, _response_to_html


def test_repair_mojibake_fixes_common_utf8_latin1_corruption() -> None:
    expected = "you’re not using your work laptop. you have a friend’s laptop."
    broken = expected.encode("utf-8").decode("latin-1")
    assert _repair_mojibake(broken) == expected


def test_response_to_html_uses_utf8_bytes_when_text_is_misdecoded() -> None:
    expected = "<html><body><p>you’re not using your work laptop.</p></body></html>"
    broken = expected.encode("utf-8").decode("latin-1")
    response = SimpleNamespace(content=expected.encode("utf-8"), text=broken)
    assert _response_to_html(response) == expected


def test_normalize_content_removes_feedback_help_prompt_noise() -> None:
    raw = "\n".join(
        [
            "## Feedback",
            "Was this page helpful?",
            "Need help with this topic?",
            "Want to try using Ask Learn to clarify or guide you through this topic?",
            "Azure RBAC controls access to management operations.",
        ]
    )
    normalized = _normalize_content(raw)
    assert "Feedback" not in normalized
    assert "Was this page helpful?" not in normalized
    assert "Need help with this topic?" not in normalized
    assert "Want to try using Ask Learn" not in normalized
    assert "Azure RBAC controls access to management operations." in normalized
