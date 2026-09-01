from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core.config import SETTINGS_DIR, app_dir, load_settings, save_settings, user_data_dir
from ui_web.version import APP_BUILD, APP_VERSION, TEST_UPDATES_ENABLED


DEFAULT_MANIFEST_URL = "https://license-server-lm.vercel.app/api/updates/windows/latest"
MAX_MANIFEST_BYTES = 1024 * 1024
REQUIRED_REASONS = {
    "security",
    "critical_security",
    "incompatible",
    "critical_incompatibility",
}


class UpdateError(RuntimeError):
    pass


def _friendly_request_error(exc: Exception, *, download: bool = False) -> str:
    action = "Das Update konnte nicht heruntergeladen werden" if download else "Die Update-Prüfung konnte nicht durchgeführt werden"
    if isinstance(exc, HTTPError):
        if exc.code in {401, 403}:
            return f"{action}. Der Zugriff wurde vom Netzwerk oder Update-Server abgelehnt. Bitte prüfen Sie Firewall oder Proxy und versuchen Sie es erneut."
        if exc.code == 404:
            return f"{action}. Die veröffentlichte Update-Datei wurde auf dem Server nicht gefunden."
        if exc.code == 429:
            return f"{action}. Der Update-Server ist momentan ausgelastet. Bitte versuchen Sie es später erneut."
        if 500 <= exc.code <= 599:
            return f"{action}. Der Update-Server ist vorübergehend nicht verfügbar."
        return f"{action}. Der Update-Server hat die Anfrage nicht angenommen."
    if isinstance(exc, (URLError, TimeoutError, ConnectionError)):
        return f"{action}. Bitte prüfen Sie die Internetverbindung sowie Firewall- und Proxy-Einstellungen."
    return str(exc) or f"{action}."


def _version_parts(value: str) -> tuple[int, ...]:
    parts = [int(part) for part in re.findall(r"\d+", str(value or ""))]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts or [0])


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_newer(version: str, build: str) -> bool:
    remote_version = _version_parts(version)
    local_version = _version_parts(APP_VERSION)
    if remote_version != local_version:
        return remote_version > local_version
    return _version_parts(build) > _version_parts(APP_BUILD)


def _safe_download_url(value: str, *, allow_test_zip: bool = False) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and is_local):
        raise UpdateError("Die Update-Datei muss über HTTPS bereitgestellt werden.")
    suffix = Path(parsed.path).suffix.lower()
    allowed_suffixes = {".exe", ".msi", ".zip"} if allow_test_zip else {".exe", ".msi"}
    if suffix not in allowed_suffixes:
        raise UpdateError("Das Update muss eine signierte EXE- oder MSI-Datei sein.")
    return url


def _verify_windows_signature(path: Path) -> tuple[bool, str]:
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        "& { param([string]$Path) (Get-AuthenticodeSignature -LiteralPath $Path).Status }",
        str(path),
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"Die digitale Signatur konnte nicht geprüft werden: {exc}"

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    status = lines[-1].casefold() if lines else ""
    if result.returncode == 0 and status == "valid":
        return True, ""
    return False, "Die digitale Signatur der Installationsdatei ist ungültig oder nicht vertrauenswürdig."


