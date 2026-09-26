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
