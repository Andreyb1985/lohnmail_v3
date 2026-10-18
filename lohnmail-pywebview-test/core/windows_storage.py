"""Windows-only API boundary; no guessed user/drive/package paths."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


def application_folders(family):
    # Isolated MTA thread: leave pywebview's UI apartment untouched. This
    # documented API supports a full-trust process querying its own family.
    def query():
        from winrt.windows.management.core import ApplicationDataManager
        data = ApplicationDataManager.create_for_package_family(family)
        return Path(data.local_folder.path), Path(data.local_cache_folder.path)
    with ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(query).result()


def known_folder(identifier):
    import ctypes
    import uuid
    from ctypes import wintypes
    class GUID(ctypes.Structure):
        _fields_ = [('data', ctypes.c_byte * 16)]
    guid = GUID.from_buffer_copy(uuid.UUID(identifier).bytes_le)
    shell = ctypes.WinDLL('shell32')
    shell.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD,
                                         wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    ole = ctypes.WinDLL('ole32')
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole.CoInitializeEx.restype = ctypes.c_long
    hr = ole.CoInitializeEx(None, 2)
    if hr < 0 and hr != -2147417850:  # RPC_E_CHANGED_MODE: COM already initialized
        raise OSError('Windows-Ordnerdienst konnte nicht initialisiert werden.')
    result = ctypes.c_void_p()
    try:
        # NO_PACKAGE_REDIRECTION resolves the known-folder path only; it does
        # NOT disable file virtualization. DONT_VERIFY avoids probing UNC here.
        if shell.SHGetKnownFolderPath(ctypes.byref(guid), 0x14000, None, ctypes.byref(result)):
            raise OSError('Der Windows-Benutzerordner konnte nicht ermittelt werden.')
        return Path(ctypes.wstring_at(result))
    finally:
        ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
        ole.CoTaskMemFree(result)
        if hr >= 0:
            ole.CoUninitialize()


def default_workspace():
    # FOLDERID_Documents: honor the real Windows location, including redirection.
    path = known_folder('FDD39AD0-238F-46AF-ADB4-6C85480369C7') / 'LohnMail'
    path.mkdir(parents=True, exist_ok=True)
    return path


def _sta_dialog(callback):
    """WinForms folder dialogs require STA; do not change the caller's apartment."""
    import clr
    clr.AddReference('System.Windows.Forms')
    clr.AddReference('System.Drawing')
    from System.Threading import Thread, ThreadStart, ApartmentState
    result, errors = [], []
    def run():
        try:
            result.append(callback())
        except Exception as exc:
            errors.append(exc)
    thread = Thread(ThreadStart(run))
    thread.SetApartmentState(ApartmentState.STA)
    thread.Start()
    thread.Join()
    if errors:
        raise errors[0]
    return result[0]


