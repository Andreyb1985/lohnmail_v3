from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Mapping


DIRECT = "direct"
STORE = "store"
SUPPORTED_DISTRIBUTIONS = {DIRECT, STORE}
MARKER_FILENAME = "lohnmail_distribution.json"


def resource_dir() -> Path:
    """Return the read-only application resource directory."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root).resolve()
    return Path(__file__).resolve().parent.parent


def _marker_data(marker_path: Path | None = None) -> dict:
    path = marker_path or (resource_dir() / MARKER_FILENAME)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def get_distribution_channel(
    environ: Mapping[str, str] | None = None,
    marker_path: Path | None = None,
) -> str:
    """Resolve the build channel without relying on the current directory."""
    values = os.environ if environ is None else environ
    override = str(values.get("LOHNMAIL_DISTRIBUTION", "") or "").strip().lower()
    if override in SUPPORTED_DISTRIBUTIONS:
        return override
    marker_value = str(_marker_data(marker_path).get("distribution", "") or "").strip().lower()
    return marker_value if marker_value in SUPPORTED_DISTRIBUTIONS else DIRECT


def is_store_build() -> bool:
    return get_distribution_channel() == STORE


def distribution_label() -> str:
    return "Microsoft Store" if is_store_build() else "Direct"


def microsoft_store_uri() -> str:
    configured = str(os.environ.get("LOHNMAIL_STORE_URI", "") or "").strip()
    if configured:
        return configured
    return str(_marker_data().get("store_uri", "") or "").strip()
