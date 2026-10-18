"""Retry the actual bridge/renderer without SMTP, Outlook or license requests."""
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import build_default_settings
from ui_web.bridge import WebBridge
from ui_web.workflow_sessions import WorkflowSessionStore


@pytest.fixture
def shipping(tmp_path):
    pdf, excel = tmp_path / "input.pdf", tmp_path / "employees.xlsx"
    pdf.write_bytes(b"synthetic")
    excel.write_bytes(b"synthetic")
    settings = build_default_settings()
    settings["selected_company_id"] = "synthetic"
    settings["companies"] = [{"id": "synthetic", "name": "Example", "email_excel_file": str(excel)}]
    settings["ui"].update(last_pdf_input_mode="single_pdf", last_pdf_dir=str(pdf))
    settings["smtp"].update(server="wrong.example.invalid", username="sender@example.invalid")
    store = WorkflowSessionStore(tmp_path / "sessions.json")
    with patch("ui_web.bridge.load_settings", side_effect=lambda: deepcopy(settings)), patch(
        "ui_web.bridge.save_settings", side_effect=lambda value: settings.update(deepcopy(value))
    ), patch("ui_web.bridge.LicenseManager.require_action", return_value=(True, {})), patch(
        "ui_web.bridge.company_output_dir", return_value=tmp_path
    ), patch("ui_web.bridge.WorkflowSessionStore", return_value=store), patch(
        "ui_web.bridge.WebBridge._register_result_reports"
    ), patch("ui_web.bridge.WebBridge._settings_payload", return_value={}), patch(
        "ui_web.bridge.WebBridge._processing_payload", return_value={}
    ), patch("core.mailer.test_smtp_connection"), patch("core.mailer.test_outlook_connection"), patch("core.jobs.run_main_job") as job:
        bridge = WebBridge()
        bridge._validation_company_id = "synthetic"
        bridge._validation_input_signature = bridge._input_signature(settings)
        bridge._validation_state = {"ready": True, "rows": [
            {"persnr": str(i), "employee": f"Example {i}", "email": f"person{i}@example.invalid",
             "document": f"{i}.pdf", "status": "OK"} for i in range(1, 4)
        ]}
        yield bridge, settings, job


def rows(statuses):
    return [{"PersNr": p, "Email": f"person{p}@example.invalid", "Files": f"{p}.pdf",
             "Count": 1, "Status": status, "Attachment": f"{p}_protected.pdf"}
            for p, status in statuses.items()]


def result(statuses, dry):
    return {"summary": {"dry_run": dry,
            "prepared_or_sent_count": sum(s == ("Dry-Run" if dry else "Gesendet") for s in statuses.values()),
            "failed_count": sum(s == "Fehler" for s in statuses.values())}, "table_rows": rows(statuses)}


def run(bridge, dry, selected):
    bridge._start_shipping(dry_run=dry, selected_persnr=selected)
    bridge.worker_thread.join(3)
    assert not bridge.worker_thread.is_alive()
    return json.loads(bridge.getShippingState())


@pytest.mark.parametrize("change", ["password", "server", "connectivity"])
def test_connection_failure_reprepare_confirm_send_uses_fresh_settings(shipping, change):
    bridge, settings, job = shipping
    ids = {"1", "2", "3"}
    job.return_value = result(dict.fromkeys(ids, "Dry-Run"), True)
    run(bridge, True, ids)
    job.side_effect = ConnectionError("synthetic connection failure")
    failed = run(bridge, False, ids)
    assert failed["status"]["failed"]
    if change != "connectivity":
        changed = "correct.example.invalid" if change == "server" else "synthetic-password"
        assert json.loads(bridge.saveSettingsState(json.dumps({"smtp": {change: changed}})))["ok"]
    # No delivery is initiated by saving settings or by preview.
    assert job.call_count == 2
    assert not json.loads(bridge.previewSelectedShippingSend(json.dumps(sorted(ids))))["ok"]
    job.side_effect = None
    job.return_value = result(dict.fromkeys(ids, "Dry-Run"), True)
    prepared = run(bridge, True, ids)
    assert prepared["status"]["finished"] and not prepared["status"]["failed"]
    assert job.call_args.kwargs["settings"]["smtp"] == settings["smtp"]
    preview = json.loads(bridge.previewSelectedShippingSend(json.dumps(sorted(ids))))
    assert preview["ok"] and preview["total_count"] == 3
    assert job.call_count == 3  # Preview did not send anything.
    job.return_value = result(dict.fromkeys(ids, "Gesendet"), False)
    sent = run(bridge, False, ids)
    assert sent["metrics"]["sent"] == 3
    assert job.call_args.kwargs["dry_run"] is False