class UpdateService:
    def __init__(
        self,
        *,
        settings_loader: Callable[[], dict] = load_settings,
        settings_saver: Callable[[dict], None] = save_settings,
        download_dir: Path | None = None,
        history_database: Path | None = None,
        manifest_url: str | None = None,
        opener: Callable = urlopen,
        process_launcher: Callable = subprocess.Popen,
        signature_verifier: Callable[[Path], tuple[bool, str]] = _verify_windows_signature,
        platform: str | None = None,
        test_updates_enabled: bool = TEST_UPDATES_ENABLED,
    ) -> None:
        self._load_settings = settings_loader
        self._save_settings = settings_saver
        self.download_dir = download_dir or SETTINGS_DIR / "updates"
        self.history_database = history_database or SETTINGS_DIR / "lohnmail_history.sqlite3"
        self.manifest_url = (
            manifest_url
            or os.environ.get("LOHNMAIL_UPDATE_MANIFEST_URL", "").strip()
            or DEFAULT_MANIFEST_URL
        )
        self._opener = opener
        self._process_launcher = process_launcher
        self._signature_verifier = signature_verifier
        self.platform = platform or sys.platform
        self.test_updates_enabled = bool(test_updates_enabled)

    def current_state(self) -> dict:
        return self._public_state(dict(self._load_settings().get("updates", {})))

    def recover_interrupted_state(self) -> dict:
        updates = dict(self._load_settings().get("updates", {}))
        if updates.get("status") == "installing":
            installed = (
                str(updates.get("available_version", "") or "") == APP_VERSION
                and str(updates.get("available_build", "") or "") == APP_BUILD
            )
            updates.update({
                "status": "current" if installed else "error",
                "install_on_exit": False,
                "progress": 100 if installed else 0,
                "message": (
                    f"Update auf Version {APP_VERSION} wurde erfolgreich installiert."
                    if installed
                    else "Das Update wurde nicht abgeschlossen. Die vorherige Version wurde wiederhergestellt."
                ),
            })
            self._save_changes(updates)
            return self._public_state(updates)
        if updates.get("status") in {"checking", "downloading"}:
            updates.update({
                "status": "error",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": 0,
                "message": "Der letzte Update-Vorgang wurde unterbrochen.",
            })
            self._save_changes(updates)
        return self._public_state(updates)

    def begin(self, action: str) -> dict:
        if action == "check":
            return self._save_changes({
                "status": "checking",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": 0,
                "message": "Updates werden gesucht.",
            })
        if action == "download":
            return self._save_changes({
                "status": "downloading",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": _safe_int(self._load_settings().get("updates", {}).get("size", 0)),
                "message": "Update wird heruntergeladen.",
            })
        raise UpdateError("Unbekannte Update-Aktion.")

    def set_preferences(self, *, auto_check: bool | None = None, install_on_exit: bool | None = None) -> dict:
        settings = self._load_settings()
        updates = dict(settings.get("updates", {}))
        if auto_check is not None:
            updates["auto_check"] = bool(auto_check)
        if install_on_exit is not None:
            updates["install_on_exit"] = bool(install_on_exit)
        settings["updates"] = updates
        self._save_settings(settings)
        return self._public_state(updates)

    def check(self) -> dict:
        checked_at = datetime.now(timezone.utc).isoformat()
        previous_updates = dict(self._load_settings().get("updates", {}))
        try:
            manifest = self._fetch_manifest()
            if not manifest.get("available", True):
                return self._save_changes({
                    "last_checked_at": checked_at,
                    "status": "current",
                    "available_version": "",
                    "available_build": "",
                    "required": False,
                    "download_url": "",
                    "sha256": "",
                    "size": 0,
                    "release_notes": [],
                    "required_reason": "",
                    "downloaded_path": "",
                    "downloaded_sha256": "",
                    "progress": 0,
                    "downloaded_bytes": 0,
                    "total_bytes": 0,
                    "message": "Keine veröffentlichten Updates.",
                })
            available = _is_newer(manifest["version"], manifest["build"])
            status = "required" if available and manifest["required"] else (
                "available" if available else "current"
            )
            message = (
                f"Version {manifest['version']} ist verfügbar."
                if available
                else "LohnMail ist aktuell."
            )
            existing_download = (
                self._verified_existing_download(previous_updates, manifest)
                if available
                else None
            )
            if existing_download:
                status = "ready"
                message = "Update wurde bereits heruntergeladen und ist zur Installation bereit."
            changes = {
                "last_checked_at": checked_at,
                "status": status,
                "available_version": manifest["version"] if available else "",
                "available_build": manifest["build"] if available else "",
                "required": manifest["required"] if available else False,
                "download_url": manifest["download_url"] if available else "",
                "sha256": manifest["sha256"] if available else "",
                "size": manifest["size"] if available else 0,
                "release_notes": manifest["release_notes"] if available else [],
                "required_reason": manifest["required_reason"] if available else "",
                "test_mode": manifest["test_mode"] if available else False,
                "downloaded_path": str(existing_download) if existing_download else "",
                "downloaded_sha256": manifest["sha256"] if existing_download else "",
                "progress": 100 if existing_download else 0,
                "downloaded_bytes": manifest["size"] if existing_download else 0,
                "total_bytes": manifest["size"] if existing_download else 0,
                "message": message,
            }
            return self._save_changes(changes)
        except Exception as exc:
            return self._save_changes({
                "last_checked_at": checked_at,
                "status": "error",
                "message": _friendly_request_error(exc),
            })

    def download(self, progress: Callable[[dict], None] | None = None) -> dict:
        updates = dict(self._load_settings().get("updates", {}))
        allow_test_zip = self.test_updates_enabled and bool(updates.get("test_mode", False))
        url = _safe_download_url(updates.get("download_url", ""), allow_test_zip=allow_test_zip)
        expected_hash = str(updates.get("sha256", "") or "").strip().lower()
        expected_size = _safe_int(updates.get("size", 0))
        if not url or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            return self._save_changes({"status": "error", "message": "Keine gültige Update-Datei verfügbar."})

        self.download_dir.mkdir(parents=True, exist_ok=True)
        filename = Path(urlparse(url).path).name
        target = self.download_dir / filename
        partial = target.with_suffix(target.suffix + ".part")
        downloaded = 0
        digest = hashlib.sha256()
        try:
            request = Request(url, headers={"User-Agent": f"LohnMail/{APP_VERSION}"})
            with self._opener(request, timeout=60) as response, partial.open("wb") as handle:
                response_size = int(response.headers.get("Content-Length", 0) or 0)
                total = expected_size or response_size
                while True:
                    chunk = response.read(256 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)
                    digest.update(chunk)
                    downloaded += len(chunk)
                    if progress:
                        progress(self._progress_state(downloaded, total))

            if expected_size and downloaded != expected_size:
                raise UpdateError("Die Größe der Update-Datei stimmt nicht mit dem Manifest überein.")
            actual_hash = digest.hexdigest()
            if actual_hash != expected_hash:
                raise UpdateError("Die Integritätsprüfung des Updates ist fehlgeschlagen.")
            partial.replace(target)
            return self._save_changes({
                "status": "ready",
                "progress": 100,
                "downloaded_bytes": downloaded,
                "total_bytes": expected_size or downloaded,
                "downloaded_path": str(target),
                "downloaded_sha256": actual_hash,
                "message": "Update wurde geprüft und ist zur Installation bereit.",
            })
        except Exception as exc:
            partial.unlink(missing_ok=True)
            return self._save_changes({
                "status": "error",
                "progress": 0,
                "downloaded_bytes": 0,
                "total_bytes": expected_size,
                "message": _friendly_request_error(exc, download=True),
            })

    def install_on_exit(self) -> dict:
        updates = dict(self._load_settings().get("updates", {}))
        if not updates.get("install_on_exit") or updates.get("status") != "ready":
            return {"ok": False, "started": False, "message": "Keine Installation beim Beenden geplant."}
        if self.platform != "win32":
            return {"ok": False, "started": False, "message": "Die automatische Installation ist nur unter Windows verfügbar."}

        path = Path(str(updates.get("downloaded_path", "") or ""))
        expected_hash = str(updates.get("downloaded_sha256", "") or "").lower()
        is_test_zip = (
            path.suffix.lower() == ".zip"
            and self.test_updates_enabled
            and bool(updates.get("test_mode", False))
        )
        if not path.is_file() or (path.suffix.lower() not in {".exe", ".msi"} and not is_test_zip):
            return {"ok": False, "started": False, "message": "Installationsdatei wurde nicht gefunden."}
        actual_hash = _sha256_file(path)
        if not expected_hash or actual_hash != expected_hash:
            return {"ok": False, "started": False, "message": "Installationsdatei ist nicht mehr gültig."}
        history_ok, history_message = self._check_history_database()
        if not history_ok:
            return {"ok": False, "started": False, "message": history_message}
        if is_test_zip:
            script = self._write_test_zip_installer(path)
            frozen_build = bool(getattr(sys, "frozen", False))
            runtime_entry = "" if frozen_build else str(app_dir() / "main.py")
            command = [
                "powershell.exe", "-NoProfile", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass",
                "-File", str(script), "-Archive", str(path), "-AppDir", str(app_dir()),
                "-RootDir", str(user_data_dir()), "-ProcessId", str(os.getpid()),
                "-ParentProcessId", str(os.getppid()),
                "-TargetVersion", str(updates.get("available_version", "") or ""),
                "-TargetBuild", str(updates.get("available_build", "") or ""),
                "-RuntimeExecutable", str(Path(sys.executable).resolve()),
                "-RuntimeEntry", runtime_entry,
            ]
            if frozen_build:
                command.append("-FrozenBuild")
        else:
            signature_valid, signature_message = self._signature_verifier(path)
            if not signature_valid:
                return {
                    "ok": False,
                    "started": False,
                    "message": signature_message or "Die digitale Signatur der Installationsdatei ist ungültig.",
                }
            command = ["msiexec.exe", "/i", str(path), "/passive", "/norestart"] if path.suffix.lower() == ".msi" else [str(path), "/SILENT", "/NORESTART"]
        self._process_launcher(command, shell=False, close_fds=True, cwd=str(user_data_dir()))
        self._save_changes({
            "status": "installing",
            "install_on_exit": False,
            "message": "LohnMail wird geschlossen und aktualisiert.",
        })
        return {"ok": True, "started": True, "message": "Update-Installation wurde gestartet."}

    def _check_history_database(self) -> tuple[bool, str]:
        """Validate physical SQLite integrity before the desktop window is closed."""
        database = self.history_database
        if not database.is_file():
            return True, ""
        connection: sqlite3.Connection | None = None
        try:
            # WAL databases may need to create or refresh their -shm sidecar even
            # while only SELECT/PRAGMA quick_check statements are executed.  A
            # strict read-only connection therefore produces false failures on
            # otherwise healthy Windows installations.  mode=rw prevents a
            # missing database from being created but permits normal WAL access.
            uri = database.resolve().as_uri() + "?mode=rw"
            connection = sqlite3.connect(uri, uri=True, timeout=10)
            connection.execute("PRAGMA busy_timeout=10000")
            result = connection.execute("PRAGMA quick_check").fetchall()
            connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
            if result != [("ok",)]:
                raise sqlite3.DatabaseError(str(result))
            return True, ""
        except (OSError, sqlite3.Error):
            return (
                False,
                "Die lokale Berichtshistorie konnte nicht geprüft werden. "
                "LohnMail bleibt geöffnet und es wurden keine Dateien verändert. "
                "Bitte schließen Sie andere LohnMail-Fenster und versuchen Sie es erneut.",
            )
        finally:
            if connection is not None:
                connection.close()

    def _write_test_zip_installer(self, archive: Path) -> Path:
        """Create the Windows helper that replaces App after this process exits."""
        script = archive.parent / "install-test-update.ps1"
        script.write_text(
            r"""param([string]$Archive,[string]$AppDir,[string]$RootDir,[int]$ProcessId,[int]$ParentProcessId=0,[string]$TargetVersion,[string]$TargetBuild,[string]$RuntimeExecutable,[string]$RuntimeEntry,[switch]$FrozenBuild,[switch]$NonInteractive)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $RootDir
$SettingsDir = Join-Path $RootDir 'Settings'
$CompaniesDir = Join-Path $RootDir 'Companies'
$BackupDir = Join-Path $RootDir 'App.update-backup'
$LogPath = Join-Path $SettingsDir 'updates\update-install.log'
$HistoryDb = Join-Path $SettingsDir 'lohnmail_history.sqlite3'
$Stage = Join-Path ([System.IO.Path]::GetTempPath()) ('LohnMailUpdate-' + [guid]::NewGuid())
$OldSettingsHash = if (Test-Path (Join-Path $SettingsDir 'settings.json')) { (Get-FileHash (Join-Path $SettingsDir 'settings.json') -Algorithm SHA256).Hash } else { '' }
$OldCompanyCount = if (Test-Path $CompaniesDir) { @(Get-ChildItem -LiteralPath $CompaniesDir -Recurse -File).Count } else { -1 }
$OldHistoryHash = ''
$Installed = $false
$RolledBack = $false
$ExitCode = 0

$Form = $null
if (-not $NonInteractive) {
  Add-Type -AssemblyName System.Windows.Forms
  Add-Type -AssemblyName System.Drawing
  $Form = New-Object System.Windows.Forms.Form
  $Form.Text = 'LohnMail Update'
  $Form.StartPosition = 'CenterScreen'
  $Form.Size = New-Object System.Drawing.Size(520,210)
  $Form.FormBorderStyle = 'FixedDialog'
  $Form.MaximizeBox = $false
  $Form.MinimizeBox = $false
  $Form.ControlBox = $false
  $Title = New-Object System.Windows.Forms.Label
  $Title.Location = New-Object System.Drawing.Point(24,22)
  $Title.Size = New-Object System.Drawing.Size(455,28)
  $Title.Font = New-Object System.Drawing.Font('Segoe UI',14,[System.Drawing.FontStyle]::Bold)
  $Title.Text = 'LohnMail wird aktualisiert'
  $Status = New-Object System.Windows.Forms.Label
  $Status.Location = New-Object System.Drawing.Point(26,62)
  $Status.Size = New-Object System.Drawing.Size(450,42)
  $Status.Font = New-Object System.Drawing.Font('Segoe UI',10)
  $Progress = New-Object System.Windows.Forms.ProgressBar
  $Progress.Location = New-Object System.Drawing.Point(26,116)
  $Progress.Size = New-Object System.Drawing.Size(450,22)
  $Progress.Minimum = 0
  $Progress.Maximum = 100
  $Form.Controls.AddRange(@($Title,$Status,$Progress))
  $Form.Show()
}
function Set-Step([string]$Text,[int]$Value) {
  if ($NonInteractive) { Write-Host "$Value% $Text"; return }
  $Status.Text = $Text
  $Progress.Value = $Value
  [System.Windows.Forms.Application]::DoEvents()
}
function Show-UpdateMessage([string]$Text,[string]$Caption,[string]$Kind) {
  if ($NonInteractive) { Write-Host "$Caption - $Text"; return }
  [System.Windows.Forms.MessageBox]::Show($Text, $Caption, 'OK', $Kind) | Out-Null
}
function Write-UpdateLog([string]$Text) {
  New-Item -ItemType Directory -Force -Path (Split-Path $LogPath) | Out-Null
  Add-Content -LiteralPath $LogPath -Value ("$(Get-Date -Format o) $Text") -Encoding UTF8
}
function ConvertTo-NativeArgument([string]$Value) {
  return '"' + $Value.Replace('"', '\"') + '"'
}
function Invoke-UpdateRuntime([string]$Runtime,[string[]]$Arguments) {
  $ProcessInfo = New-Object System.Diagnostics.ProcessStartInfo
  $ProcessInfo.FileName = $Runtime
  $ProcessInfo.Arguments = (($Arguments | ForEach-Object { ConvertTo-NativeArgument $_ }) -join ' ')
  $ProcessInfo.UseShellExecute = $false
  $ProcessInfo.CreateNoWindow = $true
  $ProcessInfo.RedirectStandardOutput = $true
  $ProcessInfo.RedirectStandardError = $true
  $RuntimeProcess = New-Object System.Diagnostics.Process
  $RuntimeProcess.StartInfo = $ProcessInfo
  if (-not $RuntimeProcess.Start()) { throw 'Die LohnMail-Laufzeit konnte nicht gestartet werden.' }
  $StandardOutput = $RuntimeProcess.StandardOutput.ReadToEnd()
  $StandardError = $RuntimeProcess.StandardError.ReadToEnd()
  $RuntimeProcess.WaitForExit()
  return [pscustomobject]@{
    ExitCode = $RuntimeProcess.ExitCode
    Output = (($StandardOutput + ' ' + $StandardError).Trim())
  }
}
function Test-HistoryDatabase([string]$Runtime,[string]$Entry,[string]$Database) {
  if (-not (Test-Path $Database)) { return }
  if (-not (Test-Path $Runtime)) { throw 'SQLite-Prüfung ist nicht verfügbar: LohnMail-Laufzeit fehlt.' }
  $RuntimeArguments = @()
  if ($Entry) { $RuntimeArguments += $Entry }
  $RuntimeArguments += '--lohnmail-update-check-db'
  $RuntimeArguments += $Database
  $DbResult = Invoke-UpdateRuntime $Runtime $RuntimeArguments
  if ($DbResult.ExitCode -ne 0) {
    $Details = $DbResult.Output
    Write-UpdateLog "SQLITE_CHECK_FAILED details=$Details"
    throw "Die lokale SQLite-Historie konnte nicht gelesen werden oder ist beschädigt. Details wurden im Update-Protokoll gespeichert."
  }
}
function Expand-UpdateArchive([string]$Runtime,[string]$Entry,[string]$ArchivePath,[string]$Destination) {
  if (-not (Test-Path $Runtime)) { throw 'Update-Laufzeit fehlt.' }
  $RuntimeArguments = @()
  if ($Entry) { $RuntimeArguments += $Entry }
  $RuntimeArguments += '--lohnmail-update-extract'
  $RuntimeArguments += $ArchivePath
  $RuntimeArguments += $Destination
  $ExtractResult = Invoke-UpdateRuntime $Runtime $RuntimeArguments
  if ($ExtractResult.ExitCode -ne 0) {
    $Details = $ExtractResult.Output
    Write-UpdateLog "ARCHIVE_EXTRACT_FAILED details=$Details"
    throw 'Die Update-Datei konnte nicht sicher entpackt werden. Details wurden im Update-Protokoll gespeichert.'
  }
}
function Test-NewApplication([string]$InstalledApp,[string]$Version,[string]$Build,[string]$Database) {
  $NewRuntime = Join-Path $InstalledApp 'LohnMail.exe'
  $NewEntry = ''
  if (-not (Test-Path $NewRuntime)) {
    $NewRuntime = Join-Path $InstalledApp '.venv\Scripts\python.exe'
    $NewEntry = Join-Path $InstalledApp 'main.py'
  }
  if (-not (Test-Path $NewRuntime)) { throw 'Die neue LohnMail-Laufzeit fehlt.' }
  if ($NewEntry -and -not (Test-Path $NewEntry)) { throw 'main.py fehlt nach der Installation.' }
  $RuntimeArguments = @()
  if ($NewEntry) { $RuntimeArguments += $NewEntry }
  $RuntimeArguments += '--lohnmail-update-selftest'
  $RuntimeArguments += $Version
  $RuntimeArguments += $Build
  if (Test-Path $Database) {
    $RuntimeArguments += '--history-db'
    $RuntimeArguments += $Database
  }
  $SelfTestResult = Invoke-UpdateRuntime $NewRuntime $RuntimeArguments
  if ($SelfTestResult.ExitCode -ne 0) {
    $SelfTestDetails = $SelfTestResult.Output
    Write-UpdateLog "APP_SELFTEST_FAILED details=$SelfTestDetails"
    throw 'Die neue Programmversion hat den Selbsttest nicht bestanden. Details wurden im Update-Protokoll gespeichert.'
  }
}
function Move-AppToBackup {
  $LastMoveError = ''
  for ($Attempt = 1; $Attempt -le 40; $Attempt++) {
    try {
      Move-Item -LiteralPath $AppDir -Destination $BackupDir -ErrorAction Stop
      return
    } catch {
      $LastMoveError = $_.Exception.Message
      if ($Attempt -lt 40) {
        Set-Step 'Warten, bis die Programmdateien freigegeben sind ...' 30
        Start-Sleep -Milliseconds 500
      }
    }
  }
  Write-UpdateLog "APP_DIRECTORY_LOCKED details=$LastMoveError"
  throw 'Der Programmordner wird noch von Windows oder einem anderen Programm verwendet. Bitte schließen Sie LohnMail-, Eingabeaufforderungs- und Explorer-Fenster im App-Ordner und versuchen Sie es erneut.'
}
function Wait-ForProcessExit([int]$Id,[int]$TimeoutSeconds) {
  if ($Id -le 0) { return }
  $Deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
  while ((Get-Process -Id $Id -ErrorAction SilentlyContinue) -and ([DateTime]::UtcNow -lt $Deadline)) {
    Start-Sleep -Milliseconds 250
  }
}

try {
  Set-Step 'LohnMail wird beendet ...' 5
  Wait-ForProcessExit $ProcessId 60
  if (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue) {
    throw 'LohnMail konnte nicht vollständig beendet werden. Bitte schließen Sie das Programm und versuchen Sie das Update erneut.'
  }
  if ($ParentProcessId -gt 0) {
    $ParentProcess = Get-Process -Id $ParentProcessId -ErrorAction SilentlyContinue
    if ($ParentProcess -and @('cmd','powershell','pwsh','py','python','pythonw') -contains $ParentProcess.ProcessName.ToLowerInvariant()) {
      Wait-ForProcessExit $ParentProcessId 15
    }
  }
  Set-Step 'Lokale SQLite-Historie wird geprüft ...' 10
  Test-HistoryDatabase $RuntimeExecutable $RuntimeEntry $HistoryDb
  $OldHistoryHash = if (Test-Path $HistoryDb) { (Get-FileHash $HistoryDb -Algorithm SHA256).Hash } else { '' }
  Set-Step 'Update-Datei wird vorbereitet ...' 15
  New-Item -ItemType Directory -Force -Path $Stage | Out-Null
  Expand-UpdateArchive $RuntimeExecutable $RuntimeEntry $Archive $Stage
  $Source = Join-Path $Stage 'LohnMail\App'
  if (-not (Test-Path $Source)) { $Source = Join-Path $Stage 'App' }
  if (-not (Test-Path (Join-Path $Source 'main.py')) -and -not (Test-Path (Join-Path $Source 'LohnMail.exe'))) {
    $Main = Get-ChildItem -LiteralPath $Stage -Recurse -File -Filter 'main.py' |
      Where-Object { $_.Directory.Name -eq 'App' } | Select-Object -First 1
    if ($Main) { $Source = $Main.Directory.FullName }
  }
  $SourceHasPython = Test-Path (Join-Path $Source 'main.py')
  $SourceHasExecutable = Test-Path (Join-Path $Source 'LohnMail.exe')
  if (-not $SourceHasPython -and -not $SourceHasExecutable) { throw 'Ungültiges Update: App enthält weder LohnMail.exe noch main.py.' }
  if ($FrozenBuild -and -not $SourceHasExecutable) { throw 'Dieses Update enthält keine fertige Windows-EXE-Version und kann nicht über eine EXE-Installation installiert werden.' }
  if (Test-Path $BackupDir) { Remove-Item -LiteralPath $BackupDir -Recurse -Force }
  Set-Step 'Sicherung der bisherigen Programmversion wird erstellt ...' 30
  Move-AppToBackup
  try {
    Set-Step 'Neue Programmdateien werden installiert ...' 55
    Copy-Item -LiteralPath $Source -Destination $AppDir -Recurse -Force
    $OldVenv = Join-Path $BackupDir '.venv'
    if ((Test-Path $OldVenv) -and -not (Test-Path (Join-Path $AppDir 'LohnMail.exe'))) { Move-Item -LiteralPath $OldVenv -Destination (Join-Path $AppDir '.venv') }

    Set-Step 'Installation und vorhandene Daten werden geprüft ...' 78
    if (-not (Test-Path (Join-Path $AppDir 'main.py')) -and -not (Test-Path (Join-Path $AppDir 'LohnMail.exe'))) { throw 'Die ausführbare LohnMail-Anwendung fehlt nach der Installation.' }
    if (-not (Test-Path $SettingsDir)) { throw 'Der Ordner Settings ist nicht mehr vorhanden.' }
    if (-not (Test-Path $CompaniesDir)) { throw 'Der Ordner Companies ist nicht mehr vorhanden.' }
    $NewSettingsHash = if (Test-Path (Join-Path $SettingsDir 'settings.json')) { (Get-FileHash (Join-Path $SettingsDir 'settings.json') -Algorithm SHA256).Hash } else { '' }
    $NewCompanyCount = @(Get-ChildItem -LiteralPath $CompaniesDir -Recurse -File).Count
    if ($OldSettingsHash -ne $NewSettingsHash) { throw 'settings.json wurde während der Installation verändert.' }
    if ($OldCompanyCount -ne $NewCompanyCount) { throw 'Der Inhalt des Ordners Companies wurde während der Installation verändert.' }
    $NewHistoryHash = if (Test-Path $HistoryDb) { (Get-FileHash $HistoryDb -Algorithm SHA256).Hash } else { '' }
    if ($OldHistoryHash -ne $NewHistoryHash) { throw 'Die lokale SQLite-Historie wurde während der Installation verändert.' }

    Test-NewApplication $AppDir $TargetVersion $TargetBuild $HistoryDb
    $Installed = $true
    Set-Step 'Update erfolgreich abgeschlossen.' 100
    Write-UpdateLog "SUCCESS version=$TargetVersion build=$TargetBuild settings_unchanged=true companies_unchanged=true sqlite_quick_check=ok sqlite_unchanged=true"
    Remove-Item -LiteralPath $BackupDir -Recurse -Force
    Show-UpdateMessage "LohnMail $TargetVersion wurde erfolgreich installiert." 'Update erfolgreich' 'Information'
  } catch {
    $ExitCode = 1
    Set-Step 'Fehler erkannt. Vorherige Version wird wiederhergestellt ...' 85
    if (Test-Path $AppDir) { Remove-Item -LiteralPath $AppDir -Recurse -Force }
    if (Test-Path $BackupDir) { Move-Item -LiteralPath $BackupDir -Destination $AppDir }
    $RolledBack = $true
    Write-UpdateLog "FAILED rollback=true error=$($_.Exception.Message)"
    Show-UpdateMessage "Das Update konnte nicht installiert werden.`r`n`r`nDie vorherige Version wurde wiederhergestellt.`r`n`r`n$($_.Exception.Message)" 'Update fehlgeschlagen' 'Error'
  }
} catch {
  $ExitCode = 1
  Write-UpdateLog "FAILED rollback=$RolledBack error=$($_.Exception.Message)"
  Show-UpdateMessage "Das Update konnte nicht vorbereitet werden.`r`n`r`n$($_.Exception.Message)" 'Update fehlgeschlagen' 'Error'
} finally {
  Remove-Item -LiteralPath $Stage -Recurse -Force -ErrorAction SilentlyContinue
  if ($Form) { $Form.Close() }
  $Launcher = Join-Path $RootDir 'INSTALL-AND-START-WINDOWS.cmd'
  if (Test-Path $Launcher) { Start-Process -FilePath $Launcher -WorkingDirectory $RootDir }
}
exit $ExitCode
""",
            encoding="utf-8-sig",
        )
        return script

    def _fetch_manifest(self) -> dict:
        parsed = urlparse(self.manifest_url)
        is_local = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if parsed.scheme != "https" and not (parsed.scheme == "http" and is_local):
            raise UpdateError("Der Update-Server muss über HTTPS erreichbar sein.")
        request = Request(self.manifest_url, headers={"Accept": "application/json", "User-Agent": f"LohnMail/{APP_VERSION}"})
        with self._opener(request, timeout=15) as response:
            raw = response.read(MAX_MANIFEST_BYTES + 1)
        if len(raw) > MAX_MANIFEST_BYTES:
            raise UpdateError("Das Update-Manifest ist zu groß.")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpdateError("Der Update-Server hat kein gültiges Manifest geliefert.") from exc
        if not isinstance(data, dict):
            raise UpdateError("Ungültiges Update-Manifest.")
        if data.get("available") is False:
            return {"available": False}

        version = str(data.get("version", "") or "").strip()
        build = str(data.get("build", "") or "").strip()
        if not version or not build:
            raise UpdateError("Version oder Build fehlt im Update-Manifest.")
        test_mode = data.get("test_mode") is True
        download_url = _safe_download_url(
            data.get("download_url", ""),
            allow_test_zip=self.test_updates_enabled and test_mode,
        )
        sha256 = str(data.get("sha256", "") or "").strip().lower()
        size = _safe_int(data.get("size", 0))
        if not download_url:
            raise UpdateError("Download-URL fehlt im Update-Manifest.")
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise UpdateError("SHA-256 fehlt oder ist ungültig.")
        if size <= 0:
            raise UpdateError("Dateigröße fehlt im Update-Manifest.")
        notes = data.get("release_notes", [])
        if isinstance(notes, str):
            notes = [line.strip() for line in notes.splitlines() if line.strip()]
        if not isinstance(notes, list):
            notes = []
        required = data.get("required") is True
        required_reason = str(data.get("required_reason", "") or "").strip().lower()
        if not required or required_reason not in REQUIRED_REASONS:
            required_reason = ""
        return {
            "available": True,
            "version": version,
            "build": build,
            "download_url": download_url,
            "sha256": sha256,
            "size": size,
            "release_notes": [str(item)[:500] for item in notes[:20]],
            "required": required and bool(required_reason),
            "required_reason": required_reason,
            "test_mode": test_mode,
        }

    @staticmethod
    def _verified_existing_download(updates: dict, manifest: dict) -> Path | None:
        if (
            str(updates.get("available_version", "")) != manifest["version"]
            or str(updates.get("available_build", "")) != manifest["build"]
            or str(updates.get("download_url", "")) != manifest["download_url"]
            or str(updates.get("sha256", "")).lower() != manifest["sha256"]
            or _safe_int(updates.get("size", 0)) != manifest["size"]
        ):
            return None

        path_value = str(updates.get("downloaded_path", "") or "").strip()
        if not path_value:
            return None
        path = Path(path_value)
        if (
            not path.is_file()
            or path.suffix.lower() not in ({".exe", ".msi", ".zip"} if manifest.get("test_mode") else {".exe", ".msi"})
            or path.stat().st_size != manifest["size"]
        ):
            return None
        if _sha256_file(path) != manifest["sha256"]:
            return None
        return path

    def _save_changes(self, changes: dict) -> dict:
        settings = self._load_settings()
        updates = dict(settings.get("updates", {}))
        updates.update(changes)
        settings["updates"] = updates
        self._save_settings(settings)
        return self._public_state(updates)

    @staticmethod
    def _progress_state(downloaded: int, total: int) -> dict:
        progress = round(downloaded * 100 / total) if total else 0
        return {
            "status": "downloading",
            "progress": min(100, max(0, progress)),
            "downloaded_bytes": downloaded,
            "total_bytes": total,
            "message": "Update wird heruntergeladen.",
        }

    def _public_state(self, updates: dict) -> dict:
        return {
            "installed_version": APP_VERSION,
            "installed_build": APP_BUILD,
            "last_checked_at": str(updates.get("last_checked_at", "") or ""),
            "auto_check": bool(updates.get("auto_check", True)),
            "status": str(updates.get("status", "idle") or "idle"),
            "available_version": str(updates.get("available_version", "") or ""),
            "available_build": str(updates.get("available_build", "") or ""),
            "required": bool(updates.get("required", False)),
            "progress": _safe_int(updates.get("progress", 0)),
            "downloaded_bytes": _safe_int(updates.get("downloaded_bytes", 0)),
            "total_bytes": _safe_int(updates.get("total_bytes", 0)),
            "release_notes": list(updates.get("release_notes", []) or []),
            "install_on_exit": bool(updates.get("install_on_exit", False)),
            "install_supported": self.platform == "win32",
            "required_reason": str(updates.get("required_reason", "") or ""),
            "test_mode": bool(updates.get("test_mode", False)),
            "message": str(updates.get("message", "") or ""),
        }
