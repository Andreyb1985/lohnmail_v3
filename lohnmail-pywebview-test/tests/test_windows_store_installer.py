from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_store_installer_is_offline_x64_and_per_user() -> None:
    text = (ROOT / "windows-store-installer.iss").read_text(encoding="utf-8")

    assert "DefaultDirName={localappdata}\\Programs\\LohnMail" in text
    assert "PrivilegesRequired=lowest" in text
    assert "ArchitecturesAllowed=x64compatible" in text
    assert "ArchitecturesInstallIn64BitMode=x64compatible" in text
    assert 'Source: "release\\LohnMail\\App\\*"' in text
    assert "http://" not in text
    assert "https://" not in text
    assert "download" not in text.lower()


def test_store_installer_only_replaces_application_files() -> None:
    text = (ROOT / "windows-store-installer.iss").read_text(encoding="utf-8")

    assert 'Type: filesandordirs; Name: "{app}\\App"' in text
    assert 'Name: "{app}\\Settings"; Flags: uninsneveruninstall' in text
    assert 'Name: "{app}\\Companies"; Flags: uninsneveruninstall' in text
    assert (
        'Source: "release\\LohnMail\\Settings\\settings.json"; '
        'DestDir: "{app}\\Settings"; Flags: onlyifdoesntexist uninsneveruninstall'
    ) in text
    assert 'Type: filesandordirs; Name: "{app}\\Settings"' not in text
    assert 'Type: filesandordirs; Name: "{app}\\Companies"' not in text


def test_store_installer_has_stable_identity_and_silent_mode() -> None:
    installer = (ROOT / "windows-store-installer.iss").read_text(encoding="utf-8")
    builder = (ROOT / "BUILD-STORE-INSTALLER.ps1").read_text(encoding="utf-8")

    assert "AppId={{A804EBDD-BF78-49DD-96A7-5B5986B71B1B}" in installer
    assert "UsePreviousAppDir=yes" in installer
    assert "CloseApplications=yes" in installer
    assert 'silent_parameters = "/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-"' in builder
    assert "Get-AuthenticodeSignature" in builder
    assert "Get-FileHash $OutputPath -Algorithm SHA256" in builder


def test_store_build_rejects_unsigned_zip_updates() -> None:
    version = (ROOT / "ui_web" / "version.py").read_text(encoding="utf-8")

    assert "TEST_UPDATES_ENABLED = False" in version
