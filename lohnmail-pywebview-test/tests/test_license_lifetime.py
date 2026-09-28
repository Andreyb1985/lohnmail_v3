"""Server-confirmed conversion, persisted cache, UI and entitlement regressions."""
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from core import license_manager as lm
from ui_web.bridge import WebBridge


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(lm, 'LICENSE_DIR', tmp_path)
    monkeypatch.setattr(lm, 'LICENSE_PATH', tmp_path / 'license.json')
    monkeypatch.setattr(lm.LicenseManager, '_current_machine_id', lambda self: 'test-machine')
    return lm.LicenseManager({})


def assert_lifetime_ui(state):
    payload = WebBridge._license_payload(object.__new__(WebBridge), {}, state=state)
    assert payload['status'] == 'active'
    assert payload['status_label'] == 'Aktiv'
    assert payload['type'] == payload['label'] == payload['plan'] == 'Lifetime'
    assert payload['unlimited'] is True
    assert payload['days_remaining'] is None
    for field in ('trial_ends_at', 'related_trial_ends_at', 'current_period_end', 'access_ends_at'):
        assert not payload[field]
    assert 'Testphase' not in payload['message']
    assert [s['status'] for s in payload['state_list'] if s['active']] == ['active']
    return payload


@pytest.mark.parametrize('automatic', [False, True])
@pytest.mark.parametrize('server_status', ['active', 'trialing', 'expiring_soon'])
def test_same_trial_key_converts_and_survives_restart_and_old_expiry(client, automatic, server_status):
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    trial_end = now + timedelta(days=60)
    response = {'license_key': 'LM-TRIAL-SYNTHETIC-0001', 'type': 'trial', 'status': 'trialing',
                'plan': 'Trial', 'trial_ends_at': trial_end.isoformat(),
                'access_ends_at': trial_end.isoformat(), 'days_remaining': 60}
    with patch.object(lm, '_now', return_value=now), patch.object(lm.LicenseManager, '_post', return_value=response):
        assert client.refresh()['status'] == 'trialing'

    # A server may retain history or omit nullable fields. Neither may revive
    # the old cached deadline. Exercise actual manual/automatic bridge methods.
    response = {'type': 'lifetime', 'status': server_status}
    bridge = object.__new__(WebBridge)
    with patch.object(lm, '_now', return_value=now + timedelta(days=7)), patch.object(
        lm.LicenseManager, '_post', return_value=response
    ) as post, patch('ui_web.bridge.load_settings', return_value={}):
        payload = json.loads(bridge.getLicenseState() if automatic else bridge.checkLicense())
        assert payload['unlimited'] is True
        assert post.call_args.args[0] == '/api/license/check'
        assert post.call_args.args[1]['license_key'] == 'LM-TRIAL-SYNTHETIC-0001'
        assert_lifetime_ui(client.load_state())

    # Normal periodic successful checks continue during the sixty days.
    with patch.object(lm, '_now', return_value=trial_end - timedelta(days=1)), patch.object(
        lm.LicenseManager, '_post', return_value=response
    ) as post:
        client.refresh()
        post.assert_called_once()
    with patch.object(lm, '_now', return_value=trial_end + timedelta(days=1)), patch.object(
        lm.LicenseManager, '_post', side_effect=AssertionError('cached use must not request')
    ):
        restarted = lm.LicenseManager({})
        state = restarted.load_state()
        assert state['license_key'] == 'LM-TRIAL-SYNTHETIC-0001'
        assert state['trial_ends_at'] == trial_end.isoformat()
        assert_lifetime_ui(state)
        assert restarted.require_action('processing')[0]
        assert restarted.require_action('send')[0]


def test_lifetime_offline_grace_and_revocation_are_preserved(client):
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    with patch.object(lm, '_now', return_value=now):
        state = client._merge_server_response(client.load_state(), {
            'license_key': 'LM-TRIAL-TEST', 'type': 'lifetime', 'status': 'active',
            'trial_ends_at': (now + timedelta(days=60)).isoformat()})
        client._save_state(state)
    with patch.object(lm, '_now', return_value=now + timedelta(days=31)), patch.object(
        client, '_post', side_effect=OSError('offline')
    ):
        assert not client.require_action('processing')[0]
    with patch.object(client, '_post', return_value={'type': 'lifetime', 'status': 'revoked'}):
        assert client.refresh(force=True)['status'] == 'revoked'
    with patch.object(client, '_post', side_effect=OSError('offline')):
        assert client.refresh(force=True)['status'] == 'revoked'
    assert not client.require_action('processing')[0]


