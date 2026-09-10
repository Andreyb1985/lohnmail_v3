from pathlib import Path
import struct


PROJECT = Path(__file__).resolve().parents[1]
REPOSITORY = PROJECT.parent


def test_msix_manifest_is_full_trust_x64_with_minimal_capabilities() -> None:
    manifest = (PROJECT / "variants/windows/msix/AppxManifest.xml.in").read_text(encoding="utf-8")

    assert 'ProcessorArchitecture="x64"' in manifest
    assert 'Executable="LohnMail.exe"' in manifest
    assert 'EntryPoint="Windows.FullTrustApplication"' in manifest
    assert 'Name="Windows.Desktop"' in manifest
    assert 'MinVersion="10.0.17763.0"' in manifest
    assert '<Capability Name="internetClient" />' in manifest
    assert '<rescap:Capability Name="runFullTrust" />' in manifest
    assert "@@IDENTITY_NAME@@" in manifest
    assert "@@PUBLISHER@@" in manifest
    assert "@@MSIX_VERSION@@" in manifest


def test_store_assets_have_required_exact_dimensions() -> None:
    expected = {
        "Square44x44Logo.png": (44, 44),
        "Square150x150Logo.png": (150, 150),
        "StoreLogo.png": (50, 50),
        "Wide310x150Logo.png": (310, 150),
        "SplashScreen.png": (620, 300),
    }
    for name, size in expected.items():
        data = (PROJECT / "variants/windows/msix/assets" / name).read_bytes()
        assert data[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", data[16:24]) == size


def test_store_build_excludes_user_data_and_uses_makeappx() -> None:
    script = (PROJECT / "variants/windows/build-store.ps1").read_text(encoding="utf-8")

    assert 'build-standalone.ps1" -Distribution store' in script
    assert "MakeAppx.exe" in script
    assert "Benutzerdaten dürfen nicht im MSIX enthalten sein" in script
    assert "Settings|Companies" in script
    assert "pdf|xlsx?|xlsm|csv" in script
    assert "build_info.json" in script
    assert "Get-FileHash $OutputMsix -Algorithm SHA256" in script


def test_store_workflow_builds_validates_and_uploads_msix() -> None:
    workflow = (REPOSITORY / ".github/workflows/build-windows-store.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" in workflow
    assert 'tags:\n      - "v*"' in workflow
    assert "runs-on: windows-latest" in workflow
    assert 'python-version: "3.12"' in workflow
    assert ".\\variants\\windows\\build-store.ps1" in workflow
    assert ".\\variants\\windows\\test-msix-upgrade.ps1" in workflow
    assert "-ApplicationVersion $Info.version" in workflow
    assert "LohnMail-Windows-Store-${{ steps.metadata.outputs.version }}" in workflow
    assert "lohnmail-pywebview-test/dist/store/*.msix" in workflow
    assert "MSIX_TEST_CERT" not in workflow


def test_direct_build_remains_separate_and_keeps_direct_updater() -> None:
    script = (PROJECT / "BUILD-WINDOWS.ps1").read_text(encoding="utf-8")

    assert 'build-standalone.ps1" -Distribution direct' in script
    assert "dist\\direct\\LohnMail" in script
    assert "exe-update.zip" in script
    assert "Settings" in script
    assert "Companies" in script
