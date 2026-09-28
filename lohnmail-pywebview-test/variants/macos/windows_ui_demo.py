"""Offline tutorial entry point only; never imported by production main.py."""
from contextlib import ExitStack, contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import json
import os
import socket
import sys


def blocked(*args, **kwargs):
    raise RuntimeError('DEMO: Kein echter Versand, keine Netzwerkprüfung oder Zahlung. Outlook Classic benötigt Windows.')


@contextmanager
def demo_runtime(data_dir):
    # Must be selected before importing modules with module-level data paths.
    os.environ['LOHNMAIL_DATA_DIR'] = str(Path(data_dir).resolve())
    os.environ['LICENSE_SERVER_URL'] = 'http://127.0.0.1:9/demo-offline'
    from core import config, secret_store, license_manager, mailer
    config.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    if not config.SETTINGS_PATH.exists():
        settings = config.build_default_settings()
        settings['updates']['auto_check'] = False
        config.SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2))
    state = dict(status='trialing', type='trial', plan='Demo', active=True,
                 blocked=False, days_remaining=60, machine_id='DEMO-OFFLINE',
                 trial_ends_at=(datetime.now(timezone.utc) + timedelta(days=60)).isoformat(),
                 server='Demo (offline)', last_message='Offline-Demonstration')
    secrets = {}
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    def local_only(original):
        def connect(sock, address):
            if not isinstance(address, tuple) or address[0] not in ('127.0.0.1', '::1'):
                return blocked()
            return original(sock, address)
        return connect

    with ExitStack() as stack:
        stack.enter_context(patch.object(secret_store.SecretStore, 'get', lambda self,key: secrets.get(key,'')))
        stack.enter_context(patch.object(secret_store.SecretStore, 'set', lambda self,key,value: secrets.__setitem__(key,value)))
        stack.enter_context(patch.object(secret_store.SecretStore, 'delete', lambda self,key: secrets.pop(key,None)))
        stack.enter_context(patch.object(license_manager.LicenseManager, 'load_state', lambda self: dict(state)))
        stack.enter_context(patch.object(license_manager.LicenseManager, 'refresh', lambda self,*a,**kw: dict(state)))
        stack.enter_context(patch.object(license_manager.LicenseManager, 'machine_id', lambda self: 'DEMO-OFFLINE'))
        stack.enter_context(patch.object(license_manager.LicenseManager, '_post', blocked))
        for name in ('send_email', 'send_email_with_attachment', 'send_email_with_attachments',
                     'send_outlook_email', 'send_outlook_email_with_attachment', 'send_outlook_email_with_attachments',
                     'test_smtp_connection', 'test_outlook_connection', 'list_outlook_accounts'):
            stack.enter_context(patch.object(mailer, name, blocked))
        stack.enter_context(patch.object(socket.socket, 'connect', local_only(original_connect)))
        stack.enter_context(patch.object(socket.socket, 'connect_ex', local_only(original_connect_ex)))
        stack.enter_context(patch.object(socket.socket, 'sendto', blocked))
        import webbrowser
        stack.enter_context(patch.object(webbrowser, 'open', lambda *a,**kw: False))
        from ui_web import bridge
        stack.enter_context(patch.object(bridge, 'OUTLOOK_SUPPORTED', True))
        stack.enter_context(patch.object(bridge, 'SELF_UPDATES_SUPPORTED', True))
        def disabled_update(service, *a, **kw):
            return dict(service.current_state(), status='idle', auto_check=False,
                        install_on_exit=False, install_supported=False,
                        message='DEMO: Update-Oberfläche sichtbar; Download und Installation gesperrt.')
        for name in ('check', 'download', 'install_on_exit'):
            stack.enter_context(patch.object(bridge.UpdateService, name, disabled_update))
        yield


def main():
    if not getattr(sys, 'frozen', False):
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        default_data = Path(__file__).resolve().parents[2] / 'dist/windows-ui-demo-source/UserData'
    else:
        default_data = Path(sys.executable).resolve().parents[3] / 'UserData'
    with demo_runtime(os.environ.get('LOHNMAIL_DEMO_DATA_DIR', str(default_data))):
        import pywebview_app
        import webview
        create = webview.create_window
        def demo_window(title, *args, **kwargs):
            kwargs.update(width=1440, height=900)
            return create('LohnMail — Windows UI Demo · Kein echter Versand', *args, **kwargs)
        with patch.object(webview, 'create_window', demo_window):
            pywebview_app.run()


if __name__ == '__main__':
    main()
