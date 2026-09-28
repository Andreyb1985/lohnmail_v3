from __future__ import annotations

import hashlib
import re
import struct
from pathlib import Path
from unittest.mock import MagicMock, patch

import pywebview_app

ROOT = Path(__file__).resolve().parents[1]


def test_macos_build_pins_separate_white_assets():
    script = (ROOT / "BUILD-MACOS.sh").read_text()
    for kind in ("SOURCE", "FILE"):
        relative = re.search(rf'^ICON_{kind}="([^"]+)"', script, re.M)[1]
        expected = re.search(rf'^EXPECTED_ICON_{kind}_SHA256="([^"]+)"', script, re.M)[1]
        assert relative.startswith("variants/macos/assets/")
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_macos_icns_includes_retina_1024_png():
    data = (ROOT / "variants/macos/assets/LohnMail.icns").read_bytes()
    assert data[:4] == b"icns"
    assert struct.unpack(">I", data[4:8])[0] == len(data)
    offset = 8
    layers = {}
    while offset < len(data):
        kind, length = struct.unpack(">4sI", data[offset:offset + 8])
        assert length > 8
        layers[kind] = data[offset + 8:offset + length]
        offset += length
    assert offset == len(data)
    assert len(layers) >= 10
    retina = layers[b"ic10"]
    assert retina[:8] == b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II", retina[16:24]) == (1024, 1024)


def test_frozen_macos_uses_transparent_dock_icon():
    appkit = MagicMock()
    with patch.object(pywebview_app.sys, "platform", "darwin"), \
         patch.object(pywebview_app.sys, "frozen", True, create=True), \
         patch.dict("sys.modules", {"AppKit": appkit}):
        pywebview_app._set_macos_dock_icon()
    appkit.NSImage.alloc().initWithContentsOfFile_.assert_called_once_with(
        str(ROOT / "web/assets/brand/lohnmail-app-icon-previous.png")
    )
    appkit.NSApplication.sharedApplication().setApplicationIconImage_.assert_called_once_with(
        appkit.NSImage.alloc().initWithContentsOfFile_.return_value
    )


def test_missing_dock_asset_keeps_bundle_fallback(tmp_path):
    appkit = MagicMock()
    with patch.object(pywebview_app.sys, "platform", "darwin"), \
         patch.object(pywebview_app, "MACOS_DOCK_ICON_PATH", tmp_path / "missing.png"), \
         patch.dict("sys.modules", {"AppKit": appkit}):
        pywebview_app._set_macos_dock_icon()
    appkit.NSApplication.sharedApplication.assert_not_called()


def test_transparent_dock_asset_is_pinned_and_distinct():
    transparent = pywebview_app.MACOS_DOCK_ICON_PATH.read_bytes()
    assert hashlib.sha256(transparent).hexdigest() == (
        "c1160ce7e96c704ea8657310834e423dfe31a1211891a16fd5c1e8d641127deb"
    )
    assert transparent != (ROOT / "variants/macos/assets/LohnMail-white.png").read_bytes()


def test_source_macos_retains_transparent_logo():
    appkit = MagicMock()
    with patch.object(pywebview_app.sys, "platform", "darwin"), \
         patch.object(pywebview_app.sys, "frozen", False, create=True), \
         patch.dict("sys.modules", {"AppKit": appkit}):
        pywebview_app._set_macos_dock_icon()
    appkit.NSImage.alloc().initWithContentsOfFile_.assert_called_once_with(
        str(ROOT / "web/assets/brand/lohnmail-app-icon-previous.png")
    )


def test_windows_does_not_use_macos_artwork():
    appkit = MagicMock()
    with patch.object(pywebview_app.sys, "platform", "win32"), \
         patch.dict("sys.modules", {"AppKit": appkit}):
        pywebview_app._set_macos_dock_icon()
    appkit.NSApplication.sharedApplication.assert_not_called()
