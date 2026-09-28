from pathlib import Path


def test_empty_processing_log_does_not_use_timestamp_columns():
    css = (Path(__file__).resolve().parents[1] / "web/styles.css").read_text()
    assert ".operation-log .log-list > div:not(.log-empty) {" in css
    assert ".operation-log .log-list > div {" not in css
    assert ".operation-log .log-list > .log-empty {" in css
    empty = css.split(".operation-log .log-list > .log-empty {", 1)[1].split("}", 1)[0]
    assert "grid-template-columns: 22px minmax(0, 1fr)" in empty
    assert ".operation-log .log-list > .log-empty > em {\n  grid-column: 2;" in css


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


def test_company_creation_uses_only_neutral_example_placeholders():
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")

    assert 'data-company-create="name" placeholder="z. B. Musterunternehmen GmbH"' in html
    assert 'data-company-create="id" placeholder="z. B. musterunternehmen"' in html


def test_large_horizontal_workflow_strips_are_removed():
    html = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    assert '<section class="workflow-card' not in html
    assert 'data-processing-action="start-check"' in html
    assert 'data-shipping-action="start-dry-run"' in html
