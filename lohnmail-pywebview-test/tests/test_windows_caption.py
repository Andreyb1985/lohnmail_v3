from types import SimpleNamespace
from unittest.mock import Mock
import ctypes
import pytest
import pywebview_app as app


@pytest.mark.parametrize("dpi,small,large", [(96,16,32),(120,20,40),(144,24,48),(192,32,64)])
def test_windows_caption_dpi_and_repaint(monkeypatch,dpi,small,large):
    user = Mock()
    user.GetDpiForWindow.return_value = dpi
    user.GetSystemMetricsForDpi.side_effect = lambda index, _: small if index in (49,50) else large
    user.LoadImageW.side_effect = [0x123456789,0x234567890]
    dwm = Mock()
    monkeypatch.setattr(ctypes, 'windll', SimpleNamespace(user32=user,dwmapi=dwm),raising=False)
    monkeypatch.setattr(app.sys,'platform','win32')
    window=SimpleNamespace(native=SimpleNamespace(Handle=0x345678901))
    app._configure_windows_window(window)
    assert [c.args[3:5] for c in user.LoadImageW.call_args_list]==[(small,small),(large,large)]
    assert user.SendMessageW.call_args_list[0].args[-1]==0x123456789
    assert len(user.SendMessageW.argtypes)==4
    assert dwm.DwmSetWindowAttribute.call_count==5
    user.SetWindowPos.assert_called_once()
    user.RedrawWindow.assert_called_once()