def test_actual_server_routes_feed_same_key_conversion_into_client(client):
    scenario = Path(__file__).resolve().parents[2] / 'license-server/test/lifetime-scenario.mjs'
    if not scenario.exists() or not shutil.which('node'):
        pytest.skip('Separate license-server checkout and Node required for cross-repository test')
    result = subprocess.run(['node', str(scenario)], check=True, capture_output=True, text=True, timeout=30)
    responses = json.loads(result.stdout)
    with patch.object(client, '_post', return_value=responses['trial']):
        trial = client.refresh(force=True)
    with patch.object(client, '_post', return_value=responses['checked']):
        upgraded = client.refresh(force=True)
    assert upgraded['license_key'] == trial['license_key']
    assert_lifetime_ui(upgraded)
    assert_lifetime_ui(lm.LicenseManager({}).load_state())
    with patch.object(client, '_post', return_value=responses['afterExpiry']):
        assert_lifetime_ui(client.refresh(force=True))


def test_converted_lifetime_still_obeys_missing_license_grace_and_device_binding(client):
    now = datetime(2030, 1, 1, tzinfo=timezone.utc)
    with patch.object(lm, '_now', return_value=now):
        client._save_state(client._merge_server_response(client.load_state(), {
            'license_key': 'LM-TRIAL-TEST', 'type': 'lifetime', 'status': 'active'}))
        with patch.object(client, '_post', side_effect=lm.LicenseNotFoundError('License not found')):
            missing = client.refresh(force=True)
        assert missing['status'] == 'license_problem'
        assert missing['days_remaining'] == 14
        assert not WebBridge._license_payload(object.__new__(WebBridge), {}, state=missing)['unlimited']
    with patch.object(lm, '_now', return_value=now + timedelta(days=15)):
        assert not client.require_action('processing')[0]
    with patch.object(lm.LicenseManager, '_current_machine_id', return_value='another-machine'):
        assert client.load_state()['status'] == 'device_mismatch'
        assert not client.require_action('processing')[0]


def test_license_render_replaces_trial_in_all_indicators(client):
    state = client._merge_server_response(client.load_state(), {
        'license_key': 'LM-TRIAL-TEST', 'type': 'lifetime', 'status': 'active',
        'trial_ends_at': '2099-01-01T00:00:00Z', 'days_remaining': 60})
    payload = assert_lifetime_ui(state)
    script = r'''
const fs = require('fs');
const vm = require('vm');
const assert = require('assert/strict');
const source = fs.readFileSync('web/app.js', 'utf8');
const fn = source.slice(source.indexOf('  function applyLicenseState('), source.indexOf('  function collectLicenseeForm('));
const nodes = new Map();
const node = key => { if (!nodes.has(key)) nodes.set(key, {textContent:'Trial · 60 Tage', innerHTML:''}); return nodes.get(key); };
const context = {
  latestLicenseState:null, latestCompanyState:{}, latestDashboardState:{},
  document:{querySelector:node}, firstDateValue:(...x)=>x.find(Boolean),
  setText:(key,value)=>node(key).textContent=value,
  setLabeledIconText:(key,value)=>node(key).textContent=value,
  formatDateTime:x=>x, setLicenseMessage:x=>node('message').textContent=x,
  licenseMessageFromState:x=>x.message, applyLicenseeState:()=>{},
  licenseStatusClass:x=>x, escapeHtml:x=>x, updateWarningCenter:()=>{}
};
vm.createContext(context);
vm.runInContext(fn,context);
context.applyLicenseState(JSON.parse(fs.readFileSync(0,'utf8')));
for (const [key,value] of Object.entries({status:'Aktiv',type:'Lifetime',days:'Unbefristet','access-end':'Unbefristet',badge:'Lifetime'})) {
  assert.equal(node(`[data-license="${key}"]`).textContent,value);
}
for (const key of ['license-pill','footer-license']) assert.equal(node(`[data-dashboard="${key}"]`).textContent,'Lizenz: Lifetime');
assert.ok(!node('message').textContent.includes('Testphase'));
assert.equal(context.latestCompanyState.license.unlimited,true);
assert.equal(context.latestDashboardState.license.days_remaining,null);
'''
    subprocess.run(['node', '-e', script], input=json.dumps(payload), text=True,
                   cwd=Path(__file__).resolve().parents[1], check=True, capture_output=True)
