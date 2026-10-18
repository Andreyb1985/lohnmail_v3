"""Exercise the real Windows STA form with synthetic paths, never user data."""
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows WinForms dialog')
@pytest.mark.parametrize('button_label, expected', [('Daten verwenden', 'reuse'), ('Abbrechen', None)])
def test_real_recovery_dialog_buttons(tmp_path, monkeypatch, button_label, expected):
    from core import windows_storage
    original = windows_storage._sta_dialog
    clicked = []

    def automated(callback):
        def run():
            from System.Windows.Forms import Application, Timer
            timer = Timer()
            timer.Interval = 100

            def tick(sender, args):
                for form in list(Application.OpenForms):
                    if str(form.Text) != 'LohnMail – Vorhandene Daten':
                        continue
                    for control in form.Controls:
                        if str(control.Text) == button_label:
                            clicked.append(button_label)
                            timer.Stop()
                            control.PerformClick()
                            return
            timer.Tick += tick
            timer.Start()
            try:
                return callback()
            finally:
                timer.Stop()
                timer.Dispose()
        return original(run)

    monkeypatch.setattr(windows_storage, '_sta_dialog', automated)
    answer = windows_storage.resolve_existing_workspace(tmp_path, 'Synthetic retry message')
    assert clicked == [button_label]
    assert answer == (('reuse', Path(tmp_path)) if expected else None)
