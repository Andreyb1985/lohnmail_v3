import json
import socket
import shutil
import subprocess
import threading
import zipfile
from pathlib import Path

import pytest

from core.diagnostics import Diagnostics, NoRedirect, RETENTION, record_handled_error, record_progress


@pytest.fixture
def service(tmp_path):
    now = [1800000000.0]
    sent = []
    credentials = {"key": "LM-TRIAL-SYNTHETIC", "machine_id": "test-machine", "url": "https://invalid.example"}
    d = Diagnostics(tmp_path / "diagnostics", version="2.0.3", build="2026.09.03.1", platform="win32",
        credentials=lambda: credentials, transport=lambda url, credential, report: sent.append(report), clock=lambda: now[0])
    return d, now, sent, credentials


def fail(d, name="Beispielunternehmen"):
    with pytest.raises(socket.gaierror):
        with d.operation("send", "example", name):
            raise socket.gaierror(11001, "secret-password alice@example.com C:\\Users\\Alice\\salary.pdf")


def test_default_off_and_allowlist(service):
    d, now, sent, credentials = service
    fail(d)
    d.flush()
    assert sent == []
    assert d.state()["automatic"] is False
    raw = d.path.read_text()
    for secret in ["secret-password", "alice@example.com", "salary.pdf", credentials["key"], "test-machine"]:
        assert secret not in raw
    report = d.state()["reports"][0]["report"]
    assert report["code"] == "NETWORK_DNS"
    assert report["company"]["name"] == "Beispielunternehmen"
    assert set(report) == {"schema", "id", "operation_id", "occurred_at", "version", "build", "platform", "stage", "company", "code", "frames", "events"}


def test_manual_snapshot_confirmation_does_not_enable_auto(service):
    d, now, sent, _ = service
    d.snapshot("example", "Beispielunternehmen")
    report = d.state()["reports"][0]["report"]
    d.flush()
    assert not sent
    assert d.queue_manual(report["id"])
    d.flush()
    assert sent == [report]
    assert not d.state()["automatic"]
    assert not d.queue_manual(report["id"])


def test_offline_queue_survives_restart_and_backoff(service):
    d, now, sent, credentials = service
    d.consent(True)
    fail(d)
    def offline(*args):
        raise OSError("private connection info")
    d.transport = offline
    d.flush()
    assert d.state()["pending"] == 1
    assert len(d.state()["reports"]) == 1  # no recursive report
    reopened = Diagnostics(d.directory, version=d.version, build=d.build, platform="win32",
        credentials=lambda: credentials, transport=lambda *args: sent.append(args[-1]), clock=lambda: now[0])
    reopened.flush()
    assert not sent
    now[0] += 61
    reopened.flush()
    assert len(sent) == 1
    assert reopened.state()["pending"] == 0


def test_revoke_consent_removes_auto_only_and_no_historical_backfill(service):
    d, now, sent, _ = service
    fail(d)
    d.consent(True)
    d.flush()
    assert not sent
    fail(d)
    auto_id = d.state()["reports"][0]["report"]["id"]
    d.snapshot("other", "Beispiel B")
    manual_id = d.state()["reports"][0]["report"]["id"]
    d.queue_manual(manual_id)
    d.consent(False)
    assert d.state()["pending"] == 1
    d.flush()
    assert [r["id"] for r in sent] == [manual_id]
    assert auto_id != manual_id


def test_dedupe_progress_and_company_snapshot(service):
    d, now, sent, _ = service
    company = {"id": "one", "name": "Beispiel A"}
    with d.operation("mass_message", company["id"], company["name"]):
        company["name"] = "Beispiel B"
        for _ in range(70):
            record_progress()
            record_handled_error(ValueError("employee-secret"))
    assert len(d.state()["reports"]) == 1
    assert d.state()["reports"][0]["report"]["company"]["name"] == "Beispiel A"
    assert len(d.data["events"]) == 4


def test_license_change_never_rebinds_pending_report(service):
    d, now, sent, credential = service
    d.consent(True)
    fail(d)
    credential["key"] = "LM-LIFE-ANOTHER-TEST"
    d.flush()
    assert not sent
    assert d.state()["pending"] == 1


def test_retention_and_export_are_safe(service, tmp_path):
    d, now, sent, _ = service
    d.consent(True)
    fail(d)
    target = tmp_path / "report.zip"
    d.export(target)
    with zipfile.ZipFile(target) as archive:
        assert archive.namelist() == ["diagnostics.json"]
        contents = archive.read("diagnostics.json").decode()
        assert 'binding' not in contents and 'consent' not in contents
        assert 'secret-password' not in contents and 'LM-TRIAL' not in contents
    now[0] += RETENTION + 1
    d.flush()
    assert not d.state()["reports"] and not sent
    assert d.path.stat().st_size < 20 * 1024 * 1024


