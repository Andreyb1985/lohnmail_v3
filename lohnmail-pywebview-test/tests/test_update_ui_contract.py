from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_update_page_uses_one_progressive_primary_action() -> None:
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert html.count('data-update-primary-action="true"') == 1
    assert html.count('data-update-action="check"') == 1
    assert 'data-update-action="download"' not in html
    assert 'data-update-action="install-now"' not in html
    assert 'data-update-download hidden' in html
    assert 'data-update-step="check"' in html
    assert 'data-update-step="restart"' in html


def test_update_page_contains_approved_user_data_guarantees() -> None:
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

    assert "Nur der Ordner App wird ersetzt" in html
    assert "Settings, Unternehmen, Berichte und Lizenzdaten" in html
    assert "vorherige App-Version wiederhergestellt" in html


def test_update_primary_action_stacks_before_laptop_layout_becomes_too_narrow() -> None:
    css = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")

    assert "@media(max-width:1700px)" in css
    assert ".settings-update-panel .update-page-layout" in css
    assert ".settings-update-panel .update-action-row" in css
    assert ".settings-update-panel .update-action-row .primary" in css
    assert "grid-template-columns:1fr" in css
    assert "min-width:0" in css
