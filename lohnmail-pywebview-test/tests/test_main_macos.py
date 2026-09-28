from __future__ import annotations

import mimetypes

import main


def test_macos_mimetypes_do_not_probe_system_files(monkeypatch) -> None:
    monkeypatch.setattr(main.sys, "platform", "darwin")
    monkeypatch.setattr(mimetypes, "knownfiles", ["/etc/apache2/mime.types"])
    monkeypatch.setattr(mimetypes, "inited", False)
    monkeypatch.setattr(mimetypes, "_db", None)

    main._initialize_mimetypes_for_macos_sandbox()

    assert mimetypes.knownfiles == []
    assert mimetypes.inited is True
    assert mimetypes.guess_type("document.pdf")[0] == "application/pdf"
