from __future__ import annotations

import ssl
import sys
from pathlib import Path


def create_ssl_context() -> ssl.SSLContext:
    """Create a verified TLS context that also works in frozen macOS apps."""
    bundle_root = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else None
    bundled_ca = bundle_root / "certs" / "cert.pem" if bundle_root else None
    if bundled_ca and bundled_ca.is_file():
        return ssl.create_default_context(cafile=str(bundled_ca))
    return ssl.create_default_context()
