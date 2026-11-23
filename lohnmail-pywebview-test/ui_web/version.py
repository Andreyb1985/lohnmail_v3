APP_VERSION = "2.2.0"
APP_BUILD = "2026.11.23.1"
# This flag exists only in explicitly labelled test builds. Production builds
# must keep it False so only signed EXE/MSI installers are accepted.
TEST_UPDATES_ENABLED = False


def app_metadata() -> dict[str, str]:
    """Installed macOS bundle identity, otherwise canonical source metadata."""
    import plistlib
    import re
    import sys
    from pathlib import Path

    fallback = {"version": APP_VERSION, "build": APP_BUILD}
    if sys.platform != "darwin" or not getattr(sys, "frozen", False):
        return fallback
    try:
        plist = Path(sys.executable).parent.parent / "Info.plist"
        data = plistlib.loads(plist.read_bytes())
        if not isinstance(data, dict):
            return fallback
        version, build = data.get("CFBundleShortVersionString"), data.get("CFBundleVersion")
        if all(isinstance(value, str) and re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", value)
               for value in (version, build)):
            return {"version": version, "build": build}
    except (OSError, ValueError, TypeError):
        pass
    return fallback
