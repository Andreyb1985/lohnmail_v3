from pathlib import Path


def test_minimum_width_uses_compact_sidebar_and_keeps_update_flow_beside_content():
    root = Path(__file__).resolve().parents[1]
    css = (root / "web" / "styles.css").read_text(encoding="utf-8")
    assert "@media(max-width:1250px)" in css
    assert ":root{--sidebar:84px}" in css
    assert ".nav-item{justify-content:center;padding:0;font-size:0}" in css
    assert "@media(min-width:1041px) and (max-width:1280px)" in css
    assert ".settings-update-panel .update-page-layout{grid-template-columns:minmax(0,1.5fr) minmax(260px,.66fr)}" in css


def test_processing_compact_layout_keeps_paths_in_their_rows():
    root = Path(__file__).resolve().parents[1]
    css = (root / "web" / "styles.css").read_text(encoding="utf-8")
    assert 'grid-template-areas:"import side" "log log"' in css
    assert ".page-processing .processing-main{display:contents}" in css
    assert ".page-processing .import-row .file-field{" in css
    assert "grid-column:3" in css
    assert ".page-processing .import-row .row-status{grid-column:4}" in css


def test_mass_message_ui_contains_attachment_selection_and_confirmation():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web" / "index.html").read_text(encoding="utf-8")
    script = (root / "web" / "app.js").read_text(encoding="utf-8")
    assert 'data-mass-action="choose-attachments"' in html
    assert 'data-mass-preview="attachments"' in html
    assert "chooseMassMessageAttachments" in script
    assert "renderMassAttachments" in script


def test_shipping_preparation_uses_selected_rows():
    script = (Path(__file__).resolve().parents[1] / "web" / "app.js").read_text(encoding="utf-8")
    assert "bridge.startSelectedShippingDryRun(JSON.stringify(selected)" in script
    assert "Bitte mindestens einen sendbaren Mitarbeiter für die Versandvorbereitung auswählen." in script
