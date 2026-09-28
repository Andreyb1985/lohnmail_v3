"""Run the canonical LohnMail source without a packaged platform build."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
runpy.run_path(str(PROJECT_ROOT / "main.py"), run_name="__main__")