def test_single_flight_and_nonblocking_reports(service):
    d, now, sent, _ = service
    d.consent(True)
    fail(d)
    entered, release = threading.Event(), threading.Event()
    def transport(*args):
        entered.set(); release.wait(2); sent.append(args[-1])
    d.transport = transport
    thread = threading.Thread(target=d.flush); thread.start()
    assert entered.wait(1)
    d.flush()
    d.consent(False)  # UI not blocked by the network request
    release.set(); thread.join(2)
    assert len(sent) == 1


def test_no_redirect_or_plaintext_transport(service):
    from core.diagnostics import send_report
    assert NoRedirect().redirect_request(None, None, None, None, None, None) is None
    with pytest.raises(ValueError):
        send_report("http://invalid.example", {}, {})


def test_corrupt_journal_does_not_block_startup(service):
    d, now, sent, credential = service
    d.directory.mkdir()
    d.path.write_text("{invalid", encoding="utf-8")
    reopened = Diagnostics(d.directory, version=d.version, build=d.build, platform="win32", credentials=lambda:credential)
    assert not reopened.state()["automatic"]
    assert not reopened.state()["storage_ok"]


def test_python_report_matches_server_contract(service):
    d, now, sent, _ = service
    fail(d)
    module = Path(__file__).resolve().parents[2] / "license-server/lib/diagnostics.js"
    if not module.is_file() or not shutil.which("node") or not (module.parents[1] / "node_modules/pg").exists():
        pytest.skip("Separate license-server checkout with Node dependencies required for cross-repository contract")
    script = "import {validateReport} from " + json.dumps(module.as_uri()) + "; let s=''; for await(const x of process.stdin)s+=x; const r=JSON.parse(s);validateReport(r,Date.parse(r.occurred_at));"
    result = subprocess.run(["node", "--input-type=module", "-e", script], input=json.dumps(d.state()["reports"][0]["report"]), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_wrapped_errors_and_frozen_module_names_are_useful_but_safe():
    from core.diagnostics import safe_failure
    namespace = {"__name__": "core.mailer", "socket": socket}
    code = compile("try:\n raise socket.gaierror(11001, 'secret employee')\nexcept Exception as exc:\n raise RuntimeError('friendly message') from exc", "C:/private/build/path/mailer.py", "exec")
    try:
        exec(code, namespace)
    except Exception as exc:
        failure = safe_failure(exc)
    assert failure["code"] == "NETWORK_DNS"
    assert failure["frames"] == [{"module": "core/mailer.py", "line": 4}, {"module": "core/mailer.py", "line": 2}]
    assert "private" not in json.dumps(failure)


def test_persisted_report_is_reallowlisted(service):
    d, now, sent, credential = service
    fail(d)
    saved = json.loads(d.path.read_text())
    saved["reports"][0]["report"]["raw_exception"] = "secret-salary"
    saved["last_send"] = "secret-email"
    d.path.write_text(json.dumps(saved))
    reopened = Diagnostics(d.directory, version=d.version, build=d.build, platform="win32", credentials=lambda:credential, clock=lambda:now[0])
    assert "secret" not in json.dumps(reopened.state())


def test_report_storage_failure_cannot_break_job_or_enable_autosend(service, monkeypatch):
    d, now, sent, _ = service
    def broken(*args):
        raise PermissionError("private location")
    monkeypatch.setattr("core.diagnostics.atomic_json", broken)
    d.consent(True)
    assert d.state()["automatic"] is False
    fail(d)
    assert d.state()["storage_ok"] is False
    d.flush()
    assert not sent


def test_manual_send_has_priority_over_auto_backlog(service):
    d, now, sent, _ = service
    d.consent(True)
    fail(d)
    d.snapshot("other", "Beispiel B")
    manual = d.state()["reports"][0]["report"]["id"]
    d.queue_manual(manual)
    d.flush()
    assert sent[0]["id"] == manual


@pytest.mark.parametrize("contents", ["{}", '{"events":[],"reports":[{}]}', '{"events":[{"at":"broken"}],"reports":[]}'])
def test_malformed_journal_is_safe(service, contents):
    d, now, sent, credential = service
    d.directory.mkdir()
    d.path.write_text(contents)
    reopened = Diagnostics(d.directory, version=d.version, build=d.build, platform="win32", credentials=lambda:credential)
    assert not reopened.state()["automatic"]
    assert not reopened.state()["reports"]
