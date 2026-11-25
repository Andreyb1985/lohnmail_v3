"""German company IDs agree in the form and backend; existing IDs stay stable."""
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from ui_web.bridge import WebBridge


CASES = [
    ("SZ Feß", "sz-fess"),
    ("Musterstraße GmbH", "musterstrasse-gmbh"),
    ("Müller & Söhne", "mueller-soehne"),
    ("Ä Ö Ü ß ẞ", "ae-oe-ue-ss-ss"),
    ("ÄRZTE ÜBER ÖL", "aerzte-ueber-oel"),
    ("Ma\u0308rchen Mu\u0308hle So\u0308hne", "maerchen-muehle-soehne"),
    ("  Muster__Firma---22  ", "muster-firma-22"),
    ("sz-fe", "sz-fe"),
    ("../Muster/..", "muster"),
    ("", ""),
]


@pytest.mark.parametrize("name,expected", CASES)
def test_german_company_id(name, expected):
    assert WebBridge._normalize_company_id(name) == expected


def test_form_and_backend_generate_identical_ids():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for company form normalization")
    source = Path(__file__).resolve().parents[1] / "web/app.js"
    script = r'''
const fs = require('fs'), vm = require('vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const start = source.indexOf('  function normalizeCompanyId(');
const end = source.indexOf('  function openCompanyCreateModal(', start);
if (start < 0 || end < 0) throw new Error('Company ID function missing');
const context = {};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
const names = JSON.parse(fs.readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(names.map(context.normalizeCompanyId)));
'''
    result = subprocess.run(
        [node, "-e", script, str(source)], input=json.dumps([name for name, _ in CASES]),
        capture_output=True, text=True, check=True, timeout=15,
    )
    assert json.loads(result.stdout) == [expected for _, expected in CASES]


@pytest.mark.parametrize("requested_id", ["", "MÜLLER STRAẞE"])
def test_create_preserves_original_name_existing_ids_and_collision_handling(monkeypatch, requested_id):
    existing = [
        {"id": "mller-strae", "name": "Müller Straße", "pdf_input": "existing-path"},
        {"id": "mueller-strasse", "name": "Other company"},
    ]
    settings = {"companies": deepcopy(existing)}
    saved = []
    monkeypatch.setattr("ui_web.bridge.load_settings", lambda: deepcopy(settings))

    def save(value):
        saved.append(deepcopy(value))
        settings.update(deepcopy(value))

    monkeypatch.setattr("ui_web.bridge.save_settings", save)
    bridge = SimpleNamespace(
        _workflow_running=lambda: False,
        _normalize_company_id=WebBridge._normalize_company_id,
        _store_active_company_pdf=lambda s: None,
        _load_active_company_pdf=lambda s: None,
        _reset_workflow_state=Mock(),
        _processing_payload=lambda s: {}, _shipping_payload=lambda s: {},
        _company_payload=lambda s: s,
        processingStateChanged=SimpleNamespace(emit=Mock()),
        shippingStateChanged=SimpleNamespace(emit=Mock()),
    )
    result = json.loads(WebBridge.createCompany(
        bridge, json.dumps({"name": "Müller Straße", "id": requested_id}),
    ))
    assert result["ok"] is True
    assert len(saved) == 1
    assert saved[0]["companies"][:2] == existing
    assert saved[0]["companies"][-1]["name"] == "Müller Straße"
    assert saved[0]["companies"][-1]["id"] == "mueller-strasse-2"
    assert saved[0]["selected_company_id"] == "mueller-strasse-2"