@pytest.mark.parametrize("interrupted", [False, True])
def test_retry_preserves_sent_rows_across_settings_and_restart(shipping, interrupted):
    bridge, settings, job = shipping
    job.return_value = result({"1": "Dry-Run", "2": "Dry-Run", "3": "Dry-Run"}, True)
    run(bridge, True, {"1", "2", "3"})
    if interrupted:
        def fail_after_first(**kwargs):
            kwargs["progress_cb"]({"kind": "shipping_progress", "phase": "sending",
                "current": 1, "total": 3, "sent": 1, "persnr": "1", "status": "complete"})
            raise ConnectionError("synthetic post-delivery failure")
        job.side_effect = fail_after_first
    else:
        job.return_value = result({"1": "Gesendet", "2": "Fehler", "3": "Fehler"}, False)
    run(bridge, False, {"1", "2", "3"})
    assert json.loads(bridge.saveSettingsState(json.dumps({"smtp": {"server": "correct.example.invalid"}})))["ok"]
    bridge = WebBridge()  # Restore persisted confirmations, not only UI checkboxes.
    assert json.loads(bridge.getShippingState())["metrics"]["sent"] == 1
    job.side_effect = None
    job.return_value = result({"2": "Dry-Run"}, True)
    run(bridge, True, {"1", "2"})  # Stale caller includes the already sent recipient.
    assert job.call_args.kwargs["selected_persnr"] == {"2"}
    preview = json.loads(bridge.previewShippingSend())
    assert preview["ok"] and [r["PersNr"] for r in preview["rows"]] == ["2"]
    assert not json.loads(bridge.previewSelectedShippingSend("[]"))["ok"]
    assert not json.loads(bridge.previewSelectedShippingSend('["2", "3"]'))["ok"]
    before = job.call_count
    bridge.startSelectedShippingSend('["2", "3"]')
    assert job.call_count == before  # An unprepared recipient cannot be added.
    job.return_value = result({"2": "Gesendet"}, False)
    sent = run(bridge, False, {"1", "2"})
    assert job.call_args.kwargs["selected_persnr"] == {"2"}
    assert sent["metrics"]["sent"] == 2
    assert {r["persnr"] for r in sent["rows"] if r["status"] == "Gesendet"} == {"1", "2"}
    assert any(r["persnr"] == "3" and r["status"] != "Gesendet" for r in sent["rows"])
    before = job.call_count
    bridge.startSelectedShippingDryRun('["1", "2"]')
    assert job.call_count == before  # No empty set falling back to all recipients.


def test_smtp_edit_during_delivery_keeps_busy_state_and_confirmations(shipping):
    bridge, settings, job = shipping
    job.return_value = result({"1": "Dry-Run", "2": "Dry-Run"}, True)
    run(bridge, True, {"1", "2"})

    def edit_during_send(**kwargs):
        settings["smtp"]["server"] = "correct.example.invalid"
        state = json.loads(bridge.getShippingState())
        assert state["status"]["running"] and not state["status"]["can_send"]
        kwargs["progress_cb"]({"kind": "shipping_progress", "phase": "sending",
            "current": 1, "total": 2, "sent": 1, "persnr": "1", "status": "complete"})
        raise ConnectionError("synthetic connection failure")

    job.side_effect = edit_during_send
    state = run(bridge, False, {"1", "2"})
    assert not state["status"]["running"]
    assert state["metrics"]["sent"] == 1
    assert json.loads(WebBridge().getShippingState())["metrics"]["sent"] == 1


