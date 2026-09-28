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
