from types import SimpleNamespace

from az104_refactored_tool.fetcher import _repair_mojibake, _response_to_html


def test_repair_mojibake_fixes_common_utf8_latin1_corruption() -> None:
    expected = "you’re not using your work laptop. you have a friend’s laptop."
    broken = expected.encode("utf-8").decode("latin-1")
    assert _repair_mojibake(broken) == expected


def test_response_to_html_uses_utf8_bytes_when_text_is_misdecoded() -> None:
    expected = "<html><body><p>you’re not using your work laptop.</p></body></html>"
    broken = expected.encode("utf-8").decode("latin-1")
    response = SimpleNamespace(content=expected.encode("utf-8"), text=broken)
    assert _response_to_html(response) == expected