def test_real_renderer_exposes_retry_and_requires_confirmation():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required")
    source = Path(__file__).resolve().parents[1] / "web/app.js"
    script = r'''
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const src=fs.readFileSync(process.argv[1],'utf8');
const label={textContent:''}, button={querySelector:()=>label,setAttribute(k,v){this[k]=v},classList:{toggle(){}}};
const c={document:{querySelector:()=>button},shippingSelectionDirty:false,selectedShippingPersnr:{},
  shippingLiveProgress:{phase:'failed'},latestShippingState:null,previewCalls:0,prepareCalls:0,sendCalls:0};
vm.createContext(c);
for(const name of ['shippingRowSelectable','syncShippingSelectionDefaults','selectedShippingList','selectedShippingRows',
  'shippingPreparationReady','updateShippingPrimaryAction','runShippingAction']) {
  const start=src.indexOf('  function '+name+'('),end=src.indexOf('\n  function ',start+1);
  vm.runInContext(src.slice(start,end),c);
}
c.startShippingDryRun=()=>c.prepareCalls++;
c.openShippingSendPreview=()=>c.previewCalls++;
c.startShippingSend=()=>c.sendCalls++;
function render(status, statuses){
 c.latestShippingState={status,metrics:{ready:3,sent:statuses.filter(s=>s==='Gesendet').length,
   exported:statuses.filter(s=>s==='Dry-Run').length,errors:statuses.filter(s=>s==='Fehler').length},
   rows:statuses.map((status,i)=>({persnr:String(i+1),email:'test@example.invalid',status}))};
 c.syncShippingSelectionDefaults();c.updateShippingPrimaryAction();
}
render({failed:true,dry_run:false,can_send:true},['Dry-Run','Dry-Run','Dry-Run']);
assert.equal(button.disabled,false); assert.equal(label.textContent,'Vorbereitung wiederholen');
assert.equal(button['data-shipping-action'],'start-dry-run');c.runShippingAction(button['data-shipping-action']);
assert.equal(c.prepareCalls,1);assert.equal(c.sendCalls,0);
render({finished:true,dry_run:false,can_send:true},['Gesendet','Fehler','Fehler']);
assert.equal(button.disabled,false);assert.deepEqual(Array.from(c.selectedShippingList()),['2','3']);
assert.equal(c.shippingPreparationReady(),false);
render({finished:true,dry_run:true,can_send:true},['Gesendet','Dry-Run','Bereit']);
assert.equal(button['data-shipping-action'],'start-dry-run'); // Restored selection includes an unprepared row.
render({finished:true,dry_run:true,can_send:true},['Gesendet','Dry-Run','Dry-Run']);
assert.equal(button['data-shipping-action'],'send-now');c.runShippingAction(button['data-shipping-action']);
assert.equal(c.previewCalls,1);assert.equal(c.sendCalls,0);
render({running:true,dry_run:false,can_send:true},['Gesendet','Dry-Run','Dry-Run']);assert.equal(button.disabled,true);
render({running:true,checking_connection:true,dry_run:true,can_send:false},['Bereit']);
assert.equal(button.disabled,true);assert.equal(label.textContent,'Verbindung wird geprüft…');
c.selectedShippingPersnr={};
render({finished:true,failed:true,connection_failed:true,dry_run:true,can_send:true},['Dry-Run']);
assert.equal(button['data-shipping-action'],'send-now');assert.equal(button.disabled,false);
render({finished:true,dry_run:false,can_send:true},['Gesendet','Gesendet','Gesendet']);assert.equal(button.disabled,true);
render({failed:true,dry_run:false,can_send:false},['Bereit']);assert.equal(button.disabled,true);
render({failed:true,dry_run:false,can_send:true},['Keine E-Mail']);assert.equal(button.disabled,true);
const start=src.indexOf('  function startShippingDryRun('),end=src.indexOf('\n  function ',start+1);
vm.runInContext(src.slice(start,end),c);
let checked=0,offline=0,done;
c.window={lohnmailBridge:{prepareSelectedShippingSend:(ids,cb)=>{assert.equal(ids,'["1"]');checked++;done=cb;},
  startSelectedShippingDryRun:(ids,cb)=>{assert.equal(ids,'["1"]');offline++;done=cb;}}};
c.activeCompanyId=()=> 'example';c.resetShippingLiveProgress=()=>{};c.setShippingMessage=()=>{};
c.consumeShippingPayload=()=>{c.latestShippingState.status.running=false;};
c.selectedShippingPersnr={};render({can_send:true},['Bereit']);
c.startShippingDryRun();assert.equal(checked,1);assert.equal(offline,0);assert.equal(button.disabled,true);
c.startShippingDryRun();assert.equal(checked,1);done('{}');
c.runShippingAction('prepare-offline');assert.equal(offline,1);assert.equal(checked,1);
console.log('PASS retry button, failed/sent selection, busy/validation guards, confirmation boundary');
'''
    completed = subprocess.run([node, "-e", script, str(source)], capture_output=True, text=True, timeout=20)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_preflight_failure_stops_before_pdf_then_retry_uses_fresh_company_settings(shipping):
    import socket
    bridge, settings, job = shipping
    events = []
    bridge.shippingError.connect(lambda payload: events.append(json.loads(payload)))
    with patch("core.mailer.test_smtp_connection", side_effect=socket.gaierror("synthetic")) as check:
        bridge.prepareSelectedShippingSend('["1"]')
        bridge.worker_thread.join(3)
        check.assert_called_once()
    job.assert_not_called()
    assert events[-1]["status"]["failed"]
    assert events[-1]["status"]["code"] == "NETWORK_DNS"
    assert events[-1]["status"]["stage"] == "mail_test"
    assert not events[-1]["status"]["running"]
    settings["companies"][0]["mail_settings"] = {"scope":"custom", "smtp":{
        "server":"company.example.invalid", "password":"synthetic-new-password"}}
    order = []
    def prepare(**kwargs):
        order.append("pdf")
        assert kwargs["dry_run"] is True
        return result({"1":"Dry-Run"}, True)
    job.side_effect = prepare
    with patch("core.mailer.test_smtp_connection", side_effect=lambda **kw: order.append("check")) as check:
        bridge.prepareSelectedShippingSend('["1"]')
        bridge.worker_thread.join(3)
    assert order == ["check", "pdf"]
    assert check.call_args.kwargs["smtp_settings"]["server"] == "company.example.invalid"
    assert check.call_args.kwargs["smtp_settings"]["password"] == "synthetic-new-password"
    assert json.loads(bridge.previewSelectedShippingSend('["1"]'))["ok"]
    assert job.call_count == 1  # Confirmation still required; no actual send.


