"""Separate process prevents demo mocks/data paths leaking into other tests."""
import subprocess
import sys
from pathlib import Path


def test_isolated_windows_ui_demo(tmp_path):
    root = Path(__file__).resolve().parents[1]
    code = r'''
import json, socket, sys
from pathlib import Path
from variants.macos.windows_ui_demo import demo_runtime
with demo_runtime(sys.argv[1]):
    from core import config, mailer
    from ui_web.bridge import WebBridge, UpdateService
    b = WebBridge()
    from core.license_manager import LicenseManager
    assert LicenseManager().require_action('processing')[0], 'Demo trial must permit local processing'
    state = b._settings_payload(config.load_settings())
    assert state['outlook_supported'] is True
    assert state['updates_supported'] is True
    assert config.load_settings()['companies'] == []
    assert config.load_settings()['smtp']['username'] == ''
    result = json.loads(b.getOutlookAccounts())
    assert result['ok'] is False and 'DEMO' in result['message']
    for name in ('send_email','send_email_with_attachment','send_email_with_attachments',
                 'send_outlook_email','send_outlook_email_with_attachment','send_outlook_email_with_attachments',
                 'test_smtp_connection','test_outlook_connection'):
        try: getattr(mailer, name)()
        except RuntimeError as e: assert 'DEMO' in str(e)
        else: raise AssertionError(name)
    for name in ('check','download','install_on_exit'):
        assert getattr(UpdateService(),name)()['install_supported'] is False
    with socket.socket() as sock:
        try: sock.connect(('203.0.113.1',443))
        except RuntimeError: pass
        else: raise AssertionError('network allowed')
    assert not list(Path(sys.argv[1]).rglob('license.json'))
    # Exercise the actual bridge entry point and processing job, not only UI flags.
    import fitz, time
    from openpyxl import Workbook
    from unittest.mock import patch
    from core import email_validation
    folder = Path(sys.argv[1]) / 'input'
    folder.mkdir()
    doc = fitz.open()
    doc.new_page().insert_text((72,72), 'Demo Mitarbeiter 00101')
    doc.save(folder / '00101.pdf')
    doc.close()
    book = Workbook()
    book.active.append(['PersNr','Email','Name','Vorname'])
    book.active.append(['00101','demo@example.com','Demo','Anna'])
    excel = Path(sys.argv[1]) / 'employees.xlsx'
    book.save(excel)
    settings = config.load_settings()
    settings['companies'] = [{'id':'demo','name':'Demo','email_excel_file':str(excel)}]
    settings['selected_company_id'] = 'demo'
    settings['ui'].update(last_pdf_dir=str(folder),last_excel_file=str(excel),last_pdf_input_mode='folder')
    config.save_settings(settings)
    with patch.object(email_validation, '_dns_check', return_value=('valid','mock DNS')):
        b.startCheck()
        deadline = time.monotonic() + 10
        while b._processing_running and time.monotonic() < deadline:
            time.sleep(.01)
    assert not b._processing_running
    assert b._processing_status['finished'], b._processing_status
    assert b._processing_status['errors'] == 0, b._processing_status
    assert list(config.COMPANIES_DIR.rglob('audit_check.xlsx'))
from ui_web import bridge
assert bridge.OUTLOOK_SUPPORTED == (sys.platform == 'win32')
'''
    subprocess.run([sys.executable, '-c', code, str(tmp_path/'demo')], cwd=root, check=True, timeout=30)
