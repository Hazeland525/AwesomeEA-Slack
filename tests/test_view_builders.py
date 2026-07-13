from listeners.views.app_home_builder import build_app_home_view


def test_build_app_home_view_default():
    view = build_app_home_view()

    assert view["type"] == "home"
    block_types = [b["type"] for b in view["blocks"]]
    assert "header" in block_types
    assert "section" in block_types

    header = next(b for b in view["blocks"] if b["type"] == "header")
    assert "remember" in header["text"]["text"]

    section = next(b for b in view["blocks"] if b["type"] == "section")
    assert "Nothing yet" in section["text"]["text"]


def test_build_app_home_view_with_pref():
    pref = "Be faster and more concise; short confirmations only."
    view = build_app_home_view(pref=pref)

    assert view["type"] == "home"
    section = next(b for b in view["blocks"] if b["type"] == "section")
    assert pref in section["text"]["text"]