def resolve_existing_workspace(workspace, error=''):
    def dialog():
        from System.Drawing import Size, Point
        from System.Windows.Forms import (Form, TextBox, Button, DialogResult, FolderBrowserDialog,
                                         FormStartPosition, FormBorderStyle, ScrollBars)
        form = Form()
        form.Text = 'LohnMail – Vorhandene Daten'
        form.ClientSize = Size(640, 320)
        form.StartPosition = FormStartPosition.CenterScreen
        form.FormBorderStyle = FormBorderStyle.FixedDialog
        form.MaximizeBox = False
        form.MinimizeBox = False
        text = TextBox()
        text.Location, text.Size = Point(20, 20), Size(600, 220)
        text.Multiline, text.ReadOnly, text.ScrollBars = True, True, ScrollBars.Vertical
        text.Text = ('Vorhandene LohnMail-Daten gefunden:\r\n' + str(workspace) +
            '\r\n\r\nDiese Daten verwenden oder einen anderen Arbeitsordner wählen? '
            'Vor dem Verbinden wird eine geprüfte Sicherung angelegt. Originaldateien bleiben erhalten. '
            'Andere LohnMail-Instanzen bitte schließen.\r\n\r\n'
            'Gelöschte Programmeinstellungen und Lizenzen können nur aus vorhandenen Kopien '
            'wiederhergestellt werden. Sonst bitte E-Mail und Lizenz erneut einrichten.' +
            ('\r\n\r\nVerbindung nicht möglich: ' + error if error else ''))
        form.Controls.Add(text)
        for label, code, x, width in [('Daten verwenden', DialogResult.Yes, 20, 180),
                                      ('Anderen Ordner wählen', DialogResult.No, 210, 220),
                                      ('Abbrechen', DialogResult.Cancel, 440, 180)]:
            button = Button()
            button.Text, button.DialogResult = label, code
            button.Location, button.Size = Point(x, 265), Size(width, 35)
            form.Controls.Add(button)
            if code == DialogResult.Cancel:
                form.CancelButton = button
                form.AcceptButton = button  # Never accept data recovery accidentally.
        try:
            answer = form.ShowDialog()
        finally:
            form.Dispose()
        if answer == DialogResult.Yes:
            return 'reuse', Path(workspace)
        if answer != DialogResult.No:
            return None
        picker = FolderBrowserDialog()
        picker.Description = 'LohnMail-Arbeitsordner wählen (vorhandene Daten werden nicht überschrieben)'
        picker.SelectedPath = str(known_folder('FDD39AD0-238F-46AF-ADB4-6C85480369C7'))
        picker.ShowNewFolderButton = True
        try:
            return ('new', Path(str(picker.SelectedPath))) if picker.ShowDialog() == DialogResult.OK else None
        finally:
            picker.Dispose()
    return _sta_dialog(dialog)


def show_recovery_notice(notice):
    def dialog():
        from System.Windows.Forms import MessageBox
        message = 'Arbeitsordner verbunden. Sicherung: ' + notice['backup']
        if not notice['settings_restored']:
            message += '\r\nProgrammeinstellungen fehlen. Bitte E-Mail und Eingabedateien erneut einrichten.'
        if not notice['license_restored']:
            message += '\r\nKeine gespeicherte Lizenz gefunden. Bitte Lizenz erneut aktivieren.'
        MessageBox.Show(message, 'LohnMail – Wiederherstellung')
    _sta_dialog(dialog)


def export_legacy_storage(workspace, family, local, cache):
    """Snapshot physical stores with a helper which verifies NO_PACKAGE itself.

    No shell, PowerShell, elevation, policy change, or customer source mutation.
    The helper must succeed before any settings/license import is attempted.
    """
    import json
    import os
    import shutil
    import subprocess
    import sys
    import tempfile
    from core.storage_paths import StorageError, atomic_json

    executable = Path(sys.executable).parent / 'LohnMail.StorageExport.exe'
    if not executable.is_file():
        raise StorageError('Datensicherungsmodul fehlt. Bitte die vollständige Store-Version installieren.')
    # Executable outside the package; desktop-app process policy plus the
    # helper's native identity check prevent reading a virtualized merged view.
    with tempfile.TemporaryDirectory(prefix='.lohnmail-export-tool-', dir=workspace) as temporary:
        directory = Path(temporary)
        helper = directory / executable.name
        shutil.copy2(executable, helper)
        request, response = directory / 'request.json', directory / 'response.json'
        atomic_json(request, {'family': family, 'workspace': str(workspace),
                              'local': str(local), 'cache': str(cache),
                              'parent': os.getpid(), 'response': str(response)})
        try:
            result = subprocess.run([str(helper), str(request), '0'], cwd=directory,
                                    timeout=900, creationflags=0x08000000, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise StorageError('Datensicherung konnte nicht abgeschlossen werden. '
                               'Originaldaten bleiben erhalten. Bitte erneut starten.') from exc
        report = json.loads(response.read_text(encoding='utf-8-sig')) if response.is_file() else {}
        if result.returncode or report.get('identity_result') != 15700 or not report.get('complete'):
            raise StorageError('Datensicherung nicht abgeschlossen; nichts umgeschaltet. '
                               + str(report.get('error', 'Windows-Datensicherungsmodul konnte nicht starten.')))