def test_offline_dry_run_and_navigation_do_not_check_transport(shipping):
    bridge, settings, job = shipping
    job.return_value = result({"1":"Dry-Run"}, True)
    with patch.object(bridge, "_check_shipping_connection", side_effect=AssertionError("no network")) as check:
        bridge.navigate("Versand")
        bridge.getShippingState()
        bridge.startSelectedShippingDryRun('["1"]')
        bridge.worker_thread.join(3)
    check.assert_not_called()
    assert job.call_args.kwargs["dry_run"] is True


def test_preflight_is_background_busy_and_stops_on_settings_change(shipping):
    import threading
    bridge, settings, job = shipping
    entered, release = threading.Event(), threading.Event()
    def wait_check(**kwargs):
        entered.set()
        assert release.wait(3)
    with patch("core.mailer.test_smtp_connection", side_effect=wait_check) as check:
        try:
            bridge.prepareSelectedShippingSend('["1"]')
            assert entered.wait(2)
            state = json.loads(bridge.getShippingState())["status"]
            assert state["running"] and state["checking_connection"]
            bridge.prepareSelectedShippingSend('["1"]')
            check.assert_called_once()
            job.assert_not_called()
            settings["smtp"]["password"] = "changed-during-check"
        finally:
            release.set()
            bridge.worker_thread.join(3)
    job.assert_not_called()
    assert not json.loads(bridge.getShippingState())["status"]["running"]


def test_outlook_preflight_and_empty_selection(shipping):
    bridge, settings, job = shipping
    settings["mail_mode"] = "outlook"
    job.return_value = result({"1":"Dry-Run"}, True)
    with patch("ui_web.bridge.OUTLOOK_SUPPORTED", True), patch("core.mailer.test_outlook_connection") as outlook, patch("core.mailer.test_smtp_connection") as smtp:
        bridge.prepareSelectedShippingSend('[]')
        outlook.assert_not_called()
        job.assert_not_called()
        bridge.prepareSelectedShippingSend('["1"]')
        bridge.worker_thread.join(3)
        outlook.assert_called_once()
        smtp.assert_not_called()
    assert job.call_args.kwargs["dry_run"] is True


def test_failed_send_preflight_preserves_prepared_pdfs_and_confirmation(shipping, tmp_path):
    import socket
    bridge, settings, job = shipping
    attachment = tmp_path / "1_protected.pdf"
    attachment.write_bytes(b"existing-pdf")
    prepared = result({"1":"Dry-Run"}, True)
    prepared["table_rows"][0]["Attachment"] = str(attachment)
    job.return_value = prepared
    run(bridge, True, {"1"})
    before = deepcopy(bridge._shipping_source_rows)
    with patch("core.mailer.test_smtp_connection", side_effect=socket.gaierror("synthetic")):
        state = run(bridge, False, {"1"})
    assert state["status"]["connection_failed"]
    assert state["status"]["finished"] and state["status"]["dry_run"]
    assert bridge._shipping_source_rows == before
    assert attachment.read_bytes() == b"existing-pdf"
    assert job.call_count == 1  # Failure did not prepare or send anything.
    assert json.loads(bridge.previewSelectedShippingSend('["1"]'))["ok"]
    assert job.call_count == 1
    job.return_value = result({"1":"Gesendet"}, False)
    run(bridge, False, {"1"})
    assert job.call_count == 2 and job.call_args.kwargs["dry_run"] is False
