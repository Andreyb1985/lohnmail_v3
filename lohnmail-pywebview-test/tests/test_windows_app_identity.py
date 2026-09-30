from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import ctypes

import pytest
import pywebview_app as app
from core import storage_paths


@pytest.mark.parametrize("packaged", [False, True])
def test_runtime_preserves_package_aumid(monkeypatch, packaged):
    shell = Mock()
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(shell32=shell), raising=False)
    monkeypatch.setattr(app.sys, "platform", "win32")
    monkeypatch.setattr(storage_paths, "package_identity",
                        lambda: ("Synthetic.Family", Path("fixture")) if packaged else None)
    app._set_runtime_app_identity()
    if packaged:
        shell.SetCurrentProcessExplicitAppUserModelID.assert_not_called()
    else:
        shell.SetCurrentProcessExplicitAppUserModelID.assert_called_once_with("LohnMail.Desktop.2")


def test_unknown_package_identity_does_not_overwrite_shell_identity(monkeypatch):
    shell = Mock()
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(shell32=shell), raising=False)
    monkeypatch.setattr(app.sys, "platform", "win32")
    monkeypatch.setattr(storage_paths, "package_identity", Mock(side_effect=OSError("synthetic")))
    app._set_runtime_app_identity()
    shell.SetCurrentProcessExplicitAppUserModelID.assert_not_called()
